# app/api/v1/users.py
"""
User Management API Routes

Endpoints:
- POST /users - Create new user (Admin only)
- POST /users/sbc - Create new SBC (Admin only)
- GET /users - List all users (Admin only)
- GET /users/{id} - Get user by ID
- PUT /users/{id} - Update user
- DELETE /users/{id} - Deactivate user (Admin only)
- POST /users/{id}/activate - Activate user (Admin only)
- POST /users/{id}/grant-approval - Grant approval permission (Admin only)
- POST /users/{id}/revoke-approval - Revoke approval permission (Admin only)
- GET /users/stats - Get user statistics (Admin only)
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import Optional, List
from uuid import UUID

from app.api.deps import (
    get_db,
    get_current_user,
    get_current_active_user,
    get_current_admin_user
)
from app.models.auth import InternalUser
from app.schemas.auth import (
    UserCreate,
    UserCreateSBC,
    UserResponse,
    UserUpdate,
    UserListResponse,
    GrantApprovalPermission,
    RevokeApprovalPermission,
    MessageResponse
)
from app.services.user_service import UserService
from app.core.permissions import is_admin, is_owner


router = APIRouter(prefix="/users", tags=["Users"])


# ============================================================================
# CREATE USER
# ============================================================================

@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(
    user_data: UserCreate,
    admin: InternalUser = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """
    Create a new user (Admin only)
    
    Args:
        user_data: User creation data (email, password, role, etc.)
        
    Returns:
        Created user data
        
    Requires:
        Admin role
        
    Raises:
        400: Email already exists or invalid data
    """
    user_service = UserService(db)
    new_user = user_service.create_user(
        user_data=user_data,
        created_by_id=admin.id
    )
    
    return new_user


# ============================================================================
# CREATE SBC
# ============================================================================

@router.post("/sbc", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_sbc(
    sbc_data: UserCreateSBC,
    admin: InternalUser = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """
    Create a new SBC account (Admin only)
    
    Simplified endpoint specifically for creating SBC accounts
    
    Args:
        sbc_data: SBC creation data
        
    Returns:
        Created SBC user data
        
    Requires:
        Admin role
    """
    user_service = UserService(db)
    new_sbc = user_service.create_sbc(
        sbc_data=sbc_data,
        created_by_id=admin.id
    )
    
    return new_sbc


# ============================================================================
# LIST USERS
# ============================================================================

@router.get("", response_model=UserListResponse)
def list_users(
    role: Optional[str] = Query(None, description="Filter by role"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
    admin: InternalUser = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """
    List all users with pagination and filters (Admin only)
    
    Query Parameters:
        - role: Filter by role (ADMIN, PROJECT_MANAGER, SBC)
        - is_active: Filter by active status (true/false)
        - page: Page number (default: 1)
        - per_page: Items per page (default: 20, max: 100)
        
    Returns:
        Paginated list of users
        
    Requires:
        Admin role
    """
    user_service = UserService(db)
    
    skip = (page - 1) * per_page
    
    users = user_service.get_all_users(
        role=role,
        is_active=is_active,
        skip=skip,
        limit=per_page
    )
    
    total = user_service.count_users(
        role=role,
        is_active=is_active
    )
    
    total_pages = (total + per_page - 1) // per_page  # Ceiling division
    
    return {
        "users": users,
        "total": total,
        "page": page,
        "per_page": per_page,
        "total_pages": total_pages
    }


# ============================================================================
# GET USER BY ID
# ============================================================================

@router.get("/{user_id}", response_model=UserResponse)
def get_user(
    user_id: UUID,
    current_user: InternalUser = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get user by ID
    
    Users can view:
    - Their own profile
    - Admin can view any profile
    
    Args:
        user_id: User's UUID
        
    Returns:
        User data
        
    Raises:
        404: User not found
        403: Insufficient permissions
    """
    user_service = UserService(db)
    user = user_service.get_user_by_id(user_id)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Check permissions: user can view themselves or admin can view anyone
    if not (is_owner(current_user, str(user.id)) or is_admin(current_user)):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view this user"
        )
    
    return user


