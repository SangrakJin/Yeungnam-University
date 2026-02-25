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
