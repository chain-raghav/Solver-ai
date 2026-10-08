from typing import Optional, Dict, Any
from pydantic import BaseModel, Field


class ComplaintLocation(BaseModel):
    building: Optional[str] = None
    room_number: Optional[str] = None
    campus_location: Optional[str] = None


class ComplaintCreateRequest(BaseModel):
    title: Optional[str] = None
    complaint_text: str = Field(min_length=5)
    is_anonymous: bool = False
    building: Optional[str] = None
    room_number: Optional[str] = None
    campus_location: Optional[str] = None
    location: Optional[Dict[str, Any]] = None