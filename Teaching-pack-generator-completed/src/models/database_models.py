
"""
SQLAlchemy database models for Teaching Pack Generator
"""
import enum
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Float, Boolean, JSON, Enum
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.sql import func

Base = declarative_base()

# ============= USER MANAGEMENT =============

class UserRole(str, enum.Enum):
    ADMIN = "admin"
    TEACHER = "teacher"
    STUDENT = "student"

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=False)
    role = Column(Enum(UserRole), nullable=False, default=UserRole.TEACHER)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    classrooms = relationship("Classroom", back_populates="teacher")
    teaching_packs = relationship("TeachingPack", back_populates="created_by")
    lessons_uploaded = relationship("Lesson", foreign_keys="[Lesson.uploaded_by_id]", back_populates="uploaded_by")

# ============= CLASSROOM MANAGEMENT =============

class Classroom(Base):
    __tablename__ = "classrooms"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    grade = Column(String(50), nullable=False)
    subject = Column(String(100), nullable=False)
    student_count = Column(Integer, nullable=False)
    teacher_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    groups_configuration = Column(JSON)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    teacher = relationship("User", back_populates="classrooms")
    students = relationship("Student", back_populates="classroom", cascade="all, delete-orphan")
    lessons = relationship("Lesson", back_populates="classroom", cascade="all, delete-orphan")
    teaching_packs = relationship("TeachingPack", back_populates="classroom", cascade="all, delete-orphan")

class Student(Base):
    __tablename__ = "students"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(String(50), nullable=False)
    full_name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, index=True)
    classroom_id = Column(Integer, ForeignKey("classrooms.id"), nullable=False)
    subject_scores = Column(JSON)
    grade_level = Column(String(50))
    notes = Column(Text)
    group_id = Column(String(50))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    classroom = relationship("Classroom", back_populates="students")

# ============= WORKFLOW JOBS =============
class WorkflowJob(Base):
    __tablename__ = "workflow_jobs"

    id = Column(String(100), primary_key=True, index=True)
    status = Column(String(50), default="queued")
    progress = Column(Float, default=0.0)
    message = Column(String(500))
    result_json = Column(JSON)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)

# ============= LESSON MANAGEMENT =============
class Lesson(Base):
    __tablename__ = "lessons"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(500), nullable=False)
    subject = Column(String(100), nullable=False)
    grade = Column(String(50), nullable=False)
    classroom_id = Column(Integer, ForeignKey("classrooms.id"), nullable=True)
    uploaded_by_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    original_filename = Column(String(500), nullable=False)
    file_path = Column(String(1000), nullable=False)
    file_size = Column(Integer)
    content_hash = Column(String(64))
    parsed_content = Column(JSON)
    flashcards = Column(JSON)
    theory_questions = Column(JSON)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    classroom = relationship("Classroom", back_populates="lessons")
    uploaded_by = relationship("User", foreign_keys=[uploaded_by_id], back_populates="lessons_uploaded")
    teaching_packs = relationship("TeachingPack", back_populates="lesson", cascade="all, delete-orphan")

# ============= TEACHING PACK SYSTEM =============
class TeachingPack(Base):
    __tablename__ = "teaching_packs"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(500), nullable=False)
    classroom_id = Column(Integer, ForeignKey("classrooms.id"), nullable=True)
    lesson_id = Column(Integer, ForeignKey("lessons.id"), nullable=False)
    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    group_configuration = Column(JSON)
    lesson_summary = Column(JSON)
    skill_set = Column(JSON)
    diagnostic = Column(JSON)
    teaching_pack_data = Column(JSON)
    video_urls = Column(JSON)
    slides_urls = Column(JSON)
    flashcard_urls = Column(JSON)
    output_file_path = Column(String(500))
    status = Column(String(50), default="queued")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True))

    classroom = relationship("Classroom", back_populates="teaching_packs")
    lesson = relationship("Lesson", back_populates="teaching_packs")
    created_by = relationship("User", back_populates="teaching_packs")

