# app/api/v1/assignments.py
"""
Assignment API Routes

Endpoints:
- POST /assignments/bulk - Create assignments from selected PO lines (PM)
- POST /assignments - Create single assignment (PM)
- GET /assignments/my - Get PM's assignments
- GET /assignments/pending - Get pending approvals (Approver)
- GET /assignments/my-work - Get SBC's work
- GET /assignments/{id} - Get assignment details
- PUT /assignments/{id} - Update assignment (DRAFT only)
- POST /assignments/{id}/submit - Submit for approval (PM)
- POST /assignments/{id}/approve - Approve (Approver)
- POST /assignments/{id}/reject - Reject (Approver)
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import Optional, List
from uuid import UUID

from app.api.deps import (
    get_db,
    get_current_active_user,
    get_current_pm_or_admin,
    get_current_approver
)
from app.models.auth import InternalUser
from app.models.assignment import Assignment
from app.schemas.assignment import (
    BulkAssignmentCreate,
    BulkAssignmentCreateResponse,
    AssignmentCreate,
    AssignmentUpdate,
    AssignmentApprove,
    AssignmentReject,
    AssignmentResponse,
    AssignmentListResponse
)
from app.schemas.auth import MessageResponse
from app.services.assignment_service import AssignmentService
from app.core.permissions import is_admin, UserRole


router = APIRouter(prefix="/assignments", tags=["Assignments"])


# ============================================================================
# BULK CREATE (Main Endpoint - Frontend Uses This)
# ============================================================================

@router.post("/bulk", response_model=BulkAssignmentCreateResponse, status_code=status.HTTP_201_CREATED)
def bulk_create_assignments(
    bulk_data: BulkAssignmentCreate,
    current_user: InternalUser = Depends(get_current_pm_or_admin),
    db: Session = Depends(get_db)
):
    """
    Create assignments from selected PO lines (PM/Admin only)
    
    User selects multiple PO lines (can be from different PO numbers).
    System automatically groups by PO number and creates one assignment per PO.
    
    Example:
        Input: 5 PO lines (3 from PO 1212121, 2 from PO 1313131)
        Output: 2 assignments created
    
    Args:
        bulk_data: Selected PO lines + SBC + notes
        
    Returns:
        Summary of created assignments
        
    Requires:
        PM or Admin role
    """
    assignment_service = AssignmentService(db)
    result = assignment_service.bulk_create_assignments(
        bulk_data=bulk_data,
        created_by_pm_id=current_user.id
    )
    
    return result


# ============================================================================
# SINGLE CREATE (Manual - For Specific Cases)
# ============================================================================

@router.post("", response_model=AssignmentResponse, status_code=status.HTTP_201_CREATED)
def create_assignment(
    assignment_data: AssignmentCreate,
    current_user: InternalUser = Depends(get_current_pm_or_admin),
    db: Session = Depends(get_db)
):
    """
    Create a single assignment manually (PM/Admin only)
    
    For specific use cases where you want to manually specify PO number and lines.
    Most users should use /bulk endpoint instead.
    
    Requires:
        PM or Admin role
    """
    assignment_service = AssignmentService(db)
    assignment = assignment_service.create_assignment(
        assignment_data=assignment_data,
        created_by_pm_id=current_user.id
    )
    
    return assignment


# ============================================================================
# UPDATE ASSIGNMENT
# ============================================================================

@router.put("/{assignment_id}", response_model=AssignmentResponse)
def update_assignment(
    assignment_id: UUID,
    update_data: AssignmentUpdate,
    current_user: InternalUser = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Update assignment (only DRAFT status)
    
    Can update:
    - PO line numbers
    - Assigned SBC
    - Assignment notes
    
    Args:
        assignment_id: Assignment UUID
        update_data: Fields to update
        
    Returns:
        Updated assignment
        
    Requires:
        Must be creator or Admin
    """
    assignment_service = AssignmentService(db)
    assignment = assignment_service.update_assignment(
        assignment_id=assignment_id,
        update_data=update_data,
        user_id=current_user.id
    )
    
    return assignment


# ============================================================================
# SUBMIT FOR APPROVAL
# ============================================================================

@router.post("/{assignment_id}/submit", response_model=AssignmentResponse)
def submit_assignment(
    assignment_id: UUID,
    current_user: InternalUser = Depends(get_current_pm_or_admin),
    db: Session = Depends(get_db)
):
    """
    Submit assignment for approval
    
    Changes status: DRAFT → PENDING_APPROVAL
    
    Args:
        assignment_id: Assignment UUID
        
    Returns:
        Updated assignment
        
    Requires:
        Must be creator
    """
    assignment_service = AssignmentService(db)
    assignment = assignment_service.submit_for_approval(
        assignment_id=assignment_id,
        user_id=current_user.id
    )
    
    return assignment


# ============================================================================
# APPROVE ASSIGNMENT
# ============================================================================

@router.post("/{assignment_id}/approve", response_model=AssignmentResponse)
def approve_assignment(
    assignment_id: UUID,
    approve_data: AssignmentApprove,
    current_user: InternalUser = Depends(get_current_approver),
    db: Session = Depends(get_db)
):
    """
    Approve assignment (Approver only)
    
    Changes status: PENDING_APPROVAL → APPROVED
    Makes assignment visible to SBC
    
    Args:
        assignment_id: Assignment UUID
        approve_data: Optional approver remarks
        
    Returns:
        Updated assignment
        
    Requires:
        Approval permission (Admin or PM with can_approve=True)
    """
    assignment_service = AssignmentService(db)
    assignment = assignment_service.approve_assignment(
        assignment_id=assignment_id,
        approver_id=current_user.id,
        remarks=approve_data.approver_remarks
    )
    
    return assignment


