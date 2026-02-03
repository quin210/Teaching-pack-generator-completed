"""
Classroom management routes
Handles classroom CRUD operations and student management
"""
from fastapi import APIRouter, HTTPException, Form
from typing import List, Dict
from api.dependencies import CurrentUser, DBSession
from models.database_service import (
    get_classrooms_by_teacher, create_classroom, get_students_by_classroom,
    create_student, update_classroom, delete_classroom, get_classroom_by_id,
    get_student_by_id, update_student, delete_student
)

router = APIRouter(prefix="/api/classrooms", tags=["Classrooms"])


@router.get("")
async def get_classrooms(current_user: CurrentUser, db: DBSession):
    """Get all classrooms for the current teacher"""
    classrooms = get_classrooms_by_teacher(db, current_user.id)
    return [
        {
            "id": c.id,
            "name": c.name,
            "grade": c.grade,
            "subject": c.subject,
            "student_count": c.student_count,
            "created_at": c.created_at
        }
        for c in classrooms
    ]


@router.post("")
async def create_new_classroom(
    name: str = Form(...), 
    grade: str = Form(...), 
    subject: str = Form(...), 
    student_count: int = Form(...),
    current_user: CurrentUser = ..., 
    db: DBSession = ...
):
    """Create a new classroom"""
    classroom = create_classroom(db, name, grade, subject, student_count, current_user.id)  # type: ignore
    return {
        "id": classroom.id,
        "name": classroom.name,
        "grade": classroom.grade,
        "subject": classroom.subject,
        "student_count": classroom.student_count,
        "created_at": classroom.created_at
    }


@router.put("/{classroom_id}")
async def update_classroom_endpoint(
    classroom_id: int, 
    name: str = Form(None), 
    grade: str = Form(None), 
    subject: str = Form(None), 
    student_count: int = Form(None),
    current_user: CurrentUser = ..., 
    db: DBSession = ...
):
    """Update a classroom"""
    # Check if classroom belongs to current user
    classroom = get_classroom_by_id(db, classroom_id)
    if not classroom or classroom.teacher_id != current_user.id:  # type: ignore
        raise HTTPException(status_code=404, detail="Classroom not found")
    
    updated_classroom = update_classroom(db, classroom_id, name, grade, subject, student_count)
    if not updated_classroom:
        raise HTTPException(status_code=404, detail="Classroom not found")
    
    return {
        "id": updated_classroom.id,
        "name": updated_classroom.name,
        "grade": updated_classroom.grade,
        "subject": updated_classroom.subject,
        "student_count": updated_classroom.student_count,
        "created_at": updated_classroom.created_at
    }


@router.delete("/{classroom_id}")
async def delete_classroom_endpoint(
    classroom_id: int, 
    current_user: CurrentUser, 
    db: DBSession
):
    """Delete a classroom"""
    # Check if classroom belongs to current user
    classroom = get_classroom_by_id(db, classroom_id)
    if not classroom or classroom.teacher_id != current_user.id:
        raise HTTPException(status_code=404, detail="Classroom not found")
    
    success = delete_classroom(db, classroom_id)
    if not success:
        raise HTTPException(status_code=404, detail="Classroom not found")
    
    return {"message": "Classroom deleted successfully"}


@router.get("/{classroom_id}/students")
async def get_classroom_students(
    classroom_id: int, 
    current_user: CurrentUser, 
    db: DBSession
):
    """Get all students in a classroom"""
    students = get_students_by_classroom(db, classroom_id)
    return [
        {
            "id": s.id,
            "student_id": s.student_id,
            "full_name": s.full_name,
            "email": s.email,
            "created_at": s.created_at
        }
        for s in students
    ]


@router.post("/{classroom_id}/students")
async def add_student_to_classroom(
    classroom_id: int, 
    student_id: str = Form(...), 
    full_name: str = Form(...), 
    email: str = Form(...),
    current_user: CurrentUser = ..., 
    db: DBSession = ...
):
    """Add a student to a classroom"""
    student = create_student(db, student_id, full_name, email, classroom_id)
    return {
        "id": student.id,
        "student_id": student.student_id,
        "full_name": student.full_name,
        "email": student.email,
        "created_at": student.created_at
    }
