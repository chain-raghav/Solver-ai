"""Student-specific routes: profile management and dashboard metrics."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.database.database import get_db
from backend.database.models import Complaint, Student
from backend.security.auth_dependencies import require_student

router = APIRouter(
    prefix="/student",
    tags=["Student"]
)


@router.get("/profile")
def get_student_profile(
    current_student: Student = Depends(require_student)
):
    """Return the authenticated student's profile."""
    return {
        "id": current_student.id,
        "student_id": current_student.student_id,
        "name": current_student.name,
        "email": current_student.email,
        "is_email_verified": current_student.is_email_verified,
        "created_at": current_student.created_at
    }


@router.put("/profile")
def update_student_profile(
    data: dict,
    current_student: Student = Depends(require_student),
    db: Session = Depends(get_db)
):
    """Update student name (email is immutable)."""
    if isinstance(data.get("name"), str) and data["name"].strip():
        current_student.name = data["name"].strip()
        db.commit()
        db.refresh(current_student)

    return {
        "id": current_student.id,
        "student_id": current_student.student_id,
        "name": current_student.name,
        "email": current_student.email,
        "is_email_verified": current_student.is_email_verified,
        "created_at": current_student.created_at
    }


@router.get("/dashboard/metrics")
def get_student_dashboard_metrics(
    current_student: Student = Depends(require_student),
    db: Session = Depends(get_db)
):
    """Return dashboard metrics for the authenticated student."""
    complaints = (
        db.query(Complaint)
        .filter(Complaint.student_id == current_student.id)
        .all()
    )

    total = len(complaints)
    pending = sum(1 for c in complaints if c.status in ["Pending", "Submitted", "Under Review"])
    in_progress = sum(1 for c in complaints if c.status == "In Progress")
    resolved = sum(1 for c in complaints if c.status in ["Resolved", "Closed"])
    rejected = sum(1 for c in complaints if c.status == "Rejected")

    recent = sorted(complaints, key=lambda c: c.created_at or "", reverse=True)[:4]

    return {
        "total": total,
        "pending": pending,
        "inProgress": in_progress,
        "resolved": resolved,
        "rejected": rejected,
        "recentComplaints": [
            {
                "id": c.id,
                "complaint_id": c.id,
                "title": c.title or (c.complaint_text[:50] + "..."),
                "complaint_text": c.complaint_text,
                "category": c.category,
                "urgency": c.urgency,
                "status": c.status,
                "created_at": c.created_at
            }
            for c in recent
        ]
    }
