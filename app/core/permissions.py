# app/core/permissions.py
"""
Permission Checking Functions

This module provides functions to check if a user has permission to perform actions.

Roles:
- ADMIN: Full system access
- PROJECT_MANAGER: Creates assignments, can have approval permission
- SBC: Views assigned work only

Permission Flags:
- can_approve: Can approve/reject assignments
- can_create_assignments: Can create assignments
- can_create_users: Can create user accounts
"""

from typing import Optional
from fastapi import HTTPException, status
import uuid


# ============================================================================
# PERMISSION CONSTANTS
# ============================================================================

class UserRole:
    """User role constants"""
    ADMIN = "ADMIN"
    PROJECT_MANAGER = "PROJECT_MANAGER"
    SBC = "SBC"


# ============================================================================
# ROLE CHECKING
# ============================================================================

def is_admin(user) -> bool:
    """
    Check if user is Admin
    
    Args:
        user: User object from database
        
    Returns:
        True if user is Admin
    """
    return user.role == UserRole.ADMIN


def is_project_manager(user) -> bool:
    """
    Check if user is Project Manager
    
    Args:
        user: User object from database
        
    Returns:
        True if user is Project Manager
    """
    return user.role == UserRole.PROJECT_MANAGER


def is_sbc(user) -> bool:
    """
    Check if user is SBC
    
    Args:
        user: User object from database
        
    Returns:
        True if user is SBC
    """
    return user.role == UserRole.SBC


# ============================================================================
# PERMISSION CHECKING
# ============================================================================

def can_approve(user) -> bool:
    """
    Check if user can approve assignments
    
    Args:
        user: User object from database
        
    Returns:
        True if user can approve
    """
    return user.can_approve


def can_create_assignments(user) -> bool:
    """
    Check if user can create assignments
    
    Args:
        user: User object from database
        
    Returns:
        True if user can create assignments
    """
    return user.can_create_assignments


def can_create_users(user) -> bool:
    """
    Check if user can create user accounts
    
    Args:
        user: User object from database
        
    Returns:
        True if user can create users
    """
    return user.can_create_users


def can_manage_permissions(user) -> bool:
    """
    Check if user can grant/revoke permissions
    Only Admin can do this
    
    Args:
        user: User object from database
        
    Returns:
        True if user can manage permissions
    """
    return is_admin(user)


# ============================================================================
# REQUIRE PERMISSION (FOR API ROUTES)
# ============================================================================

def require_admin(user) -> None:
    """
    Require user to be Admin
    Raises HTTPException if not
    
    Usage in routes:
        @router.get("/admin-only")
        def admin_route(current_user = Depends(get_current_user)):
            require_admin(current_user)
            # ... admin-only code
    
    Args:
        user: User object from database
        
    Raises:
        HTTPException: 403 Forbidden if user is not Admin
    """
    if not is_admin(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )


def require_project_manager(user) -> None:
    """
    Require user to be Project Manager or Admin
    
    Args:
        user: User object from database
        
    Raises:
        HTTPException: 403 Forbidden if user is not PM or Admin
    """
    if not (is_project_manager(user) or is_admin(user)):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Project Manager access required"
        )


def require_approval_permission(user) -> None:
    """
    Require user to have approval permission
    
    Args:
        user: User object from database
        
    Raises:
        HTTPException: 403 Forbidden if user cannot approve
    """
    if not can_approve(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Approval permission required"
        )


def require_create_assignments_permission(user) -> None:
    """
    Require user to have permission to create assignments
    
    Args:
        user: User object from database
        
    Raises:
        HTTPException: 403 Forbidden if user cannot create assignments
    """
    if not can_create_assignments(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission to create assignments required"
        )


def require_create_users_permission(user) -> None:
    """
    Require user to have permission to create users
    
    Args:
        user: User object from database
        
    Raises:
        HTTPException: 403 Forbidden if user cannot create users
    """
    if not can_create_users(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission to create users required"
        )


# ============================================================================
# OWNERSHIP CHECKING
# ============================================================================

def is_owner(user, resource_user_id: str) -> bool:
    """
    Check if user owns a resource
    
    Args:
        user: User object from database
        resource_user_id: User ID of resource owner
        
    Returns:
        True if user owns the resource
    """
    return str(user.id) == str(resource_user_id)


def require_owner_or_admin(user, resource_user_id: str) -> None:
    """
    Require user to be owner of resource or Admin
    
    Args:
        user: User object from database
        resource_user_id: User ID of resource owner
        
    Raises:
        HTTPException: 403 Forbidden if user is not owner or Admin
    """
    if not (is_owner(user, resource_user_id) or is_admin(user)):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to access this resource"
        )


# ============================================================================
# ACTIVE ACCOUNT CHECKING
# ============================================================================

