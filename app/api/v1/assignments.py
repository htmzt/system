# app/api/v1/assignments.py
"""
Assignment API Routes - COMPLETE VERSION

Endpoints:
- POST /assignments/bulk - Create assignments (PM)
- POST /assignments - Create single assignment (PM)
- GET /assignments/my - Get PM's assignments
- GET /assignments/pending-pd - Pending PD approval (PD)
- GET /assignments/pending-admin - Pending Admin approval (Admin)
- GET /assignments/all - Get all assignments (Admin/PD)
- GET /assignments/my-work - Get SBC's work (SBC)
- GET /assignments/{id} - Get assignment details
- PUT /assignments/{id} - Update assignment (DRAFT only)
- POST /assignments/{id}/submit - Submit for approval
- POST /assignments/{id}/approve-level1 - PD approval
- POST /assignments/{id}/approve-level2 - Admin approval
- POST /assignments/{id}/reject - Reject assignment
- GET /assignments/stats/overview - Get statistics
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import Optional
from uuid import UUID

from app.api.deps import (
    get_db,
    get_current_active_user,
    get_current_pm_or_admin,
    get_current_level1_approver,
    get_current_level2_approver,
    get_current_admin_or_pd,
    get_current_admin_user
)
from app.models.auth import InternalUser
from app.models.assignment import Assignment, AssignmentStatus
from app.schemas.assignment import (
    BulkAssignmentCreate,
    BulkAssignmentCreateResponse,
    AssignmentCreate,
    AssignmentUpdate,
    PDApprove,
    AdminApprove,
    AssignmentReject,
    AssignmentResponse,
    AssignmentListResponse,
    AssignmentStatistics
)
from app.schemas.auth import MessageResponse
from app.services.assignment_service import AssignmentService
from app.core.permissions import is_admin, is_pd, UserRole


router = APIRouter(prefix="/assignments", tags=["Assignments"])


# ============================================================================
# BULK CREATE (Main Endpoint)
# ============================================================================

@router.post("/bulk", response_model=BulkAssignmentCreateResponse, status_code=status.HTTP_201_CREATED)
def bulk_create_assignments(
    bulk_data: BulkAssignmentCreate,
    current_user: InternalUser = Depends(get_current_pm_or_admin),
    db: Session = Depends(get_db)
):
    """
    Create assignments from selected PO lines (PM/Admin only)
    
    System automatically groups by PO number and creates one assignment per PO.
    
    Example:
        Input: 5 PO lines (3 from PO 1212121, 2 from PO 1313131)
        Output: 2 assignments created
    """
    assignment_service = AssignmentService(db)
    result = assignment_service.bulk_create_assignments(
        bulk_data=bulk_data,
        created_by_pm_id=current_user.id
    )
    
    return result


# ============================================================================
# SINGLE CREATE
# ============================================================================

@router.post("", response_model=AssignmentResponse, status_code=status.HTTP_201_CREATED)
def create_assignment(
    assignment_data: AssignmentCreate,
    current_user: InternalUser = Depends(get_current_pm_or_admin),
    db: Session = Depends(get_db)
):
    """Create a single assignment manually (PM/Admin only)"""
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
    DRAFT → PENDING_PD_APPROVAL
    """
    assignment_service = AssignmentService(db)
    assignment = assignment_service.submit_for_approval(
        assignment_id=assignment_id,
        user_id=current_user.id
    )
    return assignment


# ============================================================================
# LEVEL 1 APPROVAL (PD)
# ============================================================================

@router.post("/{assignment_id}/approve-level1", response_model=AssignmentResponse)
def approve_level1(
    assignment_id: UUID,
    approve_data: PDApprove,
    current_user: InternalUser = Depends(get_current_level1_approver),
    db: Session = Depends(get_db)
):
    """
    PD Level 1 Approval (PD only)
    PENDING_PD_APPROVAL → PENDING_ADMIN_APPROVAL
    """
    assignment_service = AssignmentService(db)
    assignment = assignment_service.approve_level1(
        assignment_id=assignment_id,
        pd_id=current_user.id,
        pd_remarks=approve_data.pd_remarks
    )
    return assignment


# ============================================================================
# LEVEL 2 APPROVAL (ADMIN)
# ============================================================================

@router.post("/{assignment_id}/approve-level2", response_model=AssignmentResponse)
def approve_level2(
    assignment_id: UUID,
    approve_data: AdminApprove,
    current_user: InternalUser = Depends(get_current_level2_approver),
    db: Session = Depends(get_db)
):
    """
    Admin Level 2 Approval (Admin only)
    PENDING_ADMIN_APPROVAL → APPROVED
    SBC can now see and work on it
    """
    assignment_service = AssignmentService(db)
    assignment = assignment_service.approve_level2(
        assignment_id=assignment_id,
        admin_id=current_user.id,
        admin_remarks=approve_data.admin_remarks
    )
    return assignment


# ============================================================================
# REJECT ASSIGNMENT
# ============================================================================

