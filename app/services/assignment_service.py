# app/services/assignment_service.py
"""
Assignment Service

This service handles:
- Bulk assignment creation (groups by PO number automatically)
- Single assignment creation
- Submit for approval
- Approve/reject assignments
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
    """Assignment management service"""
    
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
        
        Args:
            bulk_data: Selected PO lines + SBC ID + notes
            created_by_pm_id: PM creating the assignments
            
        Returns:
            Dictionary with created assignments summary
            
        Example:
            Input: 5 PO lines (3 from PO 1212121, 2 from PO 1313131)
            Output: 2 assignments created
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
        """
        Create a single assignment manually
        
        Args:
            assignment_data: Assignment data
            created_by_pm_id: PM creating the assignment
            
        Returns:
            Created assignment
        """
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
        """
        Update assignment (only in DRAFT status)
        
        Args:
            assignment_id: Assignment UUID
            update_data: Fields to update
            user_id: User making the update
            
        Returns:
            Updated assignment
        """
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
            # Check if user is admin
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
            # Validate new SBC
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
        """
        Submit assignment for approval
        
        Args:
            assignment_id: Assignment UUID
            user_id: User submitting (must be creator)
            
        Returns:
            Updated assignment
        """
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
        assignment.status = AssignmentStatus.PENDING_APPROVAL
        assignment.submitted_at = datetime.now(timezone.utc)
        
        self.db.commit()
        self.db.refresh(assignment)
        
        return assignment
    
    # ========================================================================
    # APPROVE ASSIGNMENT
    # ========================================================================
    
    def approve_assignment(
        self,
        assignment_id: uuid.UUID,
        approver_id: uuid.UUID,
        remarks: Optional[str] = None
    ) -> Assignment:
        """
        Approve assignment
        
        Args:
            assignment_id: Assignment UUID
            approver_id: User approving (must have approval permission)
            remarks: Optional approver remarks
            
        Returns:
            Updated assignment
        """
        assignment = self.get_assignment_by_id(assignment_id)
        
        if not assignment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Assignment not found"
            )
        
        # Must be PENDING_APPROVAL
        if assignment.status != AssignmentStatus.PENDING_APPROVAL:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot approve assignment in {assignment.status.value} status"
            )
        
        # Update status
        assignment.status = AssignmentStatus.APPROVED
        assignment.approved_by_id = approver_id
        assignment.approved_at = datetime.now(timezone.utc)
        assignment.approver_remarks = remarks
        
        self.db.commit()
        self.db.refresh(assignment)
        
        return assignment
    
    # ========================================================================
    # REJECT ASSIGNMENT
    # ========================================================================
    
    def reject_assignment(
        self,
        assignment_id: uuid.UUID,
        approver_id: uuid.UUID,
        rejection_reason: str
    ) -> Assignment:
        """
        Reject assignment
        
        Args:
            assignment_id: Assignment UUID
            approver_id: User rejecting
            rejection_reason: Reason for rejection
            
        Returns:
            Updated assignment
        """
        assignment = self.get_assignment_by_id(assignment_id)
        
        if not assignment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Assignment not found"
            )
        
        # Must be PENDING_APPROVAL
        if assignment.status != AssignmentStatus.PENDING_APPROVAL:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot reject assignment in {assignment.status.value} status"
            )
        
        # Update status
        assignment.status = AssignmentStatus.REJECTED
        assignment.rejected_at = datetime.now(timezone.utc)
        assignment.rejection_reason = rejection_reason
        assignment.approver_remarks = rejection_reason
        
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
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[Assignment]:
        """Get assignments for SBC (only APPROVED)"""
        query = self.db.query(Assignment).filter(
            Assignment.assigned_to_sbc_id == sbc_id,
            Assignment.status == AssignmentStatus.APPROVED
        )
        
        return query.order_by(Assignment.approved_at.desc()).offset(skip).limit(limit).all()
    
    def get_pending_approvals(
        self,
        skip: int = 0,
        limit: int = 100
    ) -> List[Assignment]:
        """Get all pending approval assignments"""
        return self.db.query(Assignment).filter(
            Assignment.status == AssignmentStatus.PENDING_APPROVAL
        ).order_by(Assignment.submitted_at.asc()).offset(skip).limit(limit).all()
    
    # ========================================================================
    # HELPER METHODS
    # ========================================================================
    
    def _group_lines_by_po_number(
        self,
        po_lines: List[POLineSelection]
    ) -> Dict[str, List[str]]:
        """
        Group PO lines by PO number
        
        Args:
            po_lines: List of selected PO lines
            
        Returns:
            Dictionary: {po_number: [line1, line2, ...]}
            
        Example:
            Input: [
                {po_number: "1212121", po_line: "2"},
                {po_number: "1212121", po_line: "3"},
                {po_number: "1313131", po_line: "6"}
            ]
            
            Output: {
                "1212121": ["2", "3"],
                "1313131": ["6"]
            }
        """
        grouped = defaultdict(list)
        for line in po_lines:
            grouped[line.po_number].append(line.po_line)
        return dict(grouped)
    
    def _check_lines_not_assigned(
        self,
        grouped_lines: Dict[str, List[str]]
    ) -> None:
        """
        Check if any PO lines are already assigned
        
        Raises:
            HTTPException: If any line is already assigned
        """
        for po_number, line_numbers in grouped_lines.items():
            # Check if any line is in an existing assignment
            existing = self.db.query(Assignment).filter(
                Assignment.external_po_number == po_number,
                Assignment.status.in_([
                    AssignmentStatus.DRAFT,
                    AssignmentStatus.PENDING_APPROVAL,
                    AssignmentStatus.APPROVED
                ])
            ).all()
            
            for assignment in existing:
                # Check if any line overlaps
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
        Example: PO-SIB-20251020-001
        """
        today = datetime.now(timezone.utc)
        date_str = today.strftime("%Y%m%d")
        
        # Find max sequence for today
        prefix = f"PO-SIB-{date_str}-"
        last_assignment = self.db.query(Assignment).filter(
            Assignment.internal_po_id.like(f"{prefix}%")
        ).order_by(Assignment.internal_po_id.desc()).first()
        
        if last_assignment:
            # Extract sequence number and increment
            last_seq = int(last_assignment.internal_po_id.split("-")[-1])
            new_seq = last_seq + 1
        else:
            new_seq = 1
        
        return f"{prefix}{new_seq:03d}"