# app/services/user_service.py
"""
User Management Service

This service handles:
- Creating users (Admin creates PM/SBC)
- Updating user information
- Granting/revoking permissions
- User CRUD operations
- Permission change logging
"""

from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
import uuid

from app.models.auth import InternalUser, PermissionChangeLog
from app.schemas.auth import UserCreate, UserCreateSBC, UserUpdate
from app.core.security import hash_password, validate_password
from app.core.permissions import UserRole


class UserService:
    """User management service"""
    
    def __init__(self, db: Session):
        self.db = db
    
    # ========================================================================
    # CREATE USERS
    # ========================================================================
    
    def create_user(
        self,
        user_data: UserCreate,
        created_by_id: uuid.UUID
    ) -> InternalUser:
        """
        Create a new user (Admin creates PM/SBC)
        
        Args:
            user_data: User creation data
            created_by_id: ID of admin creating the user
            
        Returns:
            Created user object
            
        Raises:
            HTTPException: If validation fails or email exists
        """
        # Validate password
        is_valid, error_message = validate_password(user_data.password)
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_message
            )
        
        # Check if email already exists
        existing_user = self.db.query(InternalUser).filter(
            InternalUser.email == user_data.email.lower()
        ).first()
        
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        
        # Validate role
        valid_roles = [UserRole.ADMIN, UserRole.PROJECT_MANAGER, UserRole.SBC]
        if user_data.role not in valid_roles:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid role. Must be one of: {', '.join(valid_roles)}"
            )
        
        # Set permissions based on role
        if user_data.role == UserRole.ADMIN:
            can_approve = True
            can_create_assignments = True
            can_create_users = True
        elif user_data.role == UserRole.PROJECT_MANAGER:
            # PM can have approval permission if explicitly granted
            can_approve = user_data.can_approve if user_data.can_approve is not None else False
            can_create_assignments = True
            can_create_users = False
        else:  # SBC
            can_approve = False
            can_create_assignments = False
            can_create_users = False
        
        # Create user
        new_user = InternalUser(
            email=user_data.email.lower(),
            password_hash=hash_password(user_data.password),
            full_name=user_data.full_name,
            phone=user_data.phone,
            role=user_data.role,
            can_approve=can_approve,
            can_create_assignments=can_create_assignments,
            can_create_users=can_create_users,
            sbc_code=user_data.sbc_code,
            sbc_company_name=user_data.sbc_company_name,
            sbc_contact_phone=user_data.sbc_contact_phone,
            sbc_contact_email=user_data.sbc_contact_email,
            is_active=True,
            email_verified=True,  # Auto-verify for admin-created accounts
            created_by_id=created_by_id
        )
        
        self.db.add(new_user)
        self.db.commit()
        self.db.refresh(new_user)
        
        return new_user
    
    def create_sbc(
        self,
        sbc_data: UserCreateSBC,
        created_by_id: uuid.UUID
    ) -> InternalUser:
        """
        Create a new SBC account (simplified)
        
        Args:
            sbc_data: SBC creation data
            created_by_id: ID of admin creating the SBC
            
        Returns:
            Created SBC user object
        """
        # Check if SBC code already exists
        existing_sbc = self.db.query(InternalUser).filter(
            InternalUser.sbc_code == sbc_data.sbc_code
        ).first()
        
        if existing_sbc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"SBC code {sbc_data.sbc_code} already exists"
            )
        
        # Create user data
        user_data = UserCreate(
            email=sbc_data.email,
            password=sbc_data.password,
            full_name=sbc_data.full_name,
            role=UserRole.SBC,
            sbc_code=sbc_data.sbc_code,
            sbc_company_name=sbc_data.sbc_company_name,
            sbc_contact_phone=sbc_data.sbc_contact_phone,
            sbc_contact_email=sbc_data.sbc_contact_email
        )
        
        return self.create_user(user_data, created_by_id)
    
    # ========================================================================
    # READ USERS
    # ========================================================================
    
    def get_user_by_id(self, user_id: uuid.UUID) -> Optional[InternalUser]:
        """
        Get user by ID
        
        Args:
            user_id: User's UUID
            
        Returns:
            User object or None
        """
        return self.db.query(InternalUser).filter(
            InternalUser.id == user_id
        ).first()
    
    def get_user_by_email(self, email: str) -> Optional[InternalUser]:
        """
        Get user by email
        
        Args:
            email: User's email
            
        Returns:
            User object or None
        """
        return self.db.query(InternalUser).filter(
            InternalUser.email == email.lower()
        ).first()
    
    def get_all_users(
        self,
        role: Optional[str] = None,
        is_active: Optional[bool] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[InternalUser]:
        """
        Get all users with optional filters
        
        Args:
            role: Filter by role (optional)
            is_active: Filter by active status (optional)
            skip: Number of records to skip (pagination)
            limit: Maximum number of records to return
            
        Returns:
            List of users
        """
        query = self.db.query(InternalUser)
        
        if role:
            query = query.filter(InternalUser.role == role)
        
        if is_active is not None:
            query = query.filter(InternalUser.is_active == is_active)
        
        return query.offset(skip).limit(limit).all()
    
    def count_users(
        self,
        role: Optional[str] = None,
        is_active: Optional[bool] = None
    ) -> int:
        """
        Count users with optional filters
        
        Args:
            role: Filter by role (optional)
            is_active: Filter by active status (optional)
            
        Returns:
            Number of users
        """
        query = self.db.query(InternalUser)
        
        if role:
            query = query.filter(InternalUser.role == role)
        
        if is_active is not None:
            query = query.filter(InternalUser.is_active == is_active)
        
        return query.count()
    
    # ========================================================================
    # UPDATE USERS
    # ========================================================================
    
    def update_user(
        self,
        user_id: uuid.UUID,
        update_data: UserUpdate
    ) -> InternalUser:
        """
        Update user information
        
        Args:
            user_id: User's UUID
            update_data: Fields to update
            
        Returns:
            Updated user object
            
        Raises:
            HTTPException: If user not found
        """
        user = self.get_user_by_id(user_id)
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Update fields if provided
        if update_data.full_name is not None:
            user.full_name = update_data.full_name
        
        if update_data.phone is not None:
            user.phone = update_data.phone
        
        # SBC-specific fields
        if user.role == UserRole.SBC:
            if update_data.sbc_company_name is not None:
                user.sbc_company_name = update_data.sbc_company_name
            
            if update_data.sbc_contact_phone is not None:
                user.sbc_contact_phone = update_data.sbc_contact_phone
            
            if update_data.sbc_contact_email is not None:
                user.sbc_contact_email = update_data.sbc_contact_email
        
        user.updated_at = datetime.now(timezone.utc)
        
        self.db.commit()
        self.db.refresh(user)
        
        return user
    
    # ========================================================================
    # DEACTIVATE USER
    # ========================================================================
    
    def deactivate_user(
        self,
        user_id: uuid.UUID,
        deactivated_by_id: uuid.UUID
    ) -> InternalUser:
        """
        Deactivate user account
        
        Args:
            user_id: User to deactivate
            deactivated_by_id: Admin deactivating the user
            
        Returns:
            Updated user object
        """
        user = self.get_user_by_id(user_id)
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        user.is_active = False
        
        # Log permission change
        self._log_permission_change(
            user_id=user_id,
            changed_by_id=deactivated_by_id,
            permission_name="is_active",
            old_value="True",
            new_value="False",
            reason="Account deactivated"
        )
        
        self.db.commit()
        self.db.refresh(user)
        
        return user
    
    def activate_user(
        self,
        user_id: uuid.UUID,
        activated_by_id: uuid.UUID
    ) -> InternalUser:
        """
        Activate user account
        
        Args:
            user_id: User to activate
            activated_by_id: Admin activating the user
            
        Returns:
            Updated user object
        """
        user = self.get_user_by_id(user_id)
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        user.is_active = True
        
        # Log permission change
        self._log_permission_change(
            user_id=user_id,
            changed_by_id=activated_by_id,
            permission_name="is_active",
            old_value="False",
            new_value="True",
            reason="Account activated"
        )
        
        self.db.commit()
        self.db.refresh(user)
        
        return user
    
    # ========================================================================
    # PERMISSION MANAGEMENT
    # ========================================================================
    
    def grant_approval_permission(
        self,
        user_id: uuid.UUID,
        granted_by_id: uuid.UUID,
        reason: Optional[str] = None
    ) -> InternalUser:
        """
        Grant approval permission to a Project Manager
        
        Args:
            user_id: User to grant permission to
            granted_by_id: Admin granting the permission
            reason: Optional reason for granting
            
        Returns:
            Updated user object
            
        Raises:
            HTTPException: If user not found or not a PM
        """
        user = self.get_user_by_id(user_id)
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Only Project Managers can be granted approval permission
        # (Admins already have it, SBCs can't have it)
        if user.role != UserRole.PROJECT_MANAGER:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only Project Managers can be granted approval permission"
            )
        
        if user.can_approve:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User already has approval permission"
            )
        
        # Grant permission
        user.can_approve = True
        
        # Log permission change
        self._log_permission_change(
            user_id=user_id,
            changed_by_id=granted_by_id,
            permission_name="can_approve",
            old_value="False",
            new_value="True",
            reason=reason
        )
        
        self.db.commit()
        self.db.refresh(user)
        
        return user
    
    def revoke_approval_permission(
        self,
        user_id: uuid.UUID,
        revoked_by_id: uuid.UUID,
        reason: Optional[str] = None
    ) -> InternalUser:
        """
        Revoke approval permission from a user
        
        Args:
            user_id: User to revoke permission from
            revoked_by_id: Admin revoking the permission
            reason: Optional reason for revoking
            
        Returns:
            Updated user object
        """
        user = self.get_user_by_id(user_id)
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Can't revoke from Admin
        if user.role == UserRole.ADMIN:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot revoke approval permission from Admin"
            )
        
        if not user.can_approve:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User doesn't have approval permission"
            )
        
        # Revoke permission
        user.can_approve = False
        
        # Log permission change
        self._log_permission_change(
            user_id=user_id,
            changed_by_id=revoked_by_id,
            permission_name="can_approve",
            old_value="True",
            new_value="False",
            reason=reason
        )
        
        self.db.commit()
        self.db.refresh(user)
        
        return user
    
    # ========================================================================
    # HELPER METHODS
    # ========================================================================
    
    def _log_permission_change(
        self,
        user_id: uuid.UUID,
        changed_by_id: uuid.UUID,
        permission_name: str,
        old_value: str,
        new_value: str,
        reason: Optional[str] = None
    ) -> None:
        """Log permission change to database"""
        
        # Get changed_by user name
        changed_by = self.get_user_by_id(changed_by_id)
        changed_by_name = changed_by.full_name if changed_by else "Unknown"
        
        log_entry = PermissionChangeLog(
            user_id=user_id,
            changed_by_id=changed_by_id,
            changed_by_name=changed_by_name,
            permission_name=permission_name,
            old_value=old_value,
            new_value=new_value,
            reason=reason
        )
        
        self.db.add(log_entry)
        self.db.commit()
    
    # ========================================================================
    # STATISTICS
    # ========================================================================
    
    def get_user_statistics(self) -> Dict[str, Any]:
        """
        Get user statistics
        
        Returns:
            Dictionary with statistics
        """
        total_users = self.count_users()
        active_users = self.count_users(is_active=True)
        
        admins = self.count_users(role=UserRole.ADMIN)
        pms = self.count_users(role=UserRole.PROJECT_MANAGER)
        sbcs = self.count_users(role=UserRole.SBC)
        
        # Count PMs with approval permission
        pms_with_approval = self.db.query(InternalUser).filter(
            InternalUser.role == UserRole.PROJECT_MANAGER,
            InternalUser.can_approve == True
        ).count()
        
        return {
            "total_users": total_users,
            "active_users": active_users,
            "inactive_users": total_users - active_users,
            "by_role": {
                "admins": admins,
                "project_managers": pms,
                "sbcs": sbcs
            },
            "project_managers_with_approval": pms_with_approval
        }