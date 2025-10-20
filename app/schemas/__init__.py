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

from app.schemas.assignment import (
    # PO Line Selection
    POLineSelection,
    
    # Assignment Creation
    BulkAssignmentCreate,
    BulkAssignmentCreateResponse,
    AssignmentCreatedSummary,
    AssignmentCreate,
    AssignmentUpdate,
    
    # Assignment Actions
    AssignmentApprove,
    AssignmentReject,
    
    # Assignment Response
    AssignmentResponse,
    AssignmentWithUsers,
    AssignmentWithPODetails,
    AssignmentListResponse,
    
    # Statistics
    AssignmentStatistics,
    
    # PO Details
    POLineDetail,
)

__all__ = [
    # User schemas
    "UserCreate",
    "UserCreateSBC",
    "UserLogin",
    "Token",
    "TokenData",
    "UserResponse",
    "UserResponseWithToken",
    "UserListResponse",
    "UserUpdate",
    "PasswordChange",
    "PasswordResetRequest",
    "PasswordReset",
    "GrantApprovalPermission",
    "RevokeApprovalPermission",
    "EmailVerification",
    "MessageResponse",
    "ErrorResponse",
    
    # Assignment schemas
    "AssignmentCreate",
    "AssignmentUpdate",
    "AssignmentSubmit",
    "AssignmentApprove",
    "AssignmentReject",
    "AssignmentResponse",
    "AssignmentWithUsers",
    "AssignmentWithPODetails",
    "AssignmentListResponse",
    "AssignmentStatistics",
    "POLineDetail",
]