# app/schemas/__init__.py
"""
Pydantic Schemas
"""

from app.schemas.auth import (
    # User Creation
    UserCreate,
    UserCreateSBC,
    
    # Login
    UserLogin,
    Token,
    TokenData,
    
    # User Response
    UserResponse,
    UserResponseWithToken,
    UserListResponse,
    
    # User Update
    UserUpdate,
    
    # Password Management
    PasswordChange,
    PasswordResetRequest,
    PasswordReset,
    
    # Permissions
    GrantApprovalPermission,
    RevokeApprovalPermission,
    
    # Email Verification
    EmailVerification,
    
    # Generic Responses
    MessageResponse,
    ErrorResponse,
)

__all__ = [
    # User Creation
    "UserCreate",
    "UserCreateSBC",
    
    # Login
    "UserLogin",
    "Token",
    "TokenData",
    
    # User Response
    "UserResponse",
    "UserResponseWithToken",
    "UserListResponse",
    
    # User Update
    "UserUpdate",
    
    # Password Management
    "PasswordChange",
    "PasswordResetRequest",
    "PasswordReset",
    
    # Permissions
    "GrantApprovalPermission",
    "RevokeApprovalPermission",
    
    # Email Verification
    "EmailVerification",
    
    # Generic Responses
    "MessageResponse",
    "ErrorResponse",
]