def require_active_account(user) -> None:
    """
    Require user account to be active
    
    Args:
        user: User object from database
        
    Raises:
        HTTPException: 403 Forbidden if account is not active
    """
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is disabled"
        )


def require_unlocked_account(user) -> None:
    """
    Require user account to not be locked
    
    Args:
        user: User object from database
        
    Raises:
        HTTPException: 403 Forbidden if account is locked
    """
    if user.is_locked:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is locked due to multiple failed login attempts"
        )


def require_verified_email(user) -> None:
    """
    Require user email to be verified
    
    Args:
        user: User object from database
        
    Raises:
        HTTPException: 403 Forbidden if email is not verified
    """
    if not user.email_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email verification required"
        )


# ============================================================================
# COMBINED CHECKS
# ============================================================================

def check_user_can_login(user) -> None:
    """
    Check if user can login
    Checks:
    - Account is active
    - Account is not locked
    
    Args:
        user: User object from database
        
    Raises:
        HTTPException: 403 Forbidden if user cannot login
    """
    require_active_account(user)
    require_unlocked_account(user)


# ============================================================================
# PERMISSION SUMMARY
# ============================================================================

def get_user_permissions(user) -> dict:
    """
    Get summary of user's permissions
    
    Args:
        user: User object from database
        
    Returns:
        Dictionary of permissions
        
    Example:
        >>> permissions = get_user_permissions(admin_user)
        >>> print(permissions)
        {
            'role': 'ADMIN',
            'is_admin': True,
            'is_project_manager': False,
            'is_sbc': False,
            'can_approve': True,
            'can_create_assignments': True,
            'can_create_users': True,
            'can_manage_permissions': True
        }
    """
    return {
        "role": user.role,
        "is_admin": is_admin(user),
        "is_project_manager": is_project_manager(user),
        "is_sbc": is_sbc(user),
        "can_approve": can_approve(user),
        "can_create_assignments": can_create_assignments(user),
        "can_create_users": can_create_users(user),
        "can_manage_permissions": can_manage_permissions(user),
    }


# ============================================================================
# TESTING
# ============================================================================

if __name__ == "__main__":
    from app.models.auth import InternalUser
    
    print("=" * 60)
    print("PERMISSION FUNCTIONS TEST")
    print("=" * 60)
    
    # Create mock users for testing
    print("\n1. Creating mock users...")
    
    # Admin user
    admin = InternalUser(
        id=uuid.uuid4(),
        email="admin@test.com",
        password_hash="hash",
        full_name="Admin User",
        role=UserRole.ADMIN,
        can_approve=True,
        can_create_assignments=True,
        can_create_users=True,
        is_active=True,
        is_locked=False,
        email_verified=True
    )
    print("   ✅ Admin user created")
    
    # Project Manager (with approval)
    pm_with_approval = InternalUser(
        id=uuid.uuid4(),
        email="pm-senior@test.com",
        password_hash="hash",
        full_name="Senior PM",
        role=UserRole.PROJECT_MANAGER,
        can_approve=True,
        can_create_assignments=True,
        can_create_users=False,
        is_active=True,
        is_locked=False,
        email_verified=True
    )
    print("   ✅ PM (with approval) created")
    
    # Project Manager (no approval)
    pm_no_approval = InternalUser(
        id=uuid.uuid4(),
        email="pm-junior@test.com",
        password_hash="hash",
        full_name="Junior PM",
        role=UserRole.PROJECT_MANAGER,
        can_approve=False,
        can_create_assignments=True,
        can_create_users=False,
        is_active=True,
        is_locked=False,
        email_verified=True
    )
    print("   ✅ PM (no approval) created")
    
    # SBC user
    sbc = InternalUser(
        id=uuid.uuid4(),
        email="sbc@test.com",
        password_hash="hash",
        full_name="SBC Company",
        role=UserRole.SBC,
        can_approve=False,
        can_create_assignments=False,
        can_create_users=False,
        is_active=True,
        is_locked=False,
        email_verified=True,
        sbc_code="SBC-001"
    )
    print("   ✅ SBC user created")
    
    # Test permissions
    print("\n2. Testing permissions...")
    
    users = [
        ("Admin", admin),
        ("Senior PM", pm_with_approval),
        ("Junior PM", pm_no_approval),
        ("SBC", sbc)
    ]
    
    for name, user in users:
        print(f"\n   {name}:")
        perms = get_user_permissions(user)
        for key, value in perms.items():
            if isinstance(value, bool):
                icon = "✅" if value else "❌"
                print(f"      {icon} {key}")
            else:
                print(f"      • {key}: {value}")
    
    print("\n" + "=" * 60)
    print("✅ PERMISSION FUNCTIONS READY!")
    print("=" * 60)
    
