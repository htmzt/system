# app/models/auth.py
"""
Authentication Database Models

This module defines all database tables for the authentication system:
- InternalUser: User accounts (Admin, Project Manager, SBC)
- UserSession: Active login sessions (JWT tokens)
- LoginHistory: Audit log of all login attempts
- PermissionChangeLog: Audit log of permission changes
"""

from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Index, Integer, BigInteger, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
from datetime import datetime
from app.database import Base


# ============================================================================
# MAIN USER TABLE
# ============================================================================

class InternalUser(Base):
    """
    User accounts for Internal PO System
    
    Roles:
    - ADMIN: Full system control, creates users, approves, views everything
    - PROJECT_MANAGER: Creates assignments, can have approval permission
    - SBC: Views assigned work only
    
    Permission Flags (flexible):
    - can_approve: Can approve/reject assignments (TRUE for ADMIN, optional for PM)
    - can_create_assignments: Can create assignments (TRUE for ADMIN & PM)
    - can_create_users: Can create user accounts (TRUE for ADMIN only)
    """
    __tablename__ = "internal_users"
    
    # ========== PRIMARY KEY ==========
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # ========== AUTHENTICATION ==========
    email = Column(String(255), unique=True, nullable=False, index=True)
    # User's email for login (unique)
    
    password_hash = Column(String(255), nullable=False)
    # Encrypted password (bcrypt)
    # NEVER store plain text passwords!
    
    # ========== PROFILE ==========
    full_name = Column(String(255), nullable=False)
    # Display name
    
    phone = Column(String(50))
    # Optional phone number
    
    # ========== ROLE & PERMISSIONS ==========
    role = Column(String(50), nullable=False, index=True)
    # Values: "ADMIN", "PROJECT_MANAGER", "SBC"
    
    can_approve = Column(Boolean, default=False, nullable=False)
    # Can approve/reject assignments?
    # ADMIN: TRUE by default
    # PROJECT_MANAGER: FALSE by default (Admin can grant)
    # SBC: FALSE always
    
    can_create_assignments = Column(Boolean, default=False, nullable=False)
    # Can create assignments?
    # ADMIN: TRUE
    # PROJECT_MANAGER: TRUE
    # SBC: FALSE
    
    can_create_users = Column(Boolean, default=False, nullable=False)
    # Can create user accounts?
    # ADMIN: TRUE
    # PROJECT_MANAGER: FALSE
    # SBC: FALSE
    
    # ========== SBC-SPECIFIC FIELDS ==========
    sbc_code = Column(String(50), unique=True, index=True)
    # Example: "SBC-001", "SBC-002"
    # NULL for ADMIN and PROJECT_MANAGER
    # REQUIRED for SBC
    
    sbc_company_name = Column(String(255))
    # Company name (for SBC only)
    
    sbc_contact_phone = Column(String(50))
    sbc_contact_email = Column(String(255))
    # Additional contact info (for SBC only)
    
    # ========== ACCOUNT STATUS ==========
    is_active = Column(Boolean, default=True, nullable=False)
    # Can user login?
    # TRUE = active
    # FALSE = disabled
    
    is_locked = Column(Boolean, default=False, nullable=False)
    # Is account locked due to failed login attempts?
    # TRUE = locked
    # FALSE = normal
    
    failed_login_attempts = Column(Integer, default=0, nullable=False)
    # Counter for failed login attempts
    # Reset to 0 on successful login
    # Lock account if >= MAX_LOGIN_ATTEMPTS (from config)
    
    locked_until = Column(DateTime(timezone=True))
    # If locked, when will it auto-unlock?
    # NULL if not locked
    
    # ========== EMAIL VERIFICATION ==========
    email_verified = Column(Boolean, default=False, nullable=False)
    # Has user verified their email?
    # TRUE = verified
    # FALSE = waiting for verification
    
    email_verification_token = Column(String(255))
    # Token sent in verification email
    # NULL after verified
    
    email_verification_sent_at = Column(DateTime(timezone=True))
    # When was verification email sent?
    
    # ========== PASSWORD RESET ==========
    password_reset_token = Column(String(255))
    # Token for password reset
    # NULL if no reset requested
    
    password_reset_token_expires = Column(DateTime(timezone=True))
    # When does reset token expire?
    # Usually 1 hour from request
    
    password_reset_requested_at = Column(DateTime(timezone=True))
    # When was password reset requested?
    
    # ========== AUDIT ==========
    created_by_id = Column(UUID(as_uuid=True), ForeignKey("internal_users.id"))
    # Who created this user account?
    # NULL for first admin (created manually)
    
    # ========== TIMESTAMPS ==========
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    last_login_at = Column(DateTime(timezone=True))
    # Last successful login timestamp
    
    last_password_change = Column(DateTime(timezone=True))
    # When was password last changed?
    
    # ========== RELATIONSHIPS ==========
    created_by = relationship(
        "InternalUser",
        remote_side=[id],
        foreign_keys=[created_by_id],
        backref="created_users"
    )
    
    sessions = relationship("UserSession", back_populates="user", cascade="all, delete-orphan")
    login_history = relationship("LoginHistory", back_populates="user", cascade="all, delete-orphan")
    permission_changes = relationship(
        "PermissionChangeLog",
        foreign_keys="PermissionChangeLog.user_id",
        back_populates="user",
        cascade="all, delete-orphan"
    )
    
    # ========== INDEXES ==========
    __table_args__ = (
        Index('idx_user_email', 'email'),
        Index('idx_user_role', 'role'),
        Index('idx_user_sbc_code', 'sbc_code'),
        Index('idx_user_active', 'is_active'),
        Index('idx_user_role_active', 'role', 'is_active'),
    )
    
    def __repr__(self):
        return f"<InternalUser {self.email} ({self.role})>"


