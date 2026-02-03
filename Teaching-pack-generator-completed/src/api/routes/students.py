"""
Student management routes
Handles student CRUD operations
"""
from fastapi import APIRouter, HTTPException, Form
from api.dependencies import CurrentUser, DBSession
from models.database_service import (
    get_student_by_id, update_student, delete_student
)

router = APIRouter(prefix="/api/students", tags=["Students"])


@router.put("/{student_id}")
async def update_student_endpoint(
    student_id: int, 
    student_code: str = Form(None), 
    full_name: str = Form(None), 
    email: str = Form(None), 
    current_user: CurrentUser = ..., 
    db: DBSession = ...
):
    """Update a student"""
    # Check if student belongs to current user's classroom
    student = get_student_by_id(db, student_id)
    if not student or not student.classroom or student.classroom.teacher_id != current_user.id:  # type: ignore
        raise HTTPException(status_code=404, detail="Student not found")
    
    updated_student = update_student(db, student_id, student_code, full_name, email)
    if not updated_student:
        raise HTTPException(status_code=404, detail="Student not found")
    
    return {
        "id": updated_student.id,
        "student_id": updated_student.student_id,
        "full_name": updated_student.full_name,
        "email": updated_student.email,
        "created_at": updated_student.created_at
    }


@router.delete("/{student_id}")
async def delete_student_endpoint(
    student_id: int, 
    current_user: CurrentUser, 
    db: DBSession
):
    """Delete a student"""
    # Check if student belongs to current user's classroom
    student = get_student_by_id(db, student_id)
    if not student or not student.classroom or student.classroom.teacher_id != current_user.id:
        raise HTTPException(status_code=404, detail="Student not found")
    
    success = delete_student(db, student_id)
    if not success:
        raise HTTPException(status_code=404, detail="Student not found")
    
    return {"message": "Student deleted successfully"}