# ============================================================================
# REJECT ASSIGNMENT
# ============================================================================

@router.post("/{assignment_id}/reject", response_model=AssignmentResponse)
def reject_assignment(
    assignment_id: UUID,
    reject_data: AssignmentReject,
    current_user: InternalUser = Depends(get_current_approver),
    db: Session = Depends(get_db)
):
    """
    Reject assignment (Approver only)
    
    Changes status: PENDING_APPROVAL → REJECTED
    PM can then edit and resubmit
    
    Args:
        assignment_id: Assignment UUID
        reject_data: Rejection reason (required)
        
    Returns:
        Updated assignment
        
    Requires:
        Approval permission
    """
    assignment_service = AssignmentService(db)
    assignment = assignment_service.reject_assignment(
        assignment_id=assignment_id,
        approver_id=current_user.id,
        rejection_reason=reject_data.rejection_reason
    )
    
    return assignment


# ============================================================================
# GET MY ASSIGNMENTS (PM)
# ============================================================================

@router.get("/my", response_model=AssignmentListResponse)
def get_my_assignments(
    status: Optional[str] = Query(None, description="Filter by status"),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    current_user: InternalUser = Depends(get_current_pm_or_admin),
    db: Session = Depends(get_db)
):
    """
    Get assignments created by current PM
    
    Query Parameters:
        - status: Filter by status (DRAFT, PENDING_APPROVAL, APPROVED, etc.)
        - page: Page number
        - per_page: Items per page
        
    Returns:
        Paginated list of PM's assignments
        
    Requires:
        PM or Admin role
    """
    assignment_service = AssignmentService(db)
    
    skip = (page - 1) * per_page
    
    assignments = assignment_service.get_assignments_for_pm(
        pm_id=current_user.id,
        status=status,
        skip=skip,
        limit=per_page
    )
    
    # Count total
    total_query = db.query(Assignment).filter(
        Assignment.created_by_pm_id == current_user.id
    )
    if status:
        total_query = total_query.filter(Assignment.status == status)
    total = total_query.count()
    
    total_pages = (total + per_page - 1) // per_page
    
    return {
        "assignments": assignments,
        "total": total,
        "page": page,
        "per_page": per_page,
        "total_pages": total_pages
    }


# ============================================================================
# GET PENDING APPROVALS (Approver)
# ============================================================================

@router.get("/pending", response_model=AssignmentListResponse)
def get_pending_approvals(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    current_user: InternalUser = Depends(get_current_approver),
    db: Session = Depends(get_db)
):
    """
    Get all pending approval assignments (Approver only)
    
    Returns:
        Paginated list of assignments waiting for approval
        
    Requires:
        Approval permission
    """
    assignment_service = AssignmentService(db)
    
    skip = (page - 1) * per_page
    
    assignments = assignment_service.get_pending_approvals(
        skip=skip,
        limit=per_page
    )
    
    # Count total
    from app.models.assignment import AssignmentStatus
    total = db.query(Assignment).filter(
        Assignment.status == AssignmentStatus.PENDING_APPROVAL
    ).count()
    
    total_pages = (total + per_page - 1) // per_page
    
    return {
        "assignments": assignments,
        "total": total,
        "page": page,
        "per_page": per_page,
        "total_pages": total_pages
    }


# ============================================================================
# GET MY WORK (SBC)
# ============================================================================

@router.get("/my-work", response_model=AssignmentListResponse)
def get_my_work(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    current_user: InternalUser = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get assignments for current SBC (SBC only)
    
    Returns only APPROVED assignments assigned to this SBC
    
    Returns:
        Paginated list of SBC's work
        
    Requires:
        SBC role
    """
    # Must be SBC
    if current_user.role != UserRole.SBC:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This endpoint is for SBC users only"
        )
    
    assignment_service = AssignmentService(db)
    
    skip = (page - 1) * per_page
    
    assignments = assignment_service.get_assignments_for_sbc(
        sbc_id=current_user.id,
        skip=skip,
        limit=per_page
    )
    
    # Count total
    from app.models.assignment import AssignmentStatus
    total = db.query(Assignment).filter(
        Assignment.assigned_to_sbc_id == current_user.id,
        Assignment.status == AssignmentStatus.APPROVED
    ).count()
    
    total_pages = (total + per_page - 1) // per_page
    
    return {
        "assignments": assignments,
        "total": total,
        "page": page,
        "per_page": per_page,
        "total_pages": total_pages
    }


# ============================================================================
# GET ASSIGNMENT BY ID
# ============================================================================

@router.get("/{assignment_id}", response_model=AssignmentResponse)
def get_assignment(
    assignment_id: UUID,
    current_user: InternalUser = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get assignment by ID
    
    Access rules:
    - Admin: Can view any assignment
    - PM: Can view own assignments
    - Approver: Can view pending assignments
    - SBC: Can view approved assignments assigned to them
    
    Args:
        assignment_id: Assignment UUID
        
    Returns:
        Assignment details
    """
    assignment_service = AssignmentService(db)
    assignment = assignment_service.get_assignment_by_id(assignment_id)
    
    if not assignment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assignment not found"
        )
    
    # Check access permissions
    can_view = False
    
    # Admin can view all
    if is_admin(current_user):
        can_view = True
    # Creator can view
    elif str(assignment.created_by_pm_id) == str(current_user.id):
        can_view = True
    # Approver can view pending
    elif current_user.can_approve and assignment.status.value == "PENDING_APPROVAL":
        can_view = True
    # SBC can view approved assignments assigned to them
    elif (current_user.role == UserRole.SBC and 
          str(assignment.assigned_to_sbc_id) == str(current_user.id) and
          assignment.status.value == "APPROVED"):
        can_view = True
    
    if not can_view:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view this assignment"
        )
    
    return assignment