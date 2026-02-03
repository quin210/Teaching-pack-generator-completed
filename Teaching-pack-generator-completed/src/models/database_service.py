"""
Database service functions for CRUD operations
"""
from sqlalchemy.orm import Session
from sqlalchemy import and_
from typing import List, Optional
from loguru import logger
from .database_models import (
    User, Classroom, Student, Lesson, TeachingPack, WorkflowJob, UserRole
)
from .database import SessionLocal

# User operations
def get_user_by_email(db: Session, email: str) -> Optional[User]:
    return db.query(User).filter(User.email == email).first()

def get_user_by_id(db: Session, user_id: int) -> Optional[User]:
    return db.query(User).filter(User.id == user_id).first()

def create_user(db: Session, email: str, hashed_password: str, full_name: str, role: UserRole = UserRole.TEACHER) -> User:
    user = User(
        email=email,
        hashed_password=hashed_password,
        full_name=full_name,
        role=role
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    logger.info(f"User created: {user.email} (ID: {user.id})")
    return user

# Classroom operations
def get_classrooms_by_teacher(db: Session, teacher_id: int) -> List[Classroom]:
    return db.query(Classroom).filter(Classroom.teacher_id == teacher_id).all()

def get_classroom_by_id(db: Session, classroom_id: int) -> Optional[Classroom]:
    return db.query(Classroom).filter(Classroom.id == classroom_id).first()

def create_classroom(db: Session, name: str, grade: str, subject: str, student_count: int, teacher_id: int) -> Classroom:
    classroom = Classroom(
        name=name,
        grade=grade,
        subject=subject,
        student_count=student_count,
        teacher_id=teacher_id
    )
    db.add(classroom)
    db.commit()
    logger.info(f"Classroom created: {classroom.name} (ID: {classroom.id})")
    return classroom
 
def update_classroom(db: Session, classroom_id: int, name: str = None, grade: str = None, 
                    subject: str = None, student_count: int = None) -> Optional[Classroom]:
    classroom = get_classroom_by_id(db, classroom_id)
    if classroom:
        if name is not None:
            classroom.name = name
        if grade is not None:
            classroom.grade = grade
        if subject is not None:
            classroom.subject = subject
        if student_count is not None:
            classroom.student_count = student_count
        db.commit()
        db.refresh(classroom)
    return classroom

def delete_classroom(db: Session, classroom_id: int) -> bool:
    classroom = get_classroom_by_id(db, classroom_id)
    if classroom:
        db.delete(classroom)
        db.commit()
        return True
    return False

# Student operations
def get_students_by_classroom(db: Session, classroom_id: int) -> List[Student]:
    return db.query(Student).filter(Student.classroom_id == classroom_id).all()

def create_student(db: Session, student_id: str, full_name: str, email: str, classroom_id: int) -> Student:
    student = Student(
        student_id=student_id,
        full_name=full_name,
        email=email,
        classroom_id=classroom_id
    )
    db.add(student)
    db.commit()
    logger.info(f"Student created: {student.full_name} (ID: {student.id}) in Classroom {classroom_id}")
    db.refresh(student)
    return student

def get_student_by_id(db: Session, student_id: int) -> Optional[Student]:
    return db.query(Student).filter(Student.id == student_id).first()

def update_student(db: Session, student_id: int, student_code: str = None, full_name: str = None, 
                  email: str = None) -> Optional[Student]:
    student = get_student_by_id(db, student_id)
    if student:
        if student_code is not None:
            student.student_id = student_code
        if full_name is not None:
            student.full_name = full_name
        if email is not None:
            student.email = email
        db.commit()
        db.refresh(student)
    return student

def delete_student(db: Session, student_id: int) -> bool:
    student = get_student_by_id(db, student_id)
    if student:
        db.delete(student)
        db.commit()
        return True
    return False

def update_teaching_pack_output_file(db: Session, teaching_pack_id: int, output_file_path: str) -> bool:
    teaching_pack = db.query(TeachingPack).filter(TeachingPack.id == teaching_pack_id).first()
    if teaching_pack:
        teaching_pack.output_file_path = output_file_path
        db.commit()
        return True
    return False

# Lesson operations
def create_lesson(db: Session, title: str, subject: str, grade: str, classroom_id: int,
                 uploaded_by_id: int, original_filename: str, file_path: str, file_size: int = None,
                 content_hash: str = None, parsed_content: dict = None) -> Lesson:
    lesson = Lesson(
        title=title,
        subject=subject,
        grade=grade,
        classroom_id=classroom_id,
        uploaded_by_id=uploaded_by_id,
        original_filename=original_filename,
        file_path=file_path,
        file_size=file_size,
        content_hash=content_hash,
        parsed_content=parsed_content
    )
    db.add(lesson)
    db.commit()
    logger.info(f"Lesson created: {lesson.title} (ID: {lesson.id})")
    db.refresh(lesson)
    return lesson

def get_lessons_by_classroom(db: Session, classroom_id: int) -> List[Lesson]:
    return db.query(Lesson).filter(Lesson.classroom_id == classroom_id).all()

# Teaching Pack operations
def create_teaching_pack(db: Session, title: str, classroom_id: int | None, lesson_id: int,
                        created_by_id: int, group_configuration: dict = None, output_file_path: str = None) -> TeachingPack:
    teaching_pack = TeachingPack(
        title=title,
        classroom_id=classroom_id,
        lesson_id=lesson_id,
        created_by_id=created_by_id,
        group_configuration=group_configuration,
        output_file_path=output_file_path,
        status="processing"
    )
    db.add(teaching_pack)
    logger.info(f"Teaching Pack created: {teaching_pack.title} (ID: {teaching_pack.id})")
    db.commit()
    db.refresh(teaching_pack)
    return teaching_pack

def update_teaching_pack_status(db: Session, teaching_pack_id: int, status: str) -> TeachingPack:
    teaching_pack = db.query(TeachingPack).filter(TeachingPack.id == teaching_pack_id).first()
    if teaching_pack:
        teaching_pack.status = status
        if status == "completed":
            from datetime import datetime
            teaching_pack.completed_at = datetime.utcnow()
        db.commit()
        db.refresh(teaching_pack)
    return teaching_pack

# Utility functions
def get_db():
    """Get database session (for FastAPI dependency injection)"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()