@router.post("/{assignment_id}/reject", response_model=AssignmentResponse)
def reject_assignment(
    assignment_id: UUID,
    reject_data: AssignmentReject,
    current_user: InternalUser = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Reject assignment (PD or Admin can reject)
    Returns to REJECTED status, PM can fix and resubmit
    """
    # Must be PD or Admin
    if current_user.role not in [UserRole.PD, UserRole.ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only PD or Admin can reject assignments"
        )
    
    assignment_service = AssignmentService(db)
    assignment = assignment_service.reject_assignment(
        assignment_id=assignment_id,
        rejector_id=current_user.id,
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
    """Get assignments created by current PM"""
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
# GET PENDING PD APPROVALS
# ============================================================================

@router.get("/pending-pd", response_model=AssignmentListResponse)
def get_pending_pd_approvals(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    current_user: InternalUser = Depends(get_current_level1_approver),
    db: Session = Depends(get_db)
):
    """Get assignments pending PD approval (Level 1) - PD only"""
    assignment_service = AssignmentService(db)
    
    skip = (page - 1) * per_page
    
    assignments = assignment_service.get_pending_pd_approvals(
        skip=skip,
        limit=per_page
    )
    
    total = db.query(Assignment).filter(
        Assignment.status == AssignmentStatus.PENDING_PD_APPROVAL
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
# GET PENDING ADMIN APPROVALS
# ============================================================================

@router.get("/pending-admin", response_model=AssignmentListResponse)
def get_pending_admin_approvals(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    current_user: InternalUser = Depends(get_current_level2_approver),
    db: Session = Depends(get_db)
):
    """Get assignments pending Admin approval (Level 2) - Admin only"""
    assignment_service = AssignmentService(db)
    
    skip = (page - 1) * per_page
    
    assignments = assignment_service.get_pending_admin_approvals(
        skip=skip,
        limit=per_page
    )
    
    total = db.query(Assignment).filter(
        Assignment.status == AssignmentStatus.PENDING_ADMIN_APPROVAL
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
# GET ALL ASSIGNMENTS (ADMIN/PD)
# ============================================================================

@router.get("/all", response_model=AssignmentListResponse)
def get_all_assignments(
    status: Optional[str] = Query(None, description="Filter by status"),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    current_user: InternalUser = Depends(get_current_admin_or_pd),
    db: Session = Depends(get_db)
):
    """Get all assignments (Admin/PD only)"""
    assignment_service = AssignmentService(db)
    
    skip = (page - 1) * per_page
    
    assignments = assignment_service.get_all_assignments(
        status=status,
        skip=skip,
        limit=per_page
    )
    
    # Count total
    total_query = db.query(Assignment)
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
# GET MY WORK (SBC)
# ============================================================================

@router.get("/my-work", response_model=AssignmentListResponse)
def get_my_work(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    current_user: InternalUser = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get assignments for current SBC (APPROVED only)"""
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
    - Admin/PD: Can view any assignment
    - PM: Can view own assignments
    - SBC: Can view approved assignments assigned to them
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
    
    # Admin/PD can view all
    if is_admin(current_user) or is_pd(current_user):
        can_view = True
    # Creator can view
    elif str(assignment.created_by_pm_id) == str(current_user.id):
        can_view = True
    # SBC can view approved assignments assigned to them
    elif (current_user.role == UserRole.SBC and 
          str(assignment.assigned_to_sbc_id) == str(current_user.id) and
          assignment.status == AssignmentStatus.APPROVED):
        can_view = True
    
    if not can_view:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view this assignment"
        )
    
    return assignment


# ============================================================================
# GET STATISTICS
# ============================================================================

@router.get("/stats/overview", response_model=AssignmentStatistics)
def get_assignment_statistics(
    current_user: InternalUser = Depends(get_current_admin_or_pd),
    db: Session = Depends(get_db)
):
    """Get assignment statistics (Admin/PD only)"""
    
    total = db.query(Assignment).count()
    
    # Count by status
    draft = db.query(Assignment).filter(Assignment.status == AssignmentStatus.DRAFT).count()
    pending_pd = db.query(Assignment).filter(Assignment.status == AssignmentStatus.PENDING_PD_APPROVAL).count()
    pending_admin = db.query(Assignment).filter(Assignment.status == AssignmentStatus.PENDING_ADMIN_APPROVAL).count()
    approved = db.query(Assignment).filter(Assignment.status == AssignmentStatus.APPROVED).count()
    rejected = db.query(Assignment).filter(Assignment.status == AssignmentStatus.REJECTED).count()
    
    return {
        "total_assignments": total,
        "by_status": {
            "DRAFT": draft,
            "PENDING_PD_APPROVAL": pending_pd,
            "PENDING_ADMIN_APPROVAL": pending_admin,
            "APPROVED": approved,
            "REJECTED": rejected
        },
        "pending_pd_approval": pending_pd,
        "pending_admin_approval": pending_admin,
        "approved": approved,
        "rejected": rejected,
        "draft": draft
    }