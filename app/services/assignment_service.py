# app/services/assignment_service.py
"""
Assignment Service - COMPLETE VERSION

This service handles:
- Bulk assignment creation (groups by PO number automatically)
- Single assignment creation
- Submit for approval
- PD approval (Level 1)
- Admin approval (Level 2)
- Reject assignments
- Get assignment details with PO data
"""

from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from collections import defaultdict
import uuid

from app.models.assignment import Assignment, AssignmentStatus
from app.models.auth import InternalUser
from app.schemas.assignment import (
    BulkAssignmentCreate,
    AssignmentCreate,
    AssignmentUpdate,
    POLineSelection
)
from app.core.permissions import UserRole


class AssignmentService:
    """Assignment management service - COMPLETE"""
    
    def __init__(self, db: Session):
        self.db = db
    
    # ========================================================================
    # BULK CREATE (Main Method - Groups by PO Number)
    # ========================================================================
    
    def bulk_create_assignments(
        self,
        bulk_data: BulkAssignmentCreate,
        created_by_pm_id: uuid.UUID
    ) -> Dict[str, Any]:
        """
        Create multiple assignments from selected PO lines
        
        Automatically groups lines by PO number and creates one assignment per PO
        """
        # Validate SBC exists and has correct role
        sbc = self.db.query(InternalUser).filter(
            InternalUser.id == bulk_data.assigned_to_sbc_id,
            InternalUser.role == UserRole.SBC
        ).first()
        
        if not sbc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="SBC not found"
            )
        
        # Group PO lines by PO number
        grouped_lines = self._group_lines_by_po_number(bulk_data.po_lines)
        
        # Check for already assigned lines
        self._check_lines_not_assigned(grouped_lines)
        
        # Create one assignment per PO number
        created_assignments = []
        
        for po_number, line_numbers in grouped_lines.items():
            # Generate internal PO ID
            internal_po_id = self._generate_internal_po_id()
            
            # Create assignment
            assignment = Assignment(
                internal_po_id=internal_po_id,
                created_by_pm_id=created_by_pm_id,
                assigned_to_sbc_id=bulk_data.assigned_to_sbc_id,
                external_po_number=po_number,
                external_po_line_numbers=line_numbers,
                status=AssignmentStatus.DRAFT,
                assignment_notes=bulk_data.assignment_notes
            )
            
            self.db.add(assignment)
            created_assignments.append({
                "internal_po_id": internal_po_id,
                "external_po_number": po_number,
                "line_count": len(line_numbers),
                "lines": line_numbers
            })
        
        self.db.commit()
        
        return {
            "success": True,
            "message": f"Created {len(created_assignments)} assignment(s) successfully",
            "assignments_created": created_assignments,
            "total_assignments": len(created_assignments),
            "assigned_to_sbc_id": str(sbc.id),
            "assigned_to_sbc_name": sbc.full_name
        }
    
    # ========================================================================
    # SINGLE CREATE (Manual - For Specific Cases)
    # ========================================================================
    
    def create_assignment(
        self,
        assignment_data: AssignmentCreate,
        created_by_pm_id: uuid.UUID
    ) -> Assignment:
        """Create a single assignment manually"""
        # Validate SBC
        sbc = self.db.query(InternalUser).filter(
            InternalUser.id == assignment_data.assigned_to_sbc_id,
            InternalUser.role == UserRole.SBC
        ).first()
        
        if not sbc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="SBC not found"
            )
        
        # Check lines not already assigned
        self._check_lines_not_assigned({
            assignment_data.external_po_number: assignment_data.external_po_line_numbers
        })
        
        # Generate internal PO ID
        internal_po_id = self._generate_internal_po_id()
        
        # Create assignment
        assignment = Assignment(
            internal_po_id=internal_po_id,
            created_by_pm_id=created_by_pm_id,
            assigned_to_sbc_id=assignment_data.assigned_to_sbc_id,
            external_po_number=assignment_data.external_po_number,
            external_po_line_numbers=assignment_data.external_po_line_numbers,
            status=AssignmentStatus.DRAFT,
            assignment_notes=assignment_data.assignment_notes
        )
        
        self.db.add(assignment)
        self.db.commit()
        self.db.refresh(assignment)
        
        return assignment
    
    # ========================================================================
    # UPDATE ASSIGNMENT
    # ========================================================================
    
    def update_assignment(
        self,
        assignment_id: uuid.UUID,
        update_data: AssignmentUpdate,
        user_id: uuid.UUID
    ) -> Assignment:
        """Update assignment (only in DRAFT status)"""
        assignment = self.get_assignment_by_id(assignment_id)
        
        if not assignment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Assignment not found"
            )
        
        # Can only update DRAFT assignments
        if assignment.status != AssignmentStatus.DRAFT:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot update assignment in {assignment.status.value} status"
            )
        
        # Only creator or admin can update
        if str(assignment.created_by_pm_id) != str(user_id):
            user = self.db.query(InternalUser).filter(InternalUser.id == user_id).first()
            if not user or user.role != UserRole.ADMIN:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Not authorized to update this assignment"
                )
        
        # Update fields
        if update_data.external_po_line_numbers is not None:
            assignment.external_po_line_numbers = update_data.external_po_line_numbers
        
        if update_data.assigned_to_sbc_id is not None:
            sbc = self.db.query(InternalUser).filter(
                InternalUser.id == update_data.assigned_to_sbc_id,
                InternalUser.role == UserRole.SBC
            ).first()
            if not sbc:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="SBC not found"
                )
            assignment.assigned_to_sbc_id = update_data.assigned_to_sbc_id
        
        if update_data.assignment_notes is not None:
            assignment.assignment_notes = update_data.assignment_notes
        
        self.db.commit()
        self.db.refresh(assignment)
        
        return assignment
    
    # ========================================================================
    # SUBMIT FOR APPROVAL
    # ========================================================================
    
    def submit_for_approval(
        self,
        assignment_id: uuid.UUID,
        user_id: uuid.UUID
    ) -> Assignment:
        """Submit assignment for approval (DRAFT → PENDING_PD_APPROVAL)"""
        assignment = self.get_assignment_by_id(assignment_id)
        
        if not assignment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Assignment not found"
            )
        
        # Must be creator
        if str(assignment.created_by_pm_id) != str(user_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only creator can submit assignment"
            )
        
        # Must be DRAFT
        if assignment.status != AssignmentStatus.DRAFT:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot submit assignment in {assignment.status.value} status"
            )
        
        # Update status
        assignment.status = AssignmentStatus.PENDING_PD_APPROVAL
        assignment.submitted_at = datetime.now(timezone.utc)
        
        self.db.commit()
        self.db.refresh(assignment)
        
        return assignment
    
    # ========================================================================
    # LEVEL 1 APPROVAL (PD)
    # ========================================================================
    
    def approve_level1(
        self,
        assignment_id: uuid.UUID,
        pd_id: uuid.UUID,
        pd_remarks: Optional[str] = None
    ) -> Assignment:
        """
        PD approves assignment (Level 1)
        PENDING_PD_APPROVAL → PENDING_ADMIN_APPROVAL
        """
        assignment = self.get_assignment_by_id(assignment_id)
        
        if not assignment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Assignment not found"
            )
        
        # Must be PENDING_PD_APPROVAL
        if assignment.status != AssignmentStatus.PENDING_PD_APPROVAL:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot approve assignment in {assignment.status.value} status. Must be PENDING_PD_APPROVAL."
            )
        
        # Verify PD role
        pd = self.db.query(InternalUser).filter(InternalUser.id == pd_id).first()
        if not pd or pd.role != UserRole.PD:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only PD can give Level 1 approval"
            )
        
        # Update status
        assignment.status = AssignmentStatus.PENDING_ADMIN_APPROVAL
        assignment.pd_approved_by_id = pd_id
        assignment.pd_approved_at = datetime.now(timezone.utc)
        assignment.pd_remarks = pd_remarks
        
        self.db.commit()
        self.db.refresh(assignment)
        
        return assignment
    
    # ========================================================================
    # LEVEL 2 APPROVAL (ADMIN)
    # ========================================================================
    
    def approve_level2(
        self,
        assignment_id: uuid.UUID,
        admin_id: uuid.UUID,
        admin_remarks: Optional[str] = None
    ) -> Assignment:
        """
        Admin approves assignment (Level 2)
        PENDING_ADMIN_APPROVAL → APPROVED
        """
        assignment = self.get_assignment_by_id(assignment_id)
        
        if not assignment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Assignment not found"
            )
        
        # Must be PENDING_ADMIN_APPROVAL
        if assignment.status != AssignmentStatus.PENDING_ADMIN_APPROVAL:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot approve assignment in {assignment.status.value} status. Must be PENDING_ADMIN_APPROVAL."
            )
        
        # Verify Admin role
        admin = self.db.query(InternalUser).filter(InternalUser.id == admin_id).first()
        if not admin or admin.role != UserRole.ADMIN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only Admin can give Level 2 approval"
            )
        
        # Update status
        assignment.status = AssignmentStatus.APPROVED
        assignment.admin_approved_by_id = admin_id
        assignment.admin_approved_at = datetime.now(timezone.utc)
        assignment.admin_remarks = admin_remarks
        
        self.db.commit()
        self.db.refresh(assignment)
        
        return assignment
    
    # ========================================================================
    # REJECT ASSIGNMENT
    # ========================================================================
    
    def reject_assignment(
        self,
        assignment_id: uuid.UUID,
        rejector_id: uuid.UUID,
        rejection_reason: str
    ) -> Assignment:
        """
        Reject assignment (PD or Admin can reject)
        Returns to DRAFT status so PM can fix and resubmit
        """
        assignment = self.get_assignment_by_id(assignment_id)
        
        if not assignment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Assignment not found"
            )
        
        # Can only reject if pending approval
        if assignment.status not in [
            AssignmentStatus.PENDING_PD_APPROVAL,
            AssignmentStatus.PENDING_ADMIN_APPROVAL
        ]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot reject assignment in {assignment.status.value} status"
            )
        
        # Verify rejector is PD or Admin
        rejector = self.db.query(InternalUser).filter(InternalUser.id == rejector_id).first()
        if not rejector or rejector.role not in [UserRole.PD, UserRole.ADMIN]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only PD or Admin can reject assignments"
            )
        
        # Update status
        assignment.status = AssignmentStatus.REJECTED
        assignment.rejected_by_id = rejector_id
        assignment.rejected_at = datetime.now(timezone.utc)
        assignment.rejection_reason = rejection_reason
        
        self.db.commit()
        self.db.refresh(assignment)
        
        return assignment
    
    # ========================================================================
    # GET ASSIGNMENTS
    # ========================================================================
    
    def get_assignment_by_id(self, assignment_id: uuid.UUID) -> Optional[Assignment]:
        """Get assignment by ID"""
        return self.db.query(Assignment).filter(
            Assignment.id == assignment_id
        ).first()
    
    def get_assignments_for_pm(
        self,
        pm_id: uuid.UUID,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[Assignment]:
        """Get assignments created by PM"""
        query = self.db.query(Assignment).filter(
            Assignment.created_by_pm_id == pm_id
        )
        
        if status:
            query = query.filter(Assignment.status == status)
        
        return query.order_by(Assignment.created_at.desc()).offset(skip).limit(limit).all()
    
    def get_assignments_for_sbc(
        self,
        sbc_id: uuid.UUID,
        skip: int = 0,
        limit: int = 100
    ) -> List[Assignment]:
        """Get APPROVED assignments for SBC"""
        return self.db.query(Assignment).filter(
            Assignment.assigned_to_sbc_id == sbc_id,
            Assignment.status == AssignmentStatus.APPROVED
        ).order_by(Assignment.admin_approved_at.desc()).offset(skip).limit(limit).all()
    
    def get_pending_pd_approvals(
        self,
        skip: int = 0,
        limit: int = 100
    ) -> List[Assignment]:
        """Get assignments pending PD approval (Level 1)"""
        return self.db.query(Assignment).filter(
            Assignment.status == AssignmentStatus.PENDING_PD_APPROVAL
        ).order_by(Assignment.submitted_at.asc()).offset(skip).limit(limit).all()
    
    def get_pending_admin_approvals(
        self,
        skip: int = 0,
        limit: int = 100
    ) -> List[Assignment]:
        """Get assignments pending Admin approval (Level 2)"""
        return self.db.query(Assignment).filter(
            Assignment.status == AssignmentStatus.PENDING_ADMIN_APPROVAL
        ).order_by(Assignment.pd_approved_at.asc()).offset(skip).limit(limit).all()
    
    def get_all_assignments(
        self,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[Assignment]:
        """Get all assignments (Admin/PD only)"""
        query = self.db.query(Assignment)
        
        if status:
            query = query.filter(Assignment.status == status)
        
        return query.order_by(Assignment.created_at.desc()).offset(skip).limit(limit).all()
    
    # ========================================================================
    # HELPER METHODS
    # ========================================================================
    
    def _group_lines_by_po_number(
        self,
        po_lines: List[POLineSelection]
    ) -> Dict[str, List[str]]:
        """Group PO lines by PO number"""
        grouped = defaultdict(list)
        for line in po_lines:
            grouped[line.po_number].append(line.po_line)
        return dict(grouped)
    
    def _check_lines_not_assigned(
        self,
        grouped_lines: Dict[str, List[str]]
    ) -> None:
        """Check if any PO lines are already assigned"""
        for po_number, line_numbers in grouped_lines.items():
            existing = self.db.query(Assignment).filter(
                Assignment.external_po_number == po_number,
                Assignment.status.in_([
                    AssignmentStatus.DRAFT,
                    AssignmentStatus.PENDING_PD_APPROVAL,
                    AssignmentStatus.PENDING_ADMIN_APPROVAL,
                    AssignmentStatus.APPROVED
                ])
            ).all()
            
            for assignment in existing:
                overlap = set(line_numbers) & set(assignment.external_po_line_numbers)
                if overlap:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"PO {po_number} line(s) {', '.join(overlap)} already assigned in {assignment.internal_po_id}"
                    )
    
    def _generate_internal_po_id(self) -> str:
        """
        Generate unique internal PO ID
        Format: PO-SIB-YYYYMMDD-XXX
        """
        today = datetime.now(timezone.utc)
        date_str = today.strftime("%Y%m%d")
        prefix = f"PO-SIB-{date_str}-"
        
        last_assignment = self.db.query(Assignment).filter(
            Assignment.internal_po_id.like(f"{prefix}%")
        ).order_by(Assignment.internal_po_id.desc()).first()
        
        if last_assignment:
            last_seq = int(last_assignment.internal_po_id.split("-")[-1])
            new_seq = last_seq + 1
        else:
            new_seq = 1
        
        return f"{prefix}{new_seq:03d}"