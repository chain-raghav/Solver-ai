from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, or_, desc
from sqlalchemy.orm import Session
from pydantic import BaseModel

from backend.database.database import get_db
from backend.database.models import (
    Admin,
    Complaint,
    ComplaintUpdate,
    Student
)
from backend.security.auth_dependencies import require_admin


router = APIRouter(
    prefix="/admin",
    tags=["Admin"]
)


ALLOWED_STATUSES = {
    "Pending",
    "Submitted",
    "Under Review",
    "In Progress",
    "Resolved",
    "Rejected",
    "Closed"
}

ALLOWED_DEPARTMENTS = [
    "Hostel Administration",
    "Academic Department",
    "Campus Infrastructure & Maintenance",
    "IT Support & Networks",
    "Mess Administration",
    "Student Welfare & Grievance Cell",
    "Campus Security",
    "General Administration"
]


class StatusUpdateRequest(BaseModel):
    status: str
    remarks: Optional[str] = None


class DepartmentAssignRequest(BaseModel):
    department: str
    remarks: Optional[str] = None


# ---------------------------------------------------------
# ADMIN DASHBOARD OVERVIEW METRICS
# ---------------------------------------------------------

@router.get("/dashboard")
def admin_dashboard(
    current_admin=Depends(require_admin),
    db: Session = Depends(get_db)
):
    total = db.query(Complaint).count()

    pending = (
        db.query(Complaint)
        .filter(Complaint.status.in_(["Pending", "Submitted", "Under Review"]))
        .count()
    )

    in_progress = (
        db.query(Complaint)
        .filter(Complaint.status == "In Progress")
        .count()
    )

    resolved = (
        db.query(Complaint)
        .filter(Complaint.status.in_(["Resolved", "Closed"]))
        .count()
    )

    high_priority = (
        db.query(Complaint)
        .filter(Complaint.urgency.in_(["High", "Critical"]))
        .count()
    )

    # Categories breakdown
    category_counts = (
        db.query(
            Complaint.category,
            func.count(Complaint.id)
        )
        .group_by(Complaint.category)
        .all()
    )
    by_category = {
        (category or "Uncategorized"): count
        for category, count in category_counts
    }

    # Urgency breakdown
    urgency_counts = (
        db.query(
            Complaint.urgency,
            func.count(Complaint.id)
        )
        .group_by(Complaint.urgency)
        .all()
    )
    by_urgency = {
        (urgency or "Unassigned"): count
        for urgency, count in urgency_counts
    }

    # Recent 5 complaints
    recent_query = (
        db.query(Complaint)
        .order_by(Complaint.created_at.desc())
        .limit(5)
        .all()
    )
    recent = []
    for c in recent_query:
        student_display = "Anonymous" if c.is_anonymous else (c.student.name if c.student else "Student")
        recent.append({
            "id": c.id,
            "title": c.title or (c.complaint_text[:40] + "..."),
            "category": c.category,
            "urgency": c.urgency,
            "status": c.status,
            "student": student_display,
            "created_at": c.created_at
        })

    return {
        "total_complaints": total,
        "pending": pending,
        "in_progress": in_progress,
        "resolved": resolved,
        "high_priority": high_priority,
        "by_category": by_category,
        "by_urgency": by_urgency,
        "recent_complaints": recent
    }


# ---------------------------------------------------------
# GET ALL COMPLAINTS (SEARCH & FILTERED)
# ---------------------------------------------------------

@router.get("/complaints")
def get_all_complaints(
    status: Optional[str] = None,
    category: Optional[str] = None,
    urgency: Optional[str] = None,
    department: Optional[str] = None,
    is_anonymous: Optional[bool] = None,
    search: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    current_admin=Depends(require_admin),
    db: Session = Depends(get_db)
):
    if skip < 0:
        skip = 0
    if limit < 1 or limit > 100:
        limit = 50

    query = (
        db.query(Complaint)
        .join(Student, Complaint.student_id == Student.id, isouter=True)
    )

    if status and status != "All":
        query = query.filter(Complaint.status == status)

    if category and category != "All":
        query = query.filter(Complaint.category == category)

    if urgency and urgency != "All":
        query = query.filter(Complaint.urgency == urgency)

    if department and department != "All":
        query = query.filter(Complaint.assigned_department == department)

    if is_anonymous is not None:
        query = query.filter(Complaint.is_anonymous == is_anonymous)

    if search and search.strip():
        search_pattern = f"%{search.strip()}%"
        query = query.filter(
            or_(
                Complaint.complaint_text.ilike(search_pattern),
                Complaint.title.ilike(search_pattern),
                Complaint.building.ilike(search_pattern),
                Complaint.room_number.ilike(search_pattern),
                Student.student_id.ilike(search_pattern),
                Student.name.ilike(search_pattern)
            )
        )

    total = query.count()
    complaints = (
        query
        .order_by(Complaint.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )

    results = []
    for c in complaints:
        student = c.student
        if c.is_anonymous:
            student_info = {
                "student_id": None,
                "name": "Anonymous",
                "email": None,
                "is_anonymous": True
            }
        else:
            student_info = {
                "student_id": student.student_id if student else None,
                "name": student.name if student else "Student",
                "email": student.email if student else None,
                "is_anonymous": False
            }

        results.append({
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
            "building": c.building,
            "room_number": c.room_number,
            "campus_location": c.campus_location,
            "student": student_info,
            "created_at": c.created_at,
            "updated_at": c.updated_at
        })

    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "complaints": results
    }


