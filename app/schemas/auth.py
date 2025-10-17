# app/schemas/auth.py
"""
Pydantic Schemas for Authentication

These schemas define:
- What data the API accepts (Request models)
- What data the API returns (Response models)
- Data validation rules
"""

from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional
from datetime import datetime
from uuid import UUID


# ============================================================================
# USER REGISTRATION & CREATION
# ============================================================================

class UserCreate(BaseModel):
    """
    Schema for creating a new user (Admin creates PM/SBC)
    """
    email: EmailStr = Field(..., description="User's email address")
    password: str = Field(..., min_length=8, description="User's password")
    full_name: str = Field(..., min_length=1, max_length=255, description="Full name")
    role: str = Field(..., description="User role: ADMIN, PROJECT_MANAGER, or SBC")
    phone: Optional[str] = Field(None, max_length=50, description="Phone number")
    
    # SBC-specific fields
    sbc_code: Optional[str] = Field(None, max_length=50, description="SBC code (e.g., SBC-001)")
    sbc_company_name: Optional[str] = Field(None, max_length=255, description="Company name")
    sbc_contact_phone: Optional[str] = Field(None, max_length=50)
    sbc_contact_email: Optional[EmailStr] = Field(None)
    
    # Permission flags (optional, defaults set based on role)
    can_approve: Optional[bool] = None
    can_create_assignments: Optional[bool] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "email": "john@sib.com",
                "password": "SecurePass123!",
                "full_name": "John Smith",
                "role": "PROJECT_MANAGER",
                "phone": "+212-6-12-34-56-78"
            }
        }


class UserCreateSBC(BaseModel):
    """
    Specific schema for creating SBC accounts
    """
    email: EmailStr
    password: str = Field(..., min_length=8)
    full_name: str = Field(..., min_length=1, max_length=255)
    sbc_code: str = Field(..., max_length=50, description="SBC code (e.g., SBC-001)")
    sbc_company_name: str = Field(..., max_length=255)
    sbc_contact_phone: Optional[str] = None
    sbc_contact_email: Optional[EmailStr] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "email": "alpha@construction.com",
                "password": "SecurePass123!",
                "full_name": "Alpha Construction Ltd",
                "sbc_code": "SBC-001",
                "sbc_company_name": "Alpha Construction Ltd",
                "sbc_contact_phone": "+212-6-12-34-56-78",
                "sbc_contact_email": "contact@alpha-construction.com"
            }
        }


# ============================================================================
# LOGIN & AUTHENTICATION
# ============================================================================

class UserLogin(BaseModel):
    """
    Schema for user login
    """
    email: EmailStr = Field(..., description="User's email")
    password: str = Field(..., description="User's password")
    
    class Config:
        json_schema_extra = {
            "example": {
                "email": "john@sib.com",
                "password": "SecurePass123!"
            }
        }


class Token(BaseModel):
    """
    Schema for JWT token response
    """
    access_token: str = Field(..., description="JWT access token")
    refresh_token: Optional[str] = Field(None, description="JWT refresh token")
    token_type: str = Field(default="bearer", description="Token type")
    expires_in: int = Field(..., description="Token expiration in seconds")
    
    class Config:
        json_schema_extra = {
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_type": "bearer",
                "expires_in": 86400
            }
        }


class TokenData(BaseModel):
    """
    Schema for decoded token data
    """
    user_id: Optional[UUID] = None
    email: Optional[str] = None
    role: Optional[str] = None


# ============================================================================
# USER RESPONSE
# ============================================================================

class UserResponse(BaseModel):
    """
    Schema for user data returned by API
    """
    id: UUID
    email: str
    full_name: str
    role: str
    phone: Optional[str] = None
    
    # Permissions
    can_approve: bool
    can_create_assignments: bool
    can_create_users: bool
    
    # SBC fields
    sbc_code: Optional[str] = None
    sbc_company_name: Optional[str] = None
    sbc_contact_phone: Optional[str] = None
    sbc_contact_email: Optional[str] = None
    
    # Account status
    is_active: bool
    is_locked: bool
    email_verified: bool
    
    # Timestamps
    created_at: datetime
    updated_at: datetime
    last_login_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "email": "john@sib.com",
                "full_name": "John Smith",
                "role": "PROJECT_MANAGER",
                "phone": "+212-6-12-34-56-78",
                "can_approve": True,
                "can_create_assignments": True,
                "can_create_users": False,
                "is_active": True,
                "is_locked": False,
                "email_verified": True,
                "created_at": "2025-01-01T10:00:00Z",
                "updated_at": "2025-01-01T10:00:00Z",
                "last_login_at": "2025-01-15T14:30:00Z"
            }
        }


