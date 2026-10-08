import secrets
from backend.services.email_service import send_otp_email
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from pwdlib import PasswordHash

from backend.database.database import get_db
from backend.database.models import Student, Admin, OTPVerification
from backend.security.jwt import create_access_token
from backend.security.auth_dependencies import require_student
from backend.schemas.auth import (
    StudentRegisterRequest,
    OTPVerifyRequest,
    StudentCreateRequest,
    StudentLoginRequest,
    AdminLoginRequest
)

password_hash = PasswordHash.recommended()


router = APIRouter(
    prefix="/auth",
    tags=["Authentication"]
)


class FlexibleLoginRequest(BaseModel):
    """Accepts 'email' OR 'username' (student_id or email) + password."""
    email: Optional[str] = None
    username: Optional[str] = None
    password: str


# ---------------------------------------------------------
# STUDENT REGISTRATION (OTP FLOW)
# ---------------------------------------------------------

@router.post("/register")
def register_student(
    data: StudentRegisterRequest,
    db: Session = Depends(get_db)
):
    existing_student = (
        db.query(Student)
        .filter(Student.email == data.email)
        .first()
    )

    if existing_student:
        raise HTTPException(status_code=409, detail="Student already registered")

    previous_otps = (
        db.query(OTPVerification)
        .filter(
            OTPVerification.email == data.email,
            OTPVerification.purpose == "REGISTRATION",
            OTPVerification.verified_at.is_(None)
        )
        .all()
    )

    for previous_otp in previous_otps:
        previous_otp.consumed_at = datetime.now(timezone.utc)
        previous_otp.verified_at = previous_otp.consumed_at

    otp = str(secrets.randbelow(1000000)).zfill(6)
    otp_hash = password_hash.hash(otp)

    otp_record = OTPVerification(
        email=data.email,
        otp_hash=otp_hash,
        purpose="REGISTRATION",
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=10)
    )

    db.add(otp_record)
    db.commit()

    send_otp_email(data.email, otp)

    return {
        "message": "OTP generated successfully",
        "email": data.email
    }


@router.post("/verify-otp")
def verify_otp(
    data: OTPVerifyRequest,
    db: Session = Depends(get_db)
):
    otp_record = (
        db.query(OTPVerification)
        .filter(
            OTPVerification.email == data.email,
            OTPVerification.purpose == "REGISTRATION",
            OTPVerification.verified_at.is_(None)
        )
        .order_by(OTPVerification.created_at.desc())
        .first()
    )

    if not otp_record:
        raise HTTPException(status_code=400, detail="No valid OTP found")

    if otp_record.attempts >= 5:
        raise HTTPException(status_code=429, detail="Too many incorrect attempts. Please request a new OTP.")

    if datetime.now(timezone.utc) > otp_record.expires_at.replace(tzinfo=timezone.utc):
        raise HTTPException(status_code=400, detail="OTP has expired")

    if not password_hash.verify(data.otp, otp_record.otp_hash):
        otp_record.attempts += 1
        db.commit()
        if otp_record.attempts >= 5:
            raise HTTPException(status_code=429, detail="Too many incorrect attempts. Please request a new OTP.")
        raise HTTPException(status_code=400, detail=f"Invalid OTP. {5 - otp_record.attempts} attempts remaining")

    otp_record.verified_at = datetime.now(timezone.utc)
    db.commit()

    return {"message": "OTP verified successfully"}


@router.post("/create-account")
def create_student_account(
    data: StudentCreateRequest,
    db: Session = Depends(get_db)
):
    otp_record = (
        db.query(OTPVerification)
        .filter(
            OTPVerification.email == data.email,
            OTPVerification.purpose == "REGISTRATION",
            OTPVerification.verified_at.is_not(None),
            OTPVerification.consumed_at.is_(None)
        )
        .order_by(OTPVerification.verified_at.desc())
        .first()
    )

    if not otp_record:
        raise HTTPException(status_code=400, detail="Email has not been verified")

    existing_student = (
        db.query(Student)
        .filter(
            (Student.email == data.email) |
            (Student.student_id == data.student_id)
        )
        .first()
    )

    if existing_student:
        raise HTTPException(status_code=409, detail="Student account already exists")

    hashed_password = password_hash.hash(data.password)

    student = Student(
        student_id=data.student_id,
        name=data.name,
        email=data.email,
        password_hash=hashed_password,
        is_email_verified=True
    )

    db.add(student)
    db.commit()
    db.refresh(student)
    otp_record.consumed_at = datetime.now(timezone.utc)
    db.commit()

    return {
        "message": "Student account created successfully",
        "student_id": student.student_id,
        "email": student.email
    }


# ---------------------------------------------------------
# STUDENT LOGIN
# ---------------------------------------------------------

@router.post("/login")
def login_student(
    data: FlexibleLoginRequest,
    db: Session = Depends(get_db)
):
    """Login accepts email (frontend field) or username (student_id or email)."""
    # Determine the identifier
    identifier = (data.email or data.username or "").strip().lower()

    if not identifier:
        raise HTTPException(status_code=400, detail="Email or username is required")

    # Try email first, then student_id
    student = (
        db.query(Student)
        .filter(
            (Student.email == identifier) |
            (Student.student_id == identifier.upper())
        )
        .first()
    )

    if not student:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    if not password_hash.verify(data.password, student.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    access_token = create_access_token({
        "sub": str(student.id),
        "student_id": student.student_id,
        "role": "student"
    })

    return {
        "message": "Login successful",
        "access_token": access_token,
        "token_type": "bearer",
        "student": {
            "id": student.id,
            "student_id": student.student_id,
            "name": student.name,
            "email": student.email
        },
        "student_id": student.student_id,
        "email": student.email
    }


# ---------------------------------------------------------
# STUDENT PROFILE (Authenticated)
# ---------------------------------------------------------

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


# ---------------------------------------------------------
# ADMIN LOGIN
# ---------------------------------------------------------

@router.post("/admin/login")
def login_admin(
    data: AdminLoginRequest,
    db: Session = Depends(get_db)
):
    admin = (
        db.query(Admin)
        .filter(Admin.email == data.email)
        .first()
    )

    if not admin:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    if not password_hash.verify(data.password, admin.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    access_token = create_access_token({
        "sub": str(admin.id),
        "role": "admin"
    })

    return {
        "message": "Admin login successful",
        "access_token": access_token,
        "token_type": "bearer",
        "admin_id": admin.id,
        "name": admin.name,
        "email": admin.email,
        "role": admin.role
    }