# ---------------------------------------------------------
# GET SINGLE COMPLAINT DETAILS (WITH ANONYMITY SHIELD)
# ---------------------------------------------------------

@router.get("/complaints/{complaint_id}")
def get_complaint_details(
    complaint_id: int,
    current_admin=Depends(require_admin),
    db: Session = Depends(get_db)
):
    complaint = (
        db.query(Complaint)
        .filter(Complaint.id == complaint_id)
        .first()
    )

    if not complaint:
        raise HTTPException(
            status_code=404,
            detail="Complaint not found"
        )

    student = complaint.student
    if complaint.is_anonymous:
        student_info = {
            "student_id": None,
            "name": "Anonymous",
            "email": None,
            "is_anonymous": True
        }
    else:
        student_info = {
            "student_id": student.student_id if student else None,
            "name": student.name if student else "Student",
            "email": student.email if student else None,
            "is_anonymous": False
        }

    history = []
    for update in sorted(complaint.updates, key=lambda item: item.created_at):
        history.append({
            "id": update.id,
            "old_status": update.old_status,
            "new_status": update.new_status,
            "remarks": update.remarks,
            "admin_name": update.admin.name if update.admin else "Administrator",
            "created_at": update.created_at
        })

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
        "building": complaint.building,
        "room_number": complaint.room_number,
        "campus_location": complaint.campus_location,
        "student": student_info,
        "created_at": complaint.created_at,
        "updated_at": complaint.updated_at,
        "resolved_at": complaint.resolved_at,
        "timeline": history
    }


# ---------------------------------------------------------
# UPDATE STATUS
# ---------------------------------------------------------

@router.patch("/complaints/{complaint_id}/status")
def update_complaint_status(
    complaint_id: int,
    data: StatusUpdateRequest,
    current_admin=Depends(require_admin),
    db: Session = Depends(get_db)
):
    new_status = data.status.strip()
    if new_status not in ALLOWED_STATUSES:
        raise HTTPException(
            status_code=400,
            detail={"message": "Invalid status", "allowed_statuses": list(ALLOWED_STATUSES)}
        )

    complaint = (
        db.query(Complaint)
        .filter(Complaint.id == complaint_id)
        .first()
    )

    if not complaint:
        raise HTTPException(status_code=404, detail="Complaint not found")

    old_status = complaint.status
    complaint.status = new_status
    complaint.assigned_admin = current_admin.id

    if new_status in ["Resolved", "Closed"]:
        complaint.resolved_at = func.now()
    else:
        complaint.resolved_at = None

    update = ComplaintUpdate(
        complaint_id=complaint.id,
        admin_id=current_admin.id,
        old_status=old_status,
        new_status=new_status,
        remarks=data.remarks or f"Status changed from {old_status} to {new_status}"
    )

    db.add(update)
    db.commit()
    db.refresh(complaint)

    return {
        "message": "Complaint status updated successfully",
        "complaint_id": complaint.id,
        "old_status": old_status,
        "new_status": complaint.status,
        "remarks": data.remarks,
        "updated_at": complaint.updated_at,
        "resolved_at": complaint.resolved_at
    }


# ---------------------------------------------------------
# ASSIGN DEPARTMENT
# ---------------------------------------------------------

