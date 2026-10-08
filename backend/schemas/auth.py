from pydantic import BaseModel, EmailStr, field_validator


class StudentRegisterRequest(BaseModel):
    email: EmailStr

    @field_validator("email")
    @classmethod
    def validate_college_email(cls, value):
        if not value.lower().endswith("@vitbhopal.ac.in"):
            raise ValueError(
                "Only VIT Bhopal college email is allowed"
            )

        return value.lower()

    
class OTPVerifyRequest(BaseModel):
    email: EmailStr
    otp: str

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value):
        return value.lower()  

class StudentCreateRequest(BaseModel):
    email: EmailStr
    student_id: str
    name: str
    password: str

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value):
        return value.lower()

    @field_validator("student_id")
    @classmethod
    def validate_student_id(cls, value):
        value = value.strip().upper()

        if len(value) != 10:
            raise ValueError(
                "Registration number must be exactly 10 characters"
            )

        if not value.isalnum():
            raise ValueError(
                "Registration number must contain only letters and numbers"
            )

        return value



class StudentLoginRequest(BaseModel):
    email: EmailStr
    password: str

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value):
        return value.lower()    





class AdminLoginRequest(BaseModel):
    email: EmailStr
    password: str

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value):
        return value.lower()