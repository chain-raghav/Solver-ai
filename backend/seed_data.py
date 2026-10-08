"""Database seeder script for Campus Complaint System.
Populates admin account, demo student, and sample complaints.
"""

import os
from dotenv import load_dotenv
from pwdlib import PasswordHash
from sqlalchemy.orm import Session

from backend.database.database import SessionLocal, engine, Base
from backend.database.models import Student, Admin, Complaint, ComplaintUpdate
from backend.services.ai_service import predict_complaint_attributes

load_dotenv()
pwd_hasher = PasswordHash.recommended()


def seed():
    Base.metadata.create_all(bind=engine)
    db: Session = SessionLocal()

    try:
        # 1. Seed Administrator
        admin_email = "admin@vitbhopal.ac.in"
        admin = db.query(Admin).filter(Admin.email == admin_email).first()
        if not admin:
            admin = Admin(
                name="Dr. Rajesh Sharma",
                email=admin_email,
                password_hash=pwd_hasher.hash("admin123"),
                role="admin"
            )
            db.add(admin)
            db.commit()
            db.refresh(admin)
            print(f"[OK] Admin created: {admin_email} (Password: admin123)")
        else:
            print(f"[INFO] Admin already exists: {admin_email}")

        # 2. Seed Demo Student
        student_email = "alex.morgan@vitbhopal.ac.in"
        student = db.query(Student).filter(Student.email == student_email).first()
        if not student:
            student = Student(
                student_id="22BCE10001",
                name="Alex Morgan",
                email=student_email,
                password_hash=pwd_hasher.hash("student123"),
                is_email_verified=True
            )
            db.add(student)
            db.commit()
            db.refresh(student)
            print(f"[OK] Demo student created: {student_email} (Password: student123)")
        else:
            print(f"[INFO] Student already exists: {student_email}")

        # 3. Seed Sample Complaints if empty
        existing_count = db.query(Complaint).count()
        if existing_count < 3:
            samples = [
                {
                    "title": "Water supply disruption in Block C",
                    "text": "The water supply in Hostel Block C has not been working since yesterday morning. Washrooms on the 2nd and 3rd floors have no water.",
                    "building": "Hostel Block C",
                    "room_number": "Room 214",
                    "campus_location": "2nd Floor Washroom Wing",
                    "anonymous": False,
                    "status": "In Progress"
                },
                {
                    "title": "Flickering projector and loose wires in Room 204",
                    "text": "The overhead projector in Academic Block A Room 204 is flickering violently with sparks near the ceiling socket. Urgent repair needed.",
                    "building": "Academic Block A",
                    "room_number": "Room 204",
                    "campus_location": "2nd Floor East Wing",
                    "anonymous": False,
                    "status": "Under Review"
                },
                {
                    "title": "Mess dinner food quality issue",
                    "text": "The dinner served at Mess 2 yesterday had undercooked rice and stale vegetables. Several hostel students felt sick afterwards.",
                    "building": "Central Mess 2",
                    "room_number": "Dining Hall B",
                    "campus_location": "Ground Floor Counter 3",
                    "anonymous": True,
                    "status": "Submitted"
                },
                {
                    "title": "Wi-Fi router down in Library 3rd Floor",
                    "text": "No internet connection on the 3rd floor reading hall since 3 days. Wi-Fi router shows red blinking light.",
                    "building": "Central Library",
                    "room_number": "Hall 301",
                    "campus_location": "3rd Floor Quiet Zone",
                    "anonymous": False,
                    "status": "Resolved"
                }
            ]

            for s in samples:
                ai = predict_complaint_attributes(s["text"])
                c = Complaint(
                    student_id=student.id,
                    title=s["title"],
                    complaint_text=s["text"],
                    is_anonymous=s["anonymous"],
                    building=s["building"],
                    room_number=s["room_number"],
                    campus_location=s["campus_location"],
                    category=ai["category"],
                    category_confidence=ai["category_confidence"],
                    urgency=ai["urgency"],
                    urgency_confidence=ai["urgency_confidence"],
                    duration=ai["duration"],
                    affected_count=ai["affected_count"],
                    status=s["status"],
                    assigned_admin=admin.id,
                    assigned_department="Hostel Administration" if ai["category"] == "Hostel" else "Campus Infrastructure & Maintenance"
                )
                db.add(c)
                db.commit()
                db.refresh(c)

                # Add timeline update
                u = ComplaintUpdate(
                    complaint_id=c.id,
                    admin_id=admin.id,
                    old_status="Submitted",
                    new_status=s["status"],
                    remarks="Initial registration and AI categorization."
                )
                db.add(u)
                db.commit()

            print(f"[OK] Seeded {len(samples)} realistic complaints with AI attributes into PostgreSQL!")
        else:
            print(f"[INFO] Database already contains {existing_count} complaints.")

    finally:
        db.close()


if __name__ == "__main__":
    seed()