# ============================================================================
# UPDATE USER
# ============================================================================

@router.put("/{user_id}", response_model=UserResponse)
def update_user(
    user_id: UUID,
    update_data: UserUpdate,
    current_user: InternalUser = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Update user information
    
    Users can update:
    - Their own profile
    - Admin can update any profile
    
    Args:
        user_id: User's UUID
        update_data: Fields to update
        
    Returns:
        Updated user data
        
    Raises:
        404: User not found
        403: Insufficient permissions
    """
    # Check permissions
    if not (is_owner(current_user, str(user_id)) or is_admin(current_user)):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this user"
        )
    
    user_service = UserService(db)
    updated_user = user_service.update_user(user_id, update_data)
    
    return updated_user


# ============================================================================
# DEACTIVATE USER
# ============================================================================

@router.delete("/{user_id}", response_model=MessageResponse)
def deactivate_user(
    user_id: UUID,
    admin: InternalUser = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """
    Deactivate user account (Admin only)
    
    Note: This doesn't delete the user, just sets is_active=False
    
    Args:
        user_id: User's UUID
        
    Returns:
        Success message
        
    Requires:
        Admin role
        
    Raises:
        404: User not found
        400: Cannot deactivate yourself
    """
    # Prevent admin from deactivating themselves
    if str(user_id) == str(admin.id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot deactivate your own account"
        )
    
    user_service = UserService(db)
    user_service.deactivate_user(user_id, admin.id)
    
    return {
        "message": "User deactivated successfully",
        "success": True
    }


# ============================================================================
# ACTIVATE USER
# ============================================================================

@router.post("/{user_id}/activate", response_model=MessageResponse)
def activate_user(
    user_id: UUID,
    admin: InternalUser = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """
    Activate user account (Admin only)
    
    Args:
        user_id: User's UUID
        
    Returns:
        Success message
        
    Requires:
        Admin role
    """
    user_service = UserService(db)
    user_service.activate_user(user_id, admin.id)
    
    return {
        "message": "User activated successfully",
        "success": True
    }


# ============================================================================
# GRANT APPROVAL PERMISSION
# ============================================================================

@router.post("/{user_id}/grant-approval", response_model=UserResponse)
def grant_approval_permission(
    user_id: UUID,
    grant_data: GrantApprovalPermission,
    admin: InternalUser = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """
    Grant approval permission to a Project Manager (Admin only)
    
    Args:
        user_id: User's UUID (must be PROJECT_MANAGER)
        grant_data: Reason for granting (optional)
        
    Returns:
        Updated user data
        
    Requires:
        Admin role
        
    Raises:
        404: User not found
        400: User is not a Project Manager or already has permission
    """
    user_service = UserService(db)
    updated_user = user_service.grant_approval_permission(
        user_id=user_id,
        granted_by_id=admin.id,
        reason=grant_data.reason
    )
    
    return updated_user


# ============================================================================
# REVOKE APPROVAL PERMISSION
# ============================================================================

@router.post("/{user_id}/revoke-approval", response_model=UserResponse)
def revoke_approval_permission(
    user_id: UUID,
    revoke_data: RevokeApprovalPermission,
    admin: InternalUser = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """
    Revoke approval permission from a user (Admin only)
    
    Args:
        user_id: User's UUID
        revoke_data: Reason for revoking (optional)
        
    Returns:
        Updated user data
        
    Requires:
        Admin role
        
    Raises:
        404: User not found
        400: User doesn't have approval permission or is Admin
    """
    user_service = UserService(db)
    updated_user = user_service.revoke_approval_permission(
        user_id=user_id,
        revoked_by_id=admin.id,
        reason=revoke_data.reason
    )
    
    return updated_user


# ============================================================================
# USER STATISTICS
# ============================================================================

@router.get("/stats/overview")
def get_user_statistics(
    admin: InternalUser = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """
    Get user statistics (Admin only)
    
    Returns:
        Statistics about users in the system
        
    Requires:
        Admin role
    """
    user_service = UserService(db)
    stats = user_service.get_user_statistics()
    
    return stats