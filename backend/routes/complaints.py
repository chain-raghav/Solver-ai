from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.database.database import get_db
from backend.database.models import Complaint, ComplaintUpdate
from backend.schemas.complaints import ComplaintCreateRequest
from backend.security.auth_dependencies import require_student
from backend.services.ai_service import predict_complaint_attributes


router = APIRouter(
    prefix="/complaints",
    tags=["Complaints"]
)


# ---------------------------------------------------------
# SUBMIT / CREATE COMPLAINT (ENRICHED WITH AI)
# ---------------------------------------------------------

def _process_complaint_creation(data: ComplaintCreateRequest, current_student, db: Session):
    # Extract location details whether flat or nested
    loc = data.location or {}
    building = data.building or loc.get("building")
    room_number = data.room_number or loc.get("room_number")
    campus_location = data.campus_location or loc.get("campus_location")

    # Run AI Analysis (Model 1: Category + Model 2: Urgency + Context extractors)
    ai_insights = predict_complaint_attributes(data.complaint_text)

    # Determine default department based on category
    category_dept_map = {
        "Hostel": "Hostel Administration",
        "Academic": "Academic Department",
        "Infrastructure": "Campus Infrastructure & Maintenance",
        "Mess": "Mess Administration",
        "Harassment": "Student Welfare & Grievance Cell",
        "Facilities & Services": "Campus Infrastructure & Maintenance",
        "Maintenance": "Campus Infrastructure & Maintenance",
        "Other": "General Administration"
    }
    assigned_dept = category_dept_map.get(ai_insights["category"], "General Administration")

    complaint = Complaint(
        student_id=current_student.id,
        title=data.title or (data.complaint_text[:60] + "..." if len(data.complaint_text) > 60 else data.complaint_text),
        complaint_text=data.complaint_text,
        is_anonymous=data.is_anonymous,
        building=building,
        room_number=room_number,
        campus_location=campus_location,
        category=ai_insights["category"],
        category_confidence=ai_insights["category_confidence"],
        urgency=ai_insights["urgency"],
        urgency_confidence=ai_insights["urgency_confidence"],
        duration=ai_insights["duration"],
        affected_count=ai_insights["affected_count"],
        assigned_department=assigned_dept,
        status="Pending"
    )

    db.add(complaint)
    db.commit()
    db.refresh(complaint)

    return {
        "message": "Complaint submitted and categorized successfully",
        "complaint_id": complaint.id,
        "title": complaint.title,
        "status": complaint.status,
        "category": complaint.category,
        "category_confidence": complaint.category_confidence,
        "urgency": complaint.urgency,
        "urgency_confidence": complaint.urgency_confidence,
        "duration": complaint.duration,
        "affected_count": complaint.affected_count,
        "assigned_department": complaint.assigned_department,
        "is_anonymous": complaint.is_anonymous,
        "created_at": complaint.created_at
    }


@router.post("")
def create_complaint(
    data: ComplaintCreateRequest,
    current_student=Depends(require_student),
    db: Session = Depends(get_db)
):
    return _process_complaint_creation(data, current_student, db)


@router.post("/submit")
def submit_complaint_alias(
    data: ComplaintCreateRequest,
    current_student=Depends(require_student),
    db: Session = Depends(get_db)
):
    return _process_complaint_creation(data, current_student, db)


# ---------------------------------------------------------
# GET MY COMPLAINTS
# ---------------------------------------------------------

@router.get("")
def get_my_complaints(
    current_student=Depends(require_student),
    db: Session = Depends(get_db)
):
    complaints = (
        db.query(Complaint)
        .filter(Complaint.student_id == current_student.id)
        .order_by(Complaint.created_at.desc())
        .all()
    )

    return {
        "complaints": [
            {
                "id": c.id,
                "complaint_id": c.id,
                "title": c.title or (c.complaint_text[:50] + "..."),
                "complaint_text": c.complaint_text,
                "category": c.category,
                "category_confidence": c.category_confidence,
                "urgency": c.urgency,
                "urgency_confidence": c.urgency_confidence,
                "affected_count": c.affected_count,
                "duration": c.duration,
                "status": c.status,
                "is_anonymous": c.is_anonymous,
                "assigned_department": c.assigned_department,
                "location": {
                    "building": c.building,
                    "room_number": c.room_number,
                    "campus_location": c.campus_location
                },
                "created_at": c.created_at,
                "updated_at": c.updated_at
            }
            for c in complaints
        ]
    }


# ---------------------------------------------------------
# GET SINGLE COMPLAINT
# ---------------------------------------------------------

@router.get("/{complaint_id}")
def get_my_complaint(
    complaint_id: int,
    current_student=Depends(require_student),
    db: Session = Depends(get_db)
):
    complaint = (
        db.query(Complaint)
        .filter(
            Complaint.id == complaint_id,
            Complaint.student_id == current_student.id
        )
        .first()
    )

    if not complaint:
        raise HTTPException(
            status_code=404,
            detail="Complaint not found"
        )

    history = (
        db.query(ComplaintUpdate)
        .filter(ComplaintUpdate.complaint_id == complaint.id)
        .order_by(ComplaintUpdate.created_at.asc())
        .all()
    )

    return {
        "id": complaint.id,
        "complaint_id": complaint.id,
        "title": complaint.title or (complaint.complaint_text[:50] + "..."),
        "complaint_text": complaint.complaint_text,
        "category": complaint.category,
        "category_confidence": complaint.category_confidence,
        "urgency": complaint.urgency,
        "urgency_confidence": complaint.urgency_confidence,
        "affected_count": complaint.affected_count,
        "duration": complaint.duration,
        "status": complaint.status,
        "is_anonymous": complaint.is_anonymous,
        "assigned_department": complaint.assigned_department,
        "location": {
            "building": complaint.building,
            "room_number": complaint.room_number,
            "campus_location": complaint.campus_location
        },
        "created_at": complaint.created_at,
        "updated_at": complaint.updated_at,
        "timeline": [
            {
                "id": u.id,
                "old_status": u.old_status,
                "new_status": u.new_status,
                "remarks": u.remarks,
                "created_at": u.created_at
            }
            for u in history
        ]
    }


@router.get("/{complaint_id}/history")
def get_complaint_history(
    complaint_id: int,
    current_student=Depends(require_student),
    db: Session = Depends(get_db)
):
    complaint = (
        db.query(Complaint)
        .filter(
            Complaint.id == complaint_id,
            Complaint.student_id == current_student.id
        )
        .first()
    )

    if not complaint:
        raise HTTPException(
            status_code=404,
            detail="Complaint not found"
        )

    history = (
        db.query(ComplaintUpdate)
        .filter(ComplaintUpdate.complaint_id == complaint.id)
        .order_by(ComplaintUpdate.created_at.asc())
        .all()
    )

    return {
        "complaint_id": complaint.id,
        "current_status": complaint.status,
        "history": [
            {
                "id": update.id,
                "old_status": update.old_status,
                "new_status": update.new_status,
                "remarks": update.remarks,
                "created_at": update.created_at
            }
            for update in history
        ]
    }