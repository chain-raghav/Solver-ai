from sqlalchemy import (
    Column,
    BigInteger,
    Integer,
    String,
    Text,
    Boolean,
    Float,
    ForeignKey,
    DateTime
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from backend.database.database import Base


class Student(Base):
    __tablename__ = "students"

    id = Column(BigInteger, primary_key=True, index=True)
    student_id = Column(String(50), unique=True, nullable=False)
    name = Column(String(100), nullable=False)
    email = Column(String(150), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    is_email_verified = Column(Boolean, default=False)
    created_at = Column(DateTime, server_default=func.now())

    complaints = relationship(
        "Complaint",
        back_populates="student"
    )


class Admin(Base):
    __tablename__ = "admins"

    id = Column(BigInteger, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    email = Column(String(150), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(50), default="admin")
    created_at = Column(DateTime, server_default=func.now())

    assigned_complaints = relationship(
        "Complaint",
        back_populates="assigned_admin_user"
    )

    complaint_updates = relationship(
        "ComplaintUpdate",
        back_populates="admin"
    )





class Complaint(Base):
    __tablename__ = "complaints"

    id = Column(BigInteger, primary_key=True, index=True)

    student_id = Column(
        BigInteger,
        ForeignKey("students.id"),
        nullable=False
    )

    title = Column(String(255))
    complaint_text = Column(Text, nullable=False)
    is_anonymous = Column(Boolean, default=False)

    # Location details
    building = Column(String(100))
    room_number = Column(String(100))
    campus_location = Column(String(255))

    # ML predicted fields (Model 1 & Model 2 + context extractors)
    category = Column(String(100))
    category_confidence = Column(Float)

    urgency = Column(String(20))
    urgency_confidence = Column(Float)

    affected_count = Column(String(100), default="Individual")
    duration = Column(String(100))
    priority_score = Column(Float)

    # Department & Admin workflow
    assigned_department = Column(String(100))
    assigned_admin = Column(
        BigInteger,
        ForeignKey("admins.id")
    )

    status = Column(String(30), default="Pending")

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    resolved_at = Column(DateTime)

    student = relationship(
        "Student",
        back_populates="complaints"
    )

    assigned_admin_user = relationship(
        "Admin",
        back_populates="assigned_complaints"
    )

    updates = relationship(
        "ComplaintUpdate",
        back_populates="complaint"
    )

class ComplaintUpdate(Base):
    __tablename__ = "complaint_updates"

    id = Column(BigInteger, primary_key=True, index=True)

    complaint_id = Column(
        BigInteger,
        ForeignKey("complaints.id"),
        nullable=False
    )

    admin_id = Column(
        BigInteger,
        ForeignKey("admins.id"),
        nullable=False
    )

    old_status = Column(String(30))
    new_status = Column(String(30))
    remarks = Column(Text)

    created_at = Column(DateTime, server_default=func.now())

    complaint = relationship(
        "Complaint",
        back_populates="updates"
    )

    admin = relationship(
        "Admin",
        back_populates="complaint_updates"
    )





class StudentDevice(Base):
    __tablename__ = "student_devices"

    id = Column(BigInteger, primary_key=True, index=True)

    student_id = Column(
        BigInteger,
        ForeignKey("students.id"),
        nullable=False
    )

    device_name = Column(String(100))
    device_identifier = Column(String(255), nullable=False)
    device_token_hash = Column(String(255))

    is_trusted = Column(Boolean, default=True)

    created_at = Column(DateTime, server_default=func.now())
    last_used_at = Column(DateTime)
    revoked_at = Column(DateTime)

    student = relationship("Student")


class OTPVerification(Base):
    __tablename__ = "otp_verifications"

    id = Column(BigInteger, primary_key=True, index=True)

    student_id = Column(
        BigInteger,
        ForeignKey("students.id")
    )

    email = Column(String(150), nullable=False)
    otp_hash = Column(String(255), nullable=False)
    purpose = Column(String(30), nullable=False)

    expires_at = Column(DateTime, nullable=False)
    attempts = Column(Integer, default=0)

    verified_at = Column(DateTime)
    consumed_at = Column(DateTime)
    created_at = Column(DateTime, server_default=func.now())

    student = relationship("Student")


class DeviceRequest(Base):
    __tablename__ = "device_requests"

    id = Column(BigInteger, primary_key=True, index=True)

    student_id = Column(
        BigInteger,
        ForeignKey("students.id"),
        nullable=False
    )

    request_token_hash = Column(String(255), nullable=False)
    expires_at = Column(DateTime, nullable=False)

    approved_at = Column(DateTime)

    approved_by_device = Column(
        BigInteger,
        ForeignKey("student_devices.id")
    )

    status = Column(String(20), default="pending")
    created_at = Column(DateTime, server_default=func.now())

    student = relationship("Student")

    approved_device = relationship("StudentDevice")    