class UserResponseWithToken(BaseModel):
    """
    Schema for login response (user data + token)
    """
    user: UserResponse
    token: Token
    
    class Config:
        json_schema_extra = {
            "example": {
                "user": {
                    "id": "123e4567-e89b-12d3-a456-426614174000",
                    "email": "john@sib.com",
                    "full_name": "John Smith",
                    "role": "PROJECT_MANAGER"
                },
                "token": {
                    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                    "token_type": "bearer",
                    "expires_in": 86400
                }
            }
        }


# ============================================================================
# USER UPDATE
# ============================================================================

class UserUpdate(BaseModel):
    """
    Schema for updating user information
    """
    full_name: Optional[str] = Field(None, min_length=1, max_length=255)
    phone: Optional[str] = Field(None, max_length=50)
    
    # SBC fields
    sbc_company_name: Optional[str] = Field(None, max_length=255)
    sbc_contact_phone: Optional[str] = Field(None, max_length=50)
    sbc_contact_email: Optional[EmailStr] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "full_name": "John Smith Senior",
                "phone": "+212-6-12-34-56-99"
            }
        }


# ============================================================================
# PASSWORD MANAGEMENT
# ============================================================================

class PasswordChange(BaseModel):
    """
    Schema for changing password (user knows current password)
    """
    current_password: str = Field(..., description="Current password")
    new_password: str = Field(..., min_length=8, description="New password")
    confirm_password: str = Field(..., description="Confirm new password")
    
    @validator('confirm_password')
    def passwords_match(cls, v, values):
        if 'new_password' in values and v != values['new_password']:
            raise ValueError('Passwords do not match')
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "current_password": "OldPass123!",
                "new_password": "NewPass123!",
                "confirm_password": "NewPass123!"
            }
        }


class PasswordResetRequest(BaseModel):
    """
    Schema for requesting password reset
    """
    email: EmailStr = Field(..., description="User's email")
    
    class Config:
        json_schema_extra = {
            "example": {
                "email": "john@sib.com"
            }
        }


class PasswordReset(BaseModel):
    """
    Schema for resetting password with token
    """
    token: str = Field(..., description="Password reset token from email")
    new_password: str = Field(..., min_length=8, description="New password")
    confirm_password: str = Field(..., description="Confirm new password")
    
    @validator('confirm_password')
    def passwords_match(cls, v, values):
        if 'new_password' in values and v != values['new_password']:
            raise ValueError('Passwords do not match')
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "token": "kJ8mN2pQ5rT9wX1yZ4aC7eH0jL3nP6sV8",
                "new_password": "NewPass123!",
                "confirm_password": "NewPass123!"
            }
        }


# ============================================================================
# PERMISSION MANAGEMENT
# ============================================================================

class GrantApprovalPermission(BaseModel):
    """
    Schema for granting approval permission to PM
    """
    reason: Optional[str] = Field(None, description="Reason for granting permission")
    
    class Config:
        json_schema_extra = {
            "example": {
                "reason": "Promoted to senior PM, needs approval authority"
            }
        }


class RevokeApprovalPermission(BaseModel):
    """
    Schema for revoking approval permission
    """
    reason: Optional[str] = Field(None, description="Reason for revoking permission")
    
    class Config:
        json_schema_extra = {
            "example": {
                "reason": "Moving to different role, no longer needs approval authority"
            }
        }


# ============================================================================
# EMAIL VERIFICATION
# ============================================================================

class EmailVerification(BaseModel):
    """
    Schema for email verification
    """
    token: str = Field(..., description="Email verification token")
    
    class Config:
        json_schema_extra = {
            "example": {
                "token": "kJ8mN2pQ5rT9wX1yZ4aC7eH0jL3nP6sV8"
            }
        }


# ============================================================================
# GENERIC RESPONSES
# ============================================================================

class MessageResponse(BaseModel):
    """
    Generic message response
    """
    message: str = Field(..., description="Response message")
    success: bool = Field(default=True, description="Operation success status")
    
    class Config:
        json_schema_extra = {
            "example": {
                "message": "Operation completed successfully",
                "success": True
            }
        }


class ErrorResponse(BaseModel):
    """
    Error response
    """
    detail: str = Field(..., description="Error details")
    error_code: Optional[str] = Field(None, description="Error code")
    
    class Config:
        json_schema_extra = {
            "example": {
                "detail": "Invalid credentials",
                "error_code": "AUTH_001"
            }
        }


# ============================================================================
# USER LIST
# ============================================================================

class UserListResponse(BaseModel):
    """
    Schema for list of users with pagination
    """
    users: list[UserResponse]
    total: int = Field(..., description="Total number of users")
    page: int = Field(..., description="Current page")
    per_page: int = Field(..., description="Items per page")
    total_pages: int = Field(..., description="Total number of pages")
    
    class Config:
        json_schema_extra = {
            "example": {
                "users": [],
                "total": 50,
                "page": 1,
                "per_page": 20,
                "total_pages": 3
            }
        }