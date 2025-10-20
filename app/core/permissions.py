from typing import Optional
from fastapi import HTTPException, status
import uuid
# ============================================================================
# PERMISSION CONSTANTS
# ============================================================================
class UserRole:
    ADMIN = "ADMIN"
    PD = "PD"                    # Procurement Director
    PROJECT_MANAGER = "PROJECT_MANAGER"
    SBC = "SBC"
# ============================================================================
# ROLE CHECKING
# ============================================================================
def is_admin(user) -> bool:
    return user.role == UserRole.ADMIN
def is_project_manager(user) -> bool:
    return user.role == UserRole.PROJECT_MANAGER
def is_sbc(user) -> bool:
    return user.role == UserRole.SBC
# ============================================================================
# PERMISSION CHECKING
# ============================================================================
def can_approve(user) -> bool:
    return user.can_approve
def can_create_assignments(user) -> bool:
    return user.can_create_assignments
def can_create_users(user) -> bool:
    return user.can_create_users
def can_manage_permissions(user) -> bool:
    return is_admin(user)
# ============================================================================
# REQUIRE PERMISSION (FOR API ROUTES)
# ============================================================================
def require_admin(user) -> None:
    if not is_admin(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
def require_project_manager(user) -> None:
    if not (is_project_manager(user) or is_admin(user)):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Project Manager access required"
        )
def require_approval_permission(user) -> None:
    if not can_approve(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Approval permission required"
        )
def require_create_assignments_permission(user) -> None:
    if not can_create_assignments(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission to create assignments required"
        )
def require_create_users_permission(user) -> None:
    if not can_create_users(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission to create users required"
        )
# ============================================================================
# OWNERSHIP CHECKING
# ============================================================================
def is_owner(user, resource_user_id: str) -> bool:
    return str(user.id) == str(resource_user_id)
def require_owner_or_admin(user, resource_user_id: str) -> None:
    if not (is_owner(user, resource_user_id) or is_admin(user)):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to access this resource"
        )
# ============================================================================
# ACTIVE ACCOUNT CHECKING
# ============================================================================
def require_active_account(user) -> None:
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is disabled"
        )
def require_unlocked_account(user) -> None:
    if user.is_locked:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is locked due to multiple failed login attempts"
        )
def require_verified_email(user) -> None:
    if not user.email_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email verification required"
        )
# ============================================================================
# COMBINED CHECKS
# ============================================================================
def check_user_can_login(user) -> None:
    require_active_account(user)
    require_unlocked_account(user)
# ============================================================================
# PERMISSION SUMMARY
# ============================================================================
def get_user_permissions(user) -> dict:

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

