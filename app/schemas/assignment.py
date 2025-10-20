# app/schemas/assignment.py
"""
Pydantic Schemas for Assignment System
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict
from datetime import datetime
from uuid import UUID


# ============================================================================
# PO LINE SELECTION
# ============================================================================

class POLineSelection(BaseModel):
    """
    Single PO line selected by user
    """
    po_number: str = Field(..., description="PO Number (e.g., '1212121')")
    po_line: str = Field(..., description="PO Line number (e.g., '2')")
    
    class Config:
        json_schema_extra = {
            "example": {
                "po_number": "1212121",
                "po_line": "2"
            }
        }


# ============================================================================
# BULK CREATE ASSIGNMENT
# ============================================================================

class BulkAssignmentCreate(BaseModel):
    """
    Create multiple assignments from selected PO lines
    
    User selects multiple PO lines (can be from different PO numbers).
    System automatically groups by PO number and creates one assignment per PO.
    """
    po_lines: List[POLineSelection] = Field(
        ...,
        min_length=1,
        description="List of selected PO lines (will be grouped by PO number)"
    )
    
    assigned_to_sbc_id: UUID = Field(
        ...,
        description="UUID of SBC to assign all work to"
    )
    
    assignment_notes: Optional[str] = Field(
        None,
        max_length=5000,
        description="Notes for the SBC (applies to all assignments)"
    )
    
    @validator('po_lines')
    def validate_po_lines_unique(cls, v):
        """Ensure no duplicate PO lines"""
        seen = set()
        for line in v:
            key = (line.po_number, line.po_line)
            if key in seen:
                raise ValueError(f"Duplicate PO line: {line.po_number} - {line.po_line}")
            seen.add(key)
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "po_lines": [
                    {"po_number": "1212121", "po_line": "2"},
                    {"po_number": "1212121", "po_line": "3"},
                    {"po_number": "1212121", "po_line": "4"},
                    {"po_number": "1313131", "po_line": "6"},
                    {"po_number": "1313131", "po_line": "7"}
                ],
                "assigned_to_sbc_id": "123e4567-e89b-12d3-a456-426614174000",
                "assignment_notes": "Urgent - complete by end of month"
            }
        }


# ============================================================================
# SINGLE CREATE ASSIGNMENT (for manual use)
# ============================================================================

class AssignmentCreate(BaseModel):
    """
    Create a single assignment (manual - for specific use cases)
    """
    external_po_number: str = Field(
        ..., 
        description="External PO number (e.g., '1212121')"
    )
    
    external_po_line_numbers: List[str] = Field(
        ..., 
        min_length=1,
        description="List of PO line numbers to assign (e.g., ['2', '3', '4'])"
    )
    
    assigned_to_sbc_id: UUID = Field(
        ...,
        description="UUID of SBC to assign work to"
    )
    
    assignment_notes: Optional[str] = Field(
        None,
        max_length=5000,
        description="Notes for the SBC"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "external_po_number": "1212121",
                "external_po_line_numbers": ["2", "3", "4"],
                "assigned_to_sbc_id": "123e4567-e89b-12d3-a456-426614174000",
                "assignment_notes": "Urgent - complete by end of month"
            }
        }


# ============================================================================
# BULK CREATE RESPONSE
# ============================================================================

class AssignmentCreatedSummary(BaseModel):
    """
    Summary of a single created assignment
    """
    internal_po_id: str
    external_po_number: str
    line_count: int
    lines: List[str]
    
    class Config:
        json_schema_extra = {
            "example": {
                "internal_po_id": "PO-SIB-20251020-001",
                "external_po_number": "1212121",
                "line_count": 3,
                "lines": ["2", "3", "4"]
            }
        }


class BulkAssignmentCreateResponse(BaseModel):
    """
    Response after bulk assignment creation
    """
    success: bool = True
    message: str
    assignments_created: List[AssignmentCreatedSummary]
    total_assignments: int
    assigned_to_sbc_id: UUID
    assigned_to_sbc_name: str
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "message": "Created 2 assignments successfully",
                "assignments_created": [
                    {
                        "internal_po_id": "PO-SIB-20251020-001",
                        "external_po_number": "1212121",
                        "line_count": 3,
                        "lines": ["2", "3", "4"]
                    },
                    {
                        "internal_po_id": "PO-SIB-20251020-002",
                        "external_po_number": "1313131",
                        "line_count": 2,
                        "lines": ["6", "7"]
                    }
                ],
                "total_assignments": 2,
                "assigned_to_sbc_id": "123e4567-e89b-12d3-a456-426614174000",
                "assigned_to_sbc_name": "Alpha Construction Ltd"
            }
        }


# ============================================================================
# UPDATE ASSIGNMENT
# ============================================================================

class AssignmentUpdate(BaseModel):
    """
    Update assignment (only in DRAFT status)
    """
    external_po_line_numbers: Optional[List[str]] = Field(
        None,
        min_length=1,
        description="Update line numbers"
    )
    
    assigned_to_sbc_id: Optional[UUID] = Field(
        None,
        description="Change SBC"
    )
    
    assignment_notes: Optional[str] = Field(
        None,
        max_length=5000
    )


# ============================================================================
# APPROVE / REJECT
# ============================================================================

class AssignmentApprove(BaseModel):
    """Approve assignment"""
    approver_remarks: Optional[str] = Field(None, max_length=5000)


class AssignmentReject(BaseModel):
    """Reject assignment"""
    rejection_reason: str = Field(..., min_length=1, max_length=5000)


# ============================================================================
# ASSIGNMENT RESPONSE
# ============================================================================

class AssignmentResponse(BaseModel):
    """Assignment data"""
    id: UUID
    internal_po_id: str
    created_by_pm_id: UUID
    assigned_to_sbc_id: UUID
    approved_by_id: Optional[UUID] = None
    external_po_number: str
    external_po_line_numbers: List[str]
    status: str
    assignment_notes: Optional[str] = None
    rejection_reason: Optional[str] = None
    approver_remarks: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    submitted_at: Optional[datetime] = None
    approved_at: Optional[datetime] = None
    rejected_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class AssignmentWithUsers(AssignmentResponse):
    """Assignment with user details"""
    created_by_name: Optional[str] = None
    assigned_to_name: Optional[str] = None
    approved_by_name: Optional[str] = None
    sbc_code: Optional[str] = None


class POLineDetail(BaseModel):
    """External PO line details"""
    po_line: str
    project_name: Optional[str] = None
    item_description: Optional[str] = None
    quantity: Optional[int] = None
    unit_price: Optional[float] = None
    line_amount: Optional[float] = None
    category: Optional[str] = None


class AssignmentWithPODetails(AssignmentResponse):
    """Assignment with PO line details"""
    po_lines: List[POLineDetail] = []
    total_amount: Optional[float] = None


class AssignmentListResponse(BaseModel):
    """Paginated assignment list"""
    assignments: List[AssignmentResponse]
    total: int
    page: int
    per_page: int
    total_pages: int


class AssignmentStatistics(BaseModel):
    """Assignment statistics"""
    total_assignments: int
    by_status: Dict[str, int]
    total_amount: Optional[float] = None