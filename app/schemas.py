from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

class StartSessionReq(BaseModel):
    student_no: str = Field(min_length=1, max_length=32)
    name: str = Field(min_length=1, max_length=64)

class StartSessionRes(BaseModel):
    token: str
    expires_at: datetime

class WindowRes(BaseModel):
    start_at_kst: str
    end_at_kst: str
    is_enabled: bool
    is_open_now: bool
    now_kst: str

class ProfessorCard(BaseModel):
    id: int
    name: str
    student_count: int
    base_capacity: int
    is_full: bool
    full_message: Optional[str] = None
    total_count: int
    total_capacity: int

class ProfessorsRes(BaseModel):
    title: str
    professors: List[ProfessorCard]

class SelectReq(BaseModel):
    professor_id: int

class MySelectionRes(BaseModel):
    student_no: str
    name: str
    professor_id: Optional[int] = None
    professor_name: Optional[str] = None
    method: Optional[str] = None

class AdminAddSeatReq(BaseModel):
    professor_id: int
    count: int = Field(default=1, ge=1, le=10)

class AdminAssignReq(BaseModel):
    student_no: str
    professor_id: int

class AdminDashboardItem(BaseModel):
    professor_id: int
    professor_name: str
    student_count: int
    base_capacity: int
    extra_capacity: int
    total_count: int
    total_capacity: int

class AdminDashboardRes(BaseModel):
    window: WindowRes
    professors: List[AdminDashboardItem]
    unassigned_students: List[MySelectionRes]