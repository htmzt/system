# app/services/auth_service.py
"""
Authentication Service

This service handles:
- User login
- Token creation
- Password reset
- Email verification
- Login history tracking
"""

from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
import uuid

from app.models.auth import InternalUser, UserSession, LoginHistory
from app.schemas.auth import UserLogin, Token
from app.core.security import (
    verify_password,
    create_access_token,
    create_refresh_token,
    hash_password,
    validate_password,
    create_password_reset_token,
)
from app.config import settings


class AuthService:
    """Authentication service"""
    
    def __init__(self, db: Session):
        self.db = db
    
    # ========================================================================
    # LOGIN
    # ========================================================================
    
    def login(
        self,
        credentials: UserLogin,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Authenticate user and create session
        
        Args:
            credentials: Login credentials (email, password)
            ip_address: User's IP address
            user_agent: Browser/device info
            
        Returns:
            Dictionary with user and token
            
        Raises:
            HTTPException: If authentication fails
        """
        # Find user by email
        user = self.db.query(InternalUser).filter(
            InternalUser.email == credentials.email.lower()
        ).first()
        
        # Log login attempt
        login_success = False
        failure_reason = None
        
        if not user:
            failure_reason = "User not found"
            self._log_login_attempt(
                email=credentials.email,
                success=False,
                failure_reason=failure_reason,
                ip_address=ip_address,
                user_agent=user_agent
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )
        
        # Check if account is active
        if not user.is_active:
            failure_reason = "Account disabled"
            self._log_login_attempt(
                email=credentials.email,
                user_id=user.id,
                success=False,
                failure_reason=failure_reason,
                ip_address=ip_address,
                user_agent=user_agent
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is disabled. Please contact administrator."
            )
        
        # Check if account is locked
        if user.is_locked:
            # Check if lockout period has expired
            if user.locked_until and user.locked_until > datetime.now(timezone.utc):
                failure_reason = "Account locked"
                self._log_login_attempt(
                    email=credentials.email,
                    user_id=user.id,
                    success=False,
                    failure_reason=failure_reason,
                    ip_address=ip_address,
                    user_agent=user_agent
                )
                minutes_left = int((user.locked_until - datetime.now(timezone.utc)).total_seconds() / 60)
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Account is locked. Try again in {minutes_left} minutes."
                )
            else:
                # Unlock account
                user.is_locked = False
                user.locked_until = None
                user.failed_login_attempts = 0
        
        # Verify password
        if not verify_password(credentials.password, user.password_hash):
            # Increment failed attempts
            user.failed_login_attempts += 1
            
            # Lock account if too many failed attempts
            if user.failed_login_attempts >= settings.MAX_LOGIN_ATTEMPTS:
                user.is_locked = True
                user.locked_until = datetime.now(timezone.utc) + timedelta(
                    minutes=settings.LOCKOUT_DURATION_MINUTES
                )
                self.db.commit()
                
                failure_reason = "Invalid password - Account locked"
                self._log_login_attempt(
                    email=credentials.email,
                    user_id=user.id,
                    success=False,
                    failure_reason=failure_reason,
                    ip_address=ip_address,
                    user_agent=user_agent
                )
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Too many failed login attempts. Account locked for {settings.LOCKOUT_DURATION_MINUTES} minutes."
                )
            
            self.db.commit()
            
            failure_reason = "Invalid password"
            self._log_login_attempt(
                email=credentials.email,
                user_id=user.id,
                success=False,
                failure_reason=failure_reason,
                ip_address=ip_address,
                user_agent=user_agent
            )
            
            attempts_left = settings.MAX_LOGIN_ATTEMPTS - user.failed_login_attempts
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid email or password. {attempts_left} attempts remaining."
            )
        
        # Login successful! Reset failed attempts
        user.failed_login_attempts = 0
        user.last_login_at = datetime.now(timezone.utc)
        
        # Create access token
        token_data = {
            "sub": str(user.id),
            "email": user.email,
            "role": user.role
        }
        access_token = create_access_token(token_data)
        refresh_token = create_refresh_token(token_data)
        
        # Create session
        session = UserSession(
            user_id=user.id,
            token=access_token,
            refresh_token=refresh_token,
            ip_address=ip_address,
            user_agent=user_agent,
            expires_at=datetime.now(timezone.utc) + timedelta(
                minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
            ),
            refresh_expires_at=datetime.now(timezone.utc) + timedelta(
                days=settings.REFRESH_TOKEN_EXPIRE_DAYS
            )
        )
        self.db.add(session)
        
        # Log successful login
        self._log_login_attempt(
            email=credentials.email,
            user_id=user.id,
            success=True,
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        self.db.commit()
        
        return {
            "user": user,
            "token": {
                "access_token": access_token,
                "refresh_token": refresh_token,
                "token_type": "bearer",
                "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60  # seconds
            }
        }
    
    # ========================================================================
    # LOGOUT
    # ========================================================================
    
    def logout(self, token: str) -> bool:
        """
        Logout user (invalidate token)
        
        Args:
            token: JWT access token
            
        Returns:
            True if successful
        """
        # Find and delete session
        session = self.db.query(UserSession).filter(
            UserSession.token == token
        ).first()
        
        if session:
            self.db.delete(session)
            self.db.commit()
            return True
        
        return False
    
    # ========================================================================
    # TOKEN REFRESH
    # ========================================================================
    
    def refresh_token(self, refresh_token: str) -> Dict[str, Any]:
        """
        Refresh access token using refresh token
        
        Args:
            refresh_token: JWT refresh token
            
        Returns:
            New token data
            
        Raises:
            HTTPException: If refresh token is invalid
        """
        # Find session with refresh token
        session = self.db.query(UserSession).filter(
            UserSession.refresh_token == refresh_token,
            UserSession.is_active == True
        ).first()
        
        if not session:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token"
            )
        
        # Check if refresh token expired
        if session.refresh_expires_at < datetime.now(timezone.utc):
            self.db.delete(session)
            self.db.commit()
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token expired"
            )
        
        # Get user
        user = self.db.query(InternalUser).filter(
            InternalUser.id == session.user_id
        ).first()
        
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive"
            )
        
        # Create new access token
        token_data = {
            "sub": str(user.id),
            "email": user.email,
            "role": user.role
        }
        new_access_token = create_access_token(token_data)
        
        # Update session
        session.token = new_access_token
        session.expires_at = datetime.now(timezone.utc) + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
        session.last_activity = datetime.now(timezone.utc)
        
        self.db.commit()
        
        return {
            "access_token": new_access_token,
            "token_type": "bearer",
            "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
        }
    
    # ========================================================================
    # PASSWORD RESET REQUEST
    # ========================================================================
    
    def request_password_reset(self, email: str) -> bool:
        """
        Request password reset (send email with token)
        
        Args:
            email: User's email
            
        Returns:
            True (always returns True even if user doesn't exist for security)
        """
        user = self.db.query(InternalUser).filter(
            InternalUser.email == email.lower()
        ).first()
        
        if not user:
            # Don't reveal if user exists
            return True
        
        # Generate reset token
        reset_token = create_password_reset_token()
        
        # Save token
        user.password_reset_token = reset_token
        user.password_reset_token_expires = datetime.now(timezone.utc) + timedelta(hours=1)
        user.password_reset_requested_at = datetime.now(timezone.utc)
        
        self.db.commit()
        
        # TODO: Send email with reset link
        # reset_link = f"{settings.FRONTEND_URL}/reset-password?token={reset_token}"
        # send_email(user.email, "Password Reset", reset_link)
        
        return True
    
    # ========================================================================
    # PASSWORD RESET
    # ========================================================================
    
    def reset_password(self, token: str, new_password: str) -> bool:
        """
        Reset password using token
        
        Args:
            token: Password reset token
            new_password: New password
            
        Returns:
            True if successful
            
        Raises:
            HTTPException: If token is invalid or expired
        """
        # Validate new password
        is_valid, error_message = validate_password(new_password)
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_message
            )
        
        # Find user with token
        user = self.db.query(InternalUser).filter(
            InternalUser.password_reset_token == token
        ).first()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid reset token"
            )
        
        # Check if token expired
        if user.password_reset_token_expires < datetime.now(timezone.utc):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Reset token has expired"
            )
        
        # Update password
        user.password_hash = hash_password(new_password)
        user.password_reset_token = None
        user.password_reset_token_expires = None
        user.last_password_change = datetime.now(timezone.utc)
        
        # Invalidate all sessions (force re-login)
        self.db.query(UserSession).filter(
            UserSession.user_id == user.id
        ).delete()
        
        self.db.commit()
        
        return True
    
    # ========================================================================
    # HELPER METHODS
    # ========================================================================
    
    def _log_login_attempt(
        self,
        email: str,
        success: bool,
        user_id: Optional[uuid.UUID] = None,
        failure_reason: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> None:
        """Log login attempt to database"""
        log_entry = LoginHistory(
            user_id=user_id,
            email_attempted=email,
            success=success,
            failure_reason=failure_reason,
            ip_address=ip_address,
            user_agent=user_agent
        )
        self.db.add(log_entry)
        self.db.commit()