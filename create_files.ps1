# =========================
# advisor-alloc project files generator
# =========================

New-Item -ItemType Directory -Force -Path app | Out-Null
New-Item -ItemType Directory -Force -Path app\static | Out-Null
New-Item -ItemType Directory -Force -Path scripts | Out-Null

# app/models.py
@"
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .database import Base

class AllowedStudent(Base):
    __tablename__ = "allowed_students"
    id = Column(Integer, primary_key=True)
    student_no = Column(String(32), unique=True, index=True, nullable=False)
    name = Column(String(64), nullable=False)

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    student_no = Column(String(32), unique=True, index=True, nullable=False)
    name = Column(String(64), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

class SessionToken(Base):
    __tablename__ = "sessions"
    id = Column(Integer, primary_key=True)
    token = Column(String(128), unique=True, index=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    user = relationship("User")

class Professor(Base):
    __tablename__ = "professors"
    id = Column(Integer, primary_key=True)
    name = Column(String(64), unique=True, nullable=False)
    base_capacity = Column(Integer, nullable=False, default=12)
    extra_capacity = Column(Integer, nullable=False, default=0)
    active = Column(Boolean, nullable=False, default=True)

class Selection(Base):
    __tablename__ = "selections"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True)
    professor_id = Column(Integer, ForeignKey("professors.id", ondelete="RESTRICT"), nullable=False)
    method = Column(String(16), nullable=False, default="student")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    user = relationship("User")
    professor = relationship("Professor")

class ApplicationWindow(Base):
    __tablename__ = "application_window"
    id = Column(Integer, primary_key=True)
    start_at = Column(DateTime(timezone=True), nullable=False)
    end_at = Column(DateTime(timezone=True), nullable=False)
    is_enabled = Column(Boolean, nullable=False, default=True)
"@ | Set-Content -Encoding utf8 app\models.py

# app/security.py
@"
import os
import secrets
from datetime import datetime, timedelta, timezone

ADMIN_API_KEY = os.getenv("ADMIN_API_KEY", "change-me-now")

def new_token():
    return secrets.token_urlsafe(48)

def expiry_utc(minutes=720):
    return datetime.now(timezone.utc) + timedelta(minutes=minutes)

def require_admin_key(key):
    return key == ADMIN_API_KEY
"@ | Set-Content -Encoding utf8 app\security.py

# app/services.py
@"
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

KST = ZoneInfo("Asia/Seoul")
TITLE = "2026년 1학기 바이오캡스톤디자인(생명공학과)"

def now_utc():
    return datetime.now(timezone.utc)

def utc_to_kst_str(dt):
    return dt.astimezone(KST).strftime("%Y-%m-%d %H:%M")
"@ | Set-Content -Encoding utf8 app\services.py

# scripts/import_students.py
@"
print("학생 CSV import 스크립트 placeholder")
"@ | Set-Content -Encoding utf8 scripts\import_students.py

# app/static/index.html
@"
<!doctype html>
<html>
<head><meta charset="utf-8"><title>학생 페이지</title></head>
<body>
<h1>2026년 1학기 바이오캡스톤디자인(생명공학과)</h1>
<p>학생 페이지 테스트 화면</p>
</body>
</html>
"@ | Set-Content -Encoding utf8 app\static\index.html

# app/static/admin.html
@"
<!doctype html>
<html>
<head><meta charset="utf-8"><title>관리자 페이지</title></head>
<body>
<h1>관리자 페이지</h1>
<p>관리자 테스트 화면</p>
</body>
</html>
"@ | Set-Content -Encoding utf8 app\static\admin.html

Write-Host "✅ 모든 파일 생성 완료"