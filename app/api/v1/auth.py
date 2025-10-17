# app/api/v1/auth.py
"""
Authentication API Routes

Endpoints:
- POST /auth/login - User login
- POST /auth/logout - User logout
- POST /auth/refresh - Refresh access token
- GET /auth/me - Get current user info
- POST /auth/change-password - Change password
- POST /auth/forgot-password - Request password reset
- POST /auth/reset-password - Reset password with token
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from typing import Optional

from app.api.deps import (
    get_db,
    get_current_user,
    get_current_active_user,
    get_current_token
)
from app.models.auth import InternalUser
from app.schemas.auth import (
    UserLogin,
    UserResponseWithToken,
    UserResponse,
    Token,
    PasswordChange,
    PasswordResetRequest,
    PasswordReset,
    MessageResponse
)
from app.services.auth_service import AuthService
from app.core.security import verify_password, hash_password, validate_password


router = APIRouter(prefix="/auth", tags=["Authentication"])


# ============================================================================
# LOGIN
# ============================================================================

@router.post("/login", response_model=UserResponseWithToken)
def login(
    credentials: UserLogin,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Login user and create session
    
    Returns:
        User data and JWT token
        
    Raises:
        401: Invalid credentials
        403: Account locked or disabled
    """
    auth_service = AuthService(db)
    
    # Get client info
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    
    # Login
    result = auth_service.login(
        credentials=credentials,
        ip_address=ip_address,
        user_agent=user_agent
    )
    
    return {
        "user": result["user"],
        "token": result["token"]
    }


# ============================================================================
# LOGOUT
# ============================================================================

@router.post("/logout", response_model=MessageResponse)
def logout(
    token: str = Depends(get_current_token),
    db: Session = Depends(get_db)
):
    """
    Logout user (invalidate token)
    
    Returns:
        Success message
    """
    auth_service = AuthService(db)
    auth_service.logout(token)
    
    return {
        "message": "Logged out successfully",
        "success": True
    }


# ============================================================================
# REFRESH TOKEN
# ============================================================================

@router.post("/refresh", response_model=Token)
def refresh_token(
    refresh_token: str,
    db: Session = Depends(get_db)
):
    """
    Refresh access token using refresh token
    
    Args:
        refresh_token: JWT refresh token
        
    Returns:
        New access token
        
    Raises:
        401: Invalid or expired refresh token
    """
    auth_service = AuthService(db)
    result = auth_service.refresh_token(refresh_token)
    
    return result


# ============================================================================
# GET CURRENT USER
# ============================================================================

@router.get("/me", response_model=UserResponse)
def get_me(
    current_user: InternalUser = Depends(get_current_active_user)
):
    """
    Get current authenticated user information
    
    Returns:
        Current user data
        
    Requires:
        Valid JWT token in Authorization header
    """
    return current_user


# ============================================================================
# CHANGE PASSWORD
# ============================================================================

@router.post("/change-password", response_model=MessageResponse)
def change_password(
    password_data: PasswordChange,
    current_user: InternalUser = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Change user's password (user knows current password)
    
    Args:
        password_data: Current password and new password
        
    Returns:
        Success message
        
    Raises:
        400: Current password is incorrect or new password invalid
    """
    # Verify current password
    if not verify_password(password_data.current_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect"
        )
    
    # Validate new password
    is_valid, error_message = validate_password(password_data.new_password)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_message
        )
    
    # Check new password is different from current
    if verify_password(password_data.new_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must be different from current password"
        )
    
    # Update password
    current_user.password_hash = hash_password(password_data.new_password)
    db.commit()
    
    return {
        "message": "Password changed successfully",
        "success": True
    }


# ============================================================================
# FORGOT PASSWORD
# ============================================================================

@router.post("/forgot-password", response_model=MessageResponse)
def forgot_password(
    request_data: PasswordResetRequest,
    db: Session = Depends(get_db)
):
    """
    Request password reset (sends email with reset token)
    
    Args:
        request_data: User's email
        
    Returns:
        Success message (always returns success for security)
        
    Note:
        Always returns success even if email doesn't exist
        to prevent email enumeration attacks
    """
    auth_service = AuthService(db)
    auth_service.request_password_reset(request_data.email)
    
    return {
        "message": "If the email exists, a password reset link has been sent",
        "success": True
    }


# ============================================================================
# RESET PASSWORD
# ============================================================================

@router.post("/reset-password", response_model=MessageResponse)
def reset_password(
    reset_data: PasswordReset,
    db: Session = Depends(get_db)
):
    """
    Reset password using token from email
    
    Args:
        reset_data: Reset token and new password
        
    Returns:
        Success message
        
    Raises:
        400: Invalid or expired token, or invalid password
    """
    auth_service = AuthService(db)
    auth_service.reset_password(
        token=reset_data.token,
        new_password=reset_data.new_password
    )
    
    return {
        "message": "Password reset successfully. Please login with your new password.",
        "success": True
    }


# ============================================================================
# HEALTH CHECK
# ============================================================================

@router.get("/health")
def health_check():
    """
    Health check endpoint (no authentication required)
    
    Returns:
        Status message
    """
    return {
        "status": "healthy",
        "service": "authentication"
    }