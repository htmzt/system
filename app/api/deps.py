# app/api/deps.py
"""
API Dependencies

This module provides dependency functions for FastAPI routes:
- get_db: Get database session
- get_current_user: Get authenticated user from JWT token
- get_current_active_user: Get active user
- require_role: Require specific role
"""

from typing import Generator, Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from jose import JWTError
import uuid

from app.database import SessionLocal
from app.models.auth import InternalUser, UserSession
from app.core.security import decode_token
from app.core.permissions import (
    require_admin,
    require_project_manager,
    require_approval_permission,
    require_active_account,
    require_unlocked_account,
    UserRole
)


# ============================================================================
# DATABASE SESSION DEPENDENCY
# ============================================================================

def get_db() -> Generator[Session, None, None]:
    """
    Get database session
    
    Usage:
        @router.get("/users")
        def get_users(db: Session = Depends(get_db)):
            users = db.query(User).all()
            return users
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ============================================================================
# JWT TOKEN SECURITY
# ============================================================================

# HTTP Bearer scheme (extracts token from "Authorization: Bearer <token>" header)
security = HTTPBearer()


# ============================================================================
# GET CURRENT USER
# ============================================================================

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> InternalUser:
    """
    Get current authenticated user from JWT token
    
    This dependency:
    1. Extracts JWT token from Authorization header
    2. Decodes and validates the token
    3. Checks if session exists in database
    4. Returns the user object
    
    Usage:
        @router.get("/me")
        def get_me(current_user: InternalUser = Depends(get_current_user)):
            return current_user
    
    Args:
        credentials: JWT token from Authorization header
        db: Database session
        
    Returns:
        InternalUser object
        
    Raises:
        HTTPException: 401 if token is invalid or user not found
    """
    token = credentials.credentials
    
    # Decode token
    payload = decode_token(token)
    
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Extract user ID from token
    user_id_str: Optional[str] = payload.get("sub")
    if user_id_str is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    try:
        user_id = uuid.UUID(user_id_str)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token format",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Check if session exists and is active
    session = db.query(UserSession).filter(
        UserSession.token == token,
        UserSession.is_active == True
    ).first()
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expired or invalid",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Get user from database
    user = db.query(InternalUser).filter(InternalUser.id == user_id).first()
    
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return user


# ============================================================================
# GET CURRENT ACTIVE USER
# ============================================================================

def get_current_active_user(
    current_user: InternalUser = Depends(get_current_user)
) -> InternalUser:
    """
    Get current user and verify account is active and not locked
    
    Usage:
        @router.get("/protected")
        def protected_route(current_user: InternalUser = Depends(get_current_active_user)):
            return {"message": "Access granted"}
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        InternalUser object
        
    Raises:
        HTTPException: 403 if account is inactive or locked
    """
    require_active_account(current_user)
    require_unlocked_account(current_user)
    return current_user


# ============================================================================
# ROLE-BASED DEPENDENCIES
# ============================================================================

def get_current_admin_user(
    current_user: InternalUser = Depends(get_current_active_user)
) -> InternalUser:
    """
    Require current user to be Admin
    
    Usage:
        @router.post("/admin/create-user")
        def create_user(admin: InternalUser = Depends(get_current_admin_user)):
            # Only admins can access this
            pass
    """
    require_admin(current_user)
    return current_user


def get_current_pm_or_admin(
    current_user: InternalUser = Depends(get_current_active_user)
) -> InternalUser:
    """
    Require current user to be Project Manager or Admin
    
    Usage:
        @router.post("/assignments/create")
        def create_assignment(user: InternalUser = Depends(get_current_pm_or_admin)):
            # Only PMs and Admins can access this
            pass
    """
    require_project_manager(current_user)
    return current_user


def get_current_approver(
    current_user: InternalUser = Depends(get_current_active_user)
) -> InternalUser:
    """
    Require current user to have approval permission
    
    Usage:
        @router.post("/assignments/{id}/approve")
        def approve_assignment(approver: InternalUser = Depends(get_current_approver)):
            # Only users with approval permission can access this
            pass
    """
    require_approval_permission(current_user)
    return current_user


# ============================================================================
# OPTIONAL AUTHENTICATION
# ============================================================================

def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db)
) -> Optional[InternalUser]:
    """
    Get current user if token is provided, otherwise return None
    
    Usage for endpoints that work with or without authentication:
        @router.get("/public-or-private")
        def mixed_route(current_user: Optional[InternalUser] = Depends(get_current_user_optional)):
            if current_user:
                return {"message": f"Hello {current_user.full_name}"}
            else:
                return {"message": "Hello guest"}
    """
    if credentials is None:
        return None
    
    try:
        return get_current_user(credentials, db)
    except HTTPException:
        return None


# ============================================================================
# GET TOKEN FROM REQUEST
# ============================================================================

def get_current_token(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> str:
    """
    Extract JWT token from Authorization header
    
    Usage:
        @router.post("/logout")
        def logout(token: str = Depends(get_current_token)):
            # Use token for logout
            pass
    """
    return credentials.credentials


# ============================================================================
# TESTING DEPENDENCIES
# ============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("API DEPENDENCIES")
    print("=" * 60)
    print("\nAvailable dependencies:")
    print("  • get_db() - Get database session")
    print("  • get_current_user() - Get authenticated user")
    print("  • get_current_active_user() - Get active user")
    print("  • get_current_admin_user() - Require Admin")
    print("  • get_current_pm_or_admin() - Require PM or Admin")
    print("  • get_current_approver() - Require approval permission")
    print("  • get_current_user_optional() - Optional authentication")
    print("  • get_current_token() - Extract JWT token")
    print("\nUsage in routes:")
    print("""
    @router.get("/me")
    def get_me(current_user: InternalUser = Depends(get_current_user)):
        return current_user
    
    @router.post("/admin-only")
    def admin_route(admin: InternalUser = Depends(get_current_admin_user)):
        return {"message": "Admin access"}
    """)
    print("=" * 60)