# ============================================================================
# USER SESSIONS (JWT TOKENS)
# ============================================================================

class UserSession(Base):
    """
    Active user sessions (JWT tokens)
    
    When user logs in:
    - Create a session record
    - Generate JWT token
    - Store token here
    
    When user logs out:
    - Delete the session record
    
    Token expires:
    - Automatically deleted (by cleanup job)
    """
    __tablename__ = "user_sessions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # ========== USER ==========
    user_id = Column(UUID(as_uuid=True), ForeignKey("internal_users.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # ========== TOKEN ==========
    token = Column(String(500), unique=True, nullable=False, index=True)
    # JWT access token
    
    refresh_token = Column(String(500), unique=True)
    # For refreshing access token (optional)
    
    # ========== SESSION INFO ==========
    ip_address = Column(String(50))
    # User's IP address
    
    user_agent = Column(String(500))
    # Browser/device info
    # Example: "Mozilla/5.0 (Windows NT 10.0; Win64; x64)..."
    
    device_name = Column(String(255))
    # Friendly device name
    # Example: "Chrome on Windows", "Safari on iPhone"
    
    # ========== EXPIRATION ==========
    expires_at = Column(DateTime(timezone=True), nullable=False, index=True)
    # When does this session expire?
    # Usually NOW() + 24 hours
    
    refresh_expires_at = Column(DateTime(timezone=True))
    # When does refresh token expire?
    # Usually NOW() + 30 days
    
    # ========== STATUS ==========
    is_active = Column(Boolean, default=True, nullable=False)
    # Is session still valid?
    # FALSE if user logged out
    
    # ========== TIMESTAMPS ==========
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    last_activity = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    # Updates on every API call
    
    # ========== RELATIONSHIP ==========
    user = relationship("InternalUser", back_populates="sessions")
    
    # ========== INDEXES ==========
    __table_args__ = (
        Index('idx_session_token', 'token'),
        Index('idx_session_user', 'user_id', 'is_active'),
        Index('idx_session_expires', 'expires_at'),
    )
    
    def __repr__(self):
        return f"<UserSession user={self.user_id} expires={self.expires_at}>"


# ============================================================================
# LOGIN HISTORY (AUDIT TRAIL)
# ============================================================================

class LoginHistory(Base):
    """
    Complete audit log of all login attempts
    
    Records:
    - Successful logins
    - Failed logins
    - IP addresses
    - Device info
    
    Use cases:
    - Security monitoring
    - Detect brute force attacks
    - Show user: "Last login from..."
    - Compliance/audit requirements
    """
    __tablename__ = "login_history"
    
    id = Column(BigInteger, primary_key=True)
    
    # ========== USER ==========
    user_id = Column(UUID(as_uuid=True), ForeignKey("internal_users.id", ondelete="CASCADE"), index=True)
    # NULL if login failed (user not found)
    
    email_attempted = Column(String(255), nullable=False, index=True)
    # Email used in login attempt
    # Store even if user doesn't exist
    
    # ========== RESULT ==========
    success = Column(Boolean, nullable=False, index=True)
    # TRUE = login successful
    # FALSE = login failed
    
    failure_reason = Column(String(255))
    # If failed, why?
    # Examples:
    # - "Invalid password"
    # - "User not found"
    # - "Account locked"
    # - "Account disabled"
    # - "Email not verified"
    
    # ========== SESSION INFO ==========
    ip_address = Column(String(50), index=True)
    user_agent = Column(String(500))
    device_name = Column(String(255))
    
    # ========== LOCATION (Optional) ==========
    country = Column(String(100))
    city = Column(String(100))
    # Can be populated using IP geolocation service
    
    # ========== TIMESTAMP ==========
    attempted_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    
    # ========== RELATIONSHIP ==========
    user = relationship("InternalUser", back_populates="login_history")
    
    # ========== INDEXES ==========
    __table_args__ = (
        Index('idx_login_user', 'user_id', 'attempted_at'),
        Index('idx_login_email', 'email_attempted', 'attempted_at'),
        Index('idx_login_ip', 'ip_address', 'attempted_at'),
        Index('idx_login_success', 'success', 'attempted_at'),
    )
    
    def __repr__(self):
        status = "SUCCESS" if self.success else "FAILED"
        return f"<LoginHistory {self.email_attempted} {status} at {self.attempted_at}>"


# ============================================================================
# PERMISSION CHANGE LOG (AUDIT TRAIL)
# ============================================================================

class PermissionChangeLog(Base):
    """
    Audit log for permission changes
    
    Records when Admin:
    - Grants approval permission to PM
    - Revokes approval permission from PM
    - Changes user role
    - Modifies any permission
    
    Use cases:
    - Compliance/audit
    - Answer "Who gave John approval permission?"
    - Track permission history
    """
    __tablename__ = "permission_change_logs"
    
    id = Column(BigInteger, primary_key=True)
    
    # ========== WHO ==========
    user_id = Column(UUID(as_uuid=True), ForeignKey("internal_users.id", ondelete="CASCADE"), nullable=False, index=True)
    # User whose permissions were changed
    
    changed_by_id = Column(UUID(as_uuid=True), ForeignKey("internal_users.id"), nullable=False, index=True)
    # Admin who made the change
    
    changed_by_name = Column(String(255))
    # Denormalized for history preservation
    
    # ========== WHAT ==========
    permission_name = Column(String(100), nullable=False, index=True)
    # Examples:
    # - "can_approve"
    # - "can_create_assignments"
    # - "can_create_users"
    # - "role"
    # - "is_active"
    
    old_value = Column(String(100))
    # Previous value
    # Examples: "FALSE", "PROJECT_MANAGER"
    
    new_value = Column(String(100))
    # New value
    # Examples: "TRUE", "ADMIN"
    
    # ========== WHY ==========
    reason = Column(Text)
    # Optional reason for change
    # Example: "Promoted to senior PM, needs approval permission"
    
    # ========== TIMESTAMP ==========
    changed_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    
    # ========== RELATIONSHIP ==========
    user = relationship("InternalUser", foreign_keys=[user_id], back_populates="permission_changes")
    changed_by = relationship("InternalUser", foreign_keys=[changed_by_id])
    
    # ========== INDEXES ==========
    __table_args__ = (
        Index('idx_permission_user', 'user_id', 'changed_at'),
        Index('idx_permission_changed_by', 'changed_by_id', 'changed_at'),
        Index('idx_permission_name', 'permission_name', 'changed_at'),
    )
    
    def __repr__(self):
        return f"<PermissionChangeLog {self.permission_name}: {self.old_value} → {self.new_value}>"