@router.patch("/complaints/{complaint_id}/assign")
def assign_department(
    complaint_id: int,
    data: DepartmentAssignRequest,
    current_admin=Depends(require_admin),
    db: Session = Depends(get_db)
):
    dept = data.department.strip()
    if dept not in ALLOWED_DEPARTMENTS:
        raise HTTPException(status_code=400, detail={"message": "Invalid department", "allowed_departments": ALLOWED_DEPARTMENTS})
    complaint = (
        db.query(Complaint)
        .filter(Complaint.id == complaint_id)
        .first()
    )

    if not complaint:
        raise HTTPException(status_code=404, detail="Complaint not found")

    old_dept = complaint.assigned_department or "Unassigned"
    complaint.assigned_department = dept

    update = ComplaintUpdate(
        complaint_id=complaint.id,
        admin_id=current_admin.id,
        old_status=complaint.status,
        new_status=complaint.status,
        remarks=data.remarks or f"Routed to department: {dept} (previously: {old_dept})"
    )

    db.add(update)
    db.commit()
    db.refresh(complaint)

    return {
        "message": f"Complaint assigned to {dept} successfully",
        "complaint_id": complaint.id,
        "assigned_department": complaint.assigned_department
    }


# ---------------------------------------------------------
# ANALYTICS & INSIGHTS
# ---------------------------------------------------------

@router.get("/analytics")
def get_analytics(
    current_admin=Depends(require_admin),
    db: Session = Depends(get_db)
):
    total = db.query(Complaint).count()
    resolved_count = db.query(Complaint).filter(Complaint.status.in_(["Resolved", "Closed"])).count()
    resolution_rate = round((resolved_count / total * 100), 1) if total > 0 else 0

    category_counts = (
        db.query(Complaint.category, func.count(Complaint.id))
        .group_by(Complaint.category)
        .all()
    )

    urgency_counts = (
        db.query(Complaint.urgency, func.count(Complaint.id))
        .group_by(Complaint.urgency)
        .all()
    )

    dept_counts = (
        db.query(Complaint.assigned_department, func.count(Complaint.id))
        .group_by(Complaint.assigned_department)
        .all()
    )

    return {
        "total_complaints": total,
        "resolved_complaints": resolved_count,
        "resolution_rate_percent": resolution_rate,
        "by_category": {cat or "Other": count for cat, count in category_counts},
        "by_urgency": {urg or "Medium": count for urg, count in urgency_counts},
        "by_department": {dept or "Unassigned": count for dept, count in dept_counts}
    }


@router.get("/ai-insights")
def get_ai_insights(
    current_admin=Depends(require_admin),
    db: Session = Depends(get_db)
):
    insights = []

    # Check top category
    top_cat = (
        db.query(Complaint.category, func.count(Complaint.id).label("c"))
        .group_by(Complaint.category)
        .order_by(desc("c"))
        .first()
    )
    if top_cat:
        insights.append({
            "type": "warning",
            "title": f"Most Active Category: {top_cat[0]}",
            "description": f"{top_cat[0]} issues represent the highest volume with {top_cat[1]} complaints reported on campus.",
            "impact": "High Volume"
        })

    # Check high urgency complaints
    high_urg = db.query(Complaint).filter(Complaint.urgency.in_(["High", "Critical"])).count()
    if high_urg > 0:
        insights.append({
            "type": "danger",
            "title": "High Priority Urgent Issues",
            "description": f"{high_urg} complaints are flagged by AI Model 2 as urgent/critical requiring rapid intervention.",
            "impact": "Needs Action"
        })

    # Check top location
    top_loc = (
        db.query(Complaint.building, func.count(Complaint.id).label("c"))
        .filter(Complaint.building.isnot(None))
        .group_by(Complaint.building)
        .order_by(desc("c"))
        .first()
    )
    if top_loc and top_loc[0]:
        insights.append({
            "type": "info",
            "title": f"Campus Hotspot: {top_loc[0]}",
            "description": f"{top_loc[0]} has received {top_loc[1]} facility complaints. A physical inspection is recommended.",
            "impact": "Facility Alert"
        })

    if not insights:
        insights.append({
            "type": "info",
            "title": "Campus Stability Normal",
            "description": "No critical issue surges detected across campus departments.",
            "impact": "Normal"
        })

    return {"insights": insights}


@router.get("/complaints/{complaint_id}/related")
def get_related_complaints(
    complaint_id: int,
    current_admin=Depends(require_admin),
    db: Session = Depends(get_db)
):
    target = db.query(Complaint).filter(Complaint.id == complaint_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="Complaint not found")

    # Find complaints in the same building or category
    related_query = (
        db.query(Complaint)
        .filter(
            Complaint.id != complaint_id,
            or_(
                (Complaint.building == target.building) if target.building else False,
                Complaint.category == target.category
            )
        )
        .order_by(Complaint.created_at.desc())
        .limit(4)
        .all()
    )

    related = []
    for r in related_query:
        related.append({
            "id": r.id,
            "title": r.title or (r.complaint_text[:40] + "..."),
            "category": r.category,
            "urgency": r.urgency,
            "status": r.status,
            "building": r.building,
            "created_at": r.created_at
        })

    return {"related_complaints": related}