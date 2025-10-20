# app/models/assignment.py
"""
Assignment Model - Internal PO Assignment System
PM assigns external PO lines to SBC
"""

from sqlalchemy import Column, String, DateTime, ForeignKey, Index, Text, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
import enum
from app.database import Base


# ============================================================================
# ENUMS
# ============================================================================

class AssignmentStatus(str, enum.Enum):
    """Assignment status values"""
    DRAFT = "DRAFT"                          # PM is editing
    PENDING_APPROVAL = "PENDING_APPROVAL"    # Submitted, waiting for approval
    APPROVED = "APPROVED"                    # Approved, SBC can see it
    REJECTED = "REJECTED"                    # Rejected by approver
    CANCELLED = "CANCELLED"                  # Cancelled by PM


# ============================================================================
# ASSIGNMENT MODEL
# ============================================================================

class Assignment(Base):

    __tablename__ = "assignments"
    
    # ========== PRIMARY KEY ==========
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # ========== INTERNAL PO ID ==========
    internal_po_id = Column(String(50), unique=True, nullable=False, index=True)
    # Format: PO-SIB-YYYYMMDD-XXX
    # Example: PO-SIB-20251017-001
    
    # ========== WHO ==========
    created_by_pm_id = Column(
        UUID(as_uuid=True), 
        ForeignKey("internal_users.id", ondelete="RESTRICT"), 
        nullable=False,
        index=True
    )
    
    assigned_to_sbc_id = Column(
        UUID(as_uuid=True), 
        ForeignKey("internal_users.id", ondelete="RESTRICT"), 
        nullable=False,
        index=True
    )
    
    approved_by_id = Column(
        UUID(as_uuid=True), 
        ForeignKey("internal_users.id", ondelete="SET NULL")
    )
    
    # ========== EXTERNAL PO REFERENCE ==========
    external_po_number = Column(String(100), nullable=False, index=True)
    # Example: "1212121"
    
    external_po_line_numbers = Column(ARRAY(String), nullable=False)
    # Example: ["2", "3", "4"]
    # Array of line numbers to assign
    
    # ========== STATUS ==========
    status = Column(
        SQLEnum(AssignmentStatus),
        nullable=False, 
        default=AssignmentStatus.DRAFT,
        index=True
    )
    
    # ========== NOTES & REMARKS ==========
    assignment_notes = Column(Text)
    # PM's notes for SBC (e.g., "Urgent - complete by end of month")
    
    rejection_reason = Column(Text)
    # If rejected, why?
    
    approver_remarks = Column(Text)
    # Approver's comments
    
    # ========== TIMESTAMPS ==========
    created_at = Column(
        DateTime(timezone=True), 
        server_default=func.now(), 
        nullable=False
    )
    
    updated_at = Column(
        DateTime(timezone=True), 
        server_default=func.now(), 
        onupdate=func.now(), 
        nullable=False
    )
    
    submitted_at = Column(DateTime(timezone=True))
    # When PM submitted for approval
    
    approved_at = Column(DateTime(timezone=True))
    # When approved
    
    rejected_at = Column(DateTime(timezone=True))
    # When rejected
    
    # ========== RELATIONSHIPS ==========
    created_by = relationship(
        "InternalUser", 
        foreign_keys=[created_by_pm_id],
        backref="created_assignments"
    )
    
    assigned_to = relationship(
        "InternalUser", 
        foreign_keys=[assigned_to_sbc_id],
        backref="received_assignments"
    )
    
    approved_by = relationship(
        "InternalUser", 
        foreign_keys=[approved_by_id],
        backref="approved_assignments"
    )
    
    # ========== INDEXES ==========
    __table_args__ = (
        Index('idx_assignment_status', 'status'),
        Index('idx_assignment_pm', 'created_by_pm_id', 'status'),
        Index('idx_assignment_sbc', 'assigned_to_sbc_id', 'status'),
        Index('idx_assignment_external_po', 'external_po_number'),
        Index('idx_assignment_created', 'created_at'),
    )
    
    def __repr__(self):
        return f"<Assignment {self.internal_po_id} ({self.status.value})>"


