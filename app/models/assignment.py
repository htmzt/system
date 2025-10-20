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
    """
    Assignment status workflow:
    
    DRAFT → PENDING_PD_APPROVAL → PENDING_ADMIN_APPROVAL → APPROVED
              ↓                          ↓
           REJECTED                   REJECTED
    """
    DRAFT = "DRAFT"                              # PM is editing
    PENDING_PD_APPROVAL = "PENDING_PD_APPROVAL"  # Waiting for PD (Level 1)
    PENDING_ADMIN_APPROVAL = "PENDING_ADMIN_APPROVAL"  # Waiting for Admin (Level 2)
    APPROVED = "APPROVED"                        # Fully approved, SBC can see
    REJECTED = "REJECTED"                        # Rejected by PD or Admin
    CANCELLED = "CANCELLED"                      # Cancelled by PM

# ============================================================================
# ASSIGNMENT MODEL
# ============================================================================

class Assignment(Base):
    """
    Assignment Model - Assigns PO lines to SBCs with two-level approval
    
    Workflow:
    1. PM creates assignment → DRAFT
    2. PM submits → PENDING_PD_APPROVAL
    3. PD approves → PENDING_ADMIN_APPROVAL
    4. Admin approves → APPROVED (SBC can see it)
    
    At any approval stage, it can be REJECTED (goes back to PM)
    """
    __tablename__ = "assignments"
    
    # ========== PRIMARY KEY ==========
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # ========== INTERNAL PO ID ==========
    internal_po_id = Column(String(50), unique=True, nullable=False, index=True)
    # Format: PO-SIB-YYYYMMDD-XXX (e.g., PO-SIB-20251020-001)
    
    # ========== WHO ==========
    created_by_pm_id = Column(
        UUID(as_uuid=True), 
        ForeignKey("internal_users.id", ondelete="RESTRICT"), 
        nullable=False,
        index=True
    )
    # PM who created this assignment
    
    assigned_to_sbc_id = Column(
        UUID(as_uuid=True), 
        ForeignKey("internal_users.id", ondelete="RESTRICT"), 
        nullable=False,
        index=True
    )
    # SBC who will do the work
    
    # Approval tracking
    pd_approved_by_id = Column(
        UUID(as_uuid=True), 
        ForeignKey("internal_users.id", ondelete="SET NULL")
    )
    # PD who gave Level 1 approval
    
    admin_approved_by_id = Column(
        UUID(as_uuid=True), 
        ForeignKey("internal_users.id", ondelete="SET NULL")
    )
    # Admin who gave Level 2 approval
    
    rejected_by_id = Column(
        UUID(as_uuid=True), 
        ForeignKey("internal_users.id", ondelete="SET NULL")
    )
    # Who rejected (PD or Admin)
    
    # ========== EXTERNAL PO REFERENCE ==========
    external_po_number = Column(String(100), nullable=False, index=True)
    # External PO number (e.g., "1212121")
    
    external_po_line_numbers = Column(ARRAY(String), nullable=False)
    # Array of line numbers (e.g., ["2", "3", "4"])
    
    # ========== STATUS ==========
    status = Column(
        SQLEnum(AssignmentStatus),
        nullable=False, 
        default=AssignmentStatus.DRAFT,
        index=True
    )
    
    # ========== NOTES & REMARKS ==========
    assignment_notes = Column(Text)
    # PM's notes for the SBC
    
    pd_remarks = Column(Text)
    # PD's remarks when approving/rejecting (Level 1)
    
    admin_remarks = Column(Text)
    # Admin's remarks when approving/rejecting (Level 2)
    
    rejection_reason = Column(Text)
    # Detailed reason if rejected
    
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
    
    pd_approved_at = Column(DateTime(timezone=True))
    # When PD approved (Level 1)
    
    admin_approved_at = Column(DateTime(timezone=True))
    # When Admin approved (Level 2)
    
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
    
    pd_approved_by = relationship(
        "InternalUser", 
        foreign_keys=[pd_approved_by_id],
        backref="pd_approved_assignments"
    )
    
    admin_approved_by = relationship(
        "InternalUser", 
        foreign_keys=[admin_approved_by_id],
        backref="admin_approved_assignments"
    )
    
    rejected_by = relationship(
        "InternalUser", 
        foreign_keys=[rejected_by_id],
        backref="rejected_assignments"
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