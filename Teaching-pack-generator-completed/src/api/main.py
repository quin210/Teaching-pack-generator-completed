"""
FastAPI application for Teaching Pack Generator
Multi-agent system for automatic teaching pack generation with differentiated instruction.
"""
import os
from dotenv import load_dotenv

# Load env vars immediately
load_dotenv()

import uuid
import asyncio
import requests
from typing import List, Dict, Optional
from datetime import timedelta
from fastapi import FastAPI, File, UploadFile, HTTPException, BackgroundTasks, Depends, Form
from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from pydantic_ai.models.google import GoogleModel
from pydantic_ai.providers.google import GoogleProvider
from loguru import logger
import uuid
from pathlib import Path
import json

# Import authentication
from api.auth import (
    authenticate_user, create_access_token, get_current_active_user,
    Token, LoginRequest, UserResponse, login_for_access_token, register_user,
    ACCESS_TOKEN_EXPIRE_MINUTES, UserRole
)

# Import database models
from models.database_models import User, Lesson, TeachingPack

# Import database
from models.database import get_db, create_tables
from models.database_service import (
    get_classrooms_by_teacher, create_classroom, get_students_by_classroom,
    create_student, create_lesson, get_lessons_by_classroom, create_teaching_pack,
    update_teaching_pack_status, update_classroom, delete_classroom, get_classroom_by_id,
    get_student_by_id, update_student, delete_student
)

# Import AgentClient
from llm.base import AgentClient

# Import prompts
from data.prompts.teaching_pack_prompts import (
    LESSON_PARSER_PROMPT, SKILL_MAPPER_PROMPT, DIAGNOSTIC_BUILDER_PROMPT,
    GROUP_LABELER_PROMPT, PACK_PLANNER_PROMPT, SLIDE_AUTHOR_PROMPT,
    QUIZ_PRACTICE_PROMPT, VIDEO_GENERATOR_PROMPT, SLIDE_DRAFTER_PROMPT, VIDEO_DRAFTER_PROMPT
)
from data.prompts.flashcard_prompts import FLASHCARD_GENERATOR_PROMPT, FLASHCARD_GROUP_GENERATOR_PROMPT
from data.prompts.study_prompts import THEORY_QUESTION_GENERATOR_PROMPT

# Import models
from models.teaching_pack_models import (
    LessonSummary, SkillSet, Diagnostic, GroupProfile,
    PackPlan, Slides, Video, Quiz
)
from models.flashcard_models import FlashcardSet
from models.study_models import TheoryQuestionSet

# Import helpers
from utils.workflow_helpers import (
    load_lesson_content, load_student_list, generate_mock_diagnostic_results,
    export_diagnostic_results, format_diagnostic_questions,
    parse_student_list_with_scores
)

# Import tools
from utils.basetools.grouping_utils import profile_groups_by_quartile
from utils.basetools.heterogeneous_grouping import heterogeneous_grouping_by_subject, ai_grouping_by_subject
from utils.basetools.slide_tools import generate_slides_from_text, search_themes
from utils.basetools.video_tools import generate_video_from_prompt
from utils.basetools.pdf_parser import extract_text_from_pdf
from utils.r2_storage import upload_fileobj_to_r2
from utils.r2_public import r2_public_url, safe_key


# ============= FASTAPI APP SETUP =============
app = FastAPI(
    title="Teaching Pack Generator API",
    description="Multi-agent system for automatic teaching pack generation with differentiated instruction",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Custom middleware to ensure CORS headers are always added, even on errors
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

class CORSErrorMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Handle preflight OPTIONS request
        if request.method == "OPTIONS":
            return Response(
                status_code=200,
                headers={
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Methods": "*",
                    "Access-Control-Allow-Headers": "*",
                    "Access-Control-Max-Age": "86400",
                }
            )
        
        try:
            response = await call_next(request)
            # Ensure CORS headers are present
            response.headers["Access-Control-Allow-Origin"] = "*"
            response.headers["Access-Control-Allow-Methods"] = "*"
            response.headers["Access-Control-Allow-Headers"] = "*"
            return response
        except Exception as e:
            logger.error(f"Middleware caught exception: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return JSONResponse(
                status_code=500,
                content={"detail": str(e)},
                headers={
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Methods": "*",
                    "Access-Control-Allow-Headers": "*",
                }
            )

# Add custom CORS error middleware FIRST (it will run last, wrapping everything)
app.add_middleware(CORSErrorMiddleware)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,  # Changed from True to fix CORS with wildcard origins
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# Global exception handler to ensure CORS headers are always sent
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Handle all unhandled exceptions and ensure CORS headers are included"""
    logger.error(f"Unhandled exception: {exc}")
    import traceback
    logger.error(f"Traceback: {traceback.format_exc()}")
    return JSONResponse(
        status_code=500,
        content={"detail": str(exc)},
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "*",
            "Access-Control-Allow-Headers": "*",
        }
    )

@app.on_event("startup")
async def startup_event():
    """Initialize database on startup"""
    # Run database migrations first
    try:
        logger.info("Running database migrations...")
        import subprocess
        result = subprocess.run(["alembic", "upgrade", "head"],
                              capture_output=True, text=True, cwd="/app")
        if result.returncode == 0:
            logger.info(" Database migrations completed")
        else:
            logger.warning(f"  Migration output: {result.stdout}")
            logger.error(f" Migration error: {result.stderr}")
    except Exception as e:
        logger.warning(f"  Migration failed: {e}")

    # Then create tables (in case migrations didn't create them)
    create_tables()
    logger.info(" Database tables created/verified")


# ============= MODEL CONFIGURATION =============
provider = GoogleProvider(api_key=os.getenv("GEMINI_API_KEY"))
model = GoogleModel('gemini-2.0-flash', provider=provider)

# AGENTS INITIALIZATION =============
lesson_parser_agent = AgentClient(model=model, system_prompt=LESSON_PARSER_PROMPT, tools=[extract_text_from_pdf]).create_agent(result_type=LessonSummary)
skill_mapper_agent = AgentClient(model=model, system_prompt=SKILL_MAPPER_PROMPT, tools=[]).create_agent(result_type=SkillSet)
diagnostic_builder_agent = AgentClient(model=model, system_prompt=DIAGNOSTIC_BUILDER_PROMPT, tools=[]).create_agent(result_type=Diagnostic)
group_labeler_agent = AgentClient(model=model, system_prompt=GROUP_LABELER_PROMPT, tools=[]).create_agent(result_type=GroupProfile)
pack_planner_agent = AgentClient(model=model, system_prompt=PACK_PLANNER_PROMPT, tools=[]).create_agent(result_type=PackPlan)
slide_drafter_agent = AgentClient(model=model, system_prompt=SLIDE_DRAFTER_PROMPT, tools=[]).create_agent(result_type=Slides)  # Removed search_themes to avoid rate limit
quiz_practice_agent = AgentClient(model=model, system_prompt=QUIZ_PRACTICE_PROMPT, tools=[]).create_agent(result_type=Quiz)
theory_question_agent = AgentClient(model=model, system_prompt=THEORY_QUESTION_GENERATOR_PROMPT, tools=[]).create_agent(result_type=TheoryQuestionSet)
flashcard_agent = AgentClient(model=model, system_prompt=FLASHCARD_GENERATOR_PROMPT, tools=[]).create_agent(result_type=FlashcardSet)
flashcard_group_agent = AgentClient(model=model, system_prompt=FLASHCARD_GROUP_GENERATOR_PROMPT, tools=[]).create_agent(result_type=FlashcardSet)
video_drafter_agent = AgentClient(model=model, system_prompt=VIDEO_DRAFTER_PROMPT, tools=[]).create_agent(result_type=Video)

# ============= STORAGE FOR ASYNC JOBS =============
jobs_storage = {}
OUTPUT_DIR = Path("outputs")
OUTPUT_DIR.mkdir(exist_ok=True)

# ============= TEACHING PACK MANAGEMENT ENDPOINTS =============


# ============= REQUEST/RESPONSE MODELS =============
class JobStatus(BaseModel):
    job_id: str
    status: str  # pending, processing, completed, failed
    message: Optional[str] = None
    result: Optional[Dict] = None
    error: Optional[str] = None


class GeneratePackRequest(BaseModel):
    num_groups: int = 4
    num_students: int = 30


class GenerateAssetsRequest(BaseModel):
    slides_content: Optional[Dict] = None
    video_content: Optional[Dict] = None
    generate_video: bool = False
    generate_slides: bool = True
    group_id: Optional[str] = None  # ID of the group being generated

class GenerateDraftRequest(BaseModel):
    type: str  # 'slides' or 'video'


class LessonParseResponse(BaseModel):
    lesson_summary: LessonSummary
    job_id: str


class SkillMapResponse(BaseModel):
    skill_set: SkillSet
    job_id: str


class DiagnosticResponse(BaseModel):
    diagnostic: Diagnostic
    job_id: str

@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "message": "Teaching Pack Generator API",
        "version": "1.0.0",
        "docs": "/docs",
        "endpoints": {
            "auth": {
                "login": "POST /api/auth/login",
                "register": "POST /api/auth/register"
            },
            "classrooms": {
                "list": "GET /api/classrooms",
                "create": "POST /api/classrooms",
                "update": "PUT /api/classrooms/{classroom_id}",
                "delete": "DELETE /api/classrooms/{classroom_id}",
                "students": "GET /api/classrooms/{classroom_id}/students",
                "add_student": "POST /api/classrooms/{classroom_id}/students",
                "lessons": "GET /api/classrooms/{classroom_id}/lessons",
                "teaching_packs": "GET /api/classrooms/{classroom_id}/teaching-packs"
            },
            "students": {
                "update": "PUT /api/students/{student_id}",
                "delete": "DELETE /api/students/{student_id}"
            },
            "lessons": "GET /api/lessons",
            "teaching_packs": "GET /api/teaching-packs",
            "lesson_parse": "POST /api/lesson/parse",
            "skills_map": "POST /api/skills/map",
            "diagnostic_build": "POST /api/diagnostic/build",
            "packs_generate": "POST /api/packs/generate",
            "job_status": "GET /api/jobs/{job_id}"
        }
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "gemini_api_configured": bool(os.getenv("GEMINI_API_KEY"))
    }


@app.get("/api/test-error")
async def test_error():
    """Test endpoint to verify error handling with CORS"""
    raise Exception("This is a test error to verify CORS headers on 500 responses")


@app.post("/api/test-auth-error")
async def test_auth_error(current_user = Depends(get_current_active_user)):
    """Test endpoint to verify auth errors with CORS"""
    raise Exception(f"Auth successful for {current_user.email}, this is a test error")


@app.get("/api/auth/me", response_model=UserResponse)
async def read_users_me(current_user = Depends(get_current_active_user)):
    """Get current user information"""
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        full_name=current_user.full_name,
        role=current_user.role.value,
        is_active=current_user.is_active
    )


@app.post("/api/lesson/parse")
async def parse_lesson(
    file: UploadFile = File(...),
    classroom_id: Optional[int] = None,
    current_user: User = Depends(get_current_active_user),
    db = Depends(get_db)
):
    """
    Parse a lesson file (PDF or TXT) to extract lesson summary

    - **file**: Lesson file (PDF or TXT format)
    - **classroom_id**: Optional classroom ID to associate the lesson with

    Returns: LessonSummary with title, subject, grade, key concepts, etc.
    """
    try:
        # Validate file type
        if not file.filename.endswith(('.pdf', '.txt')):# type: ignore
            raise HTTPException(status_code=400, detail="Only PDF and TXT files are supported")

        # Save uploaded file
        job_id = str(uuid.uuid4())
        upload_dir = OUTPUT_DIR / "uploads" / job_id
        upload_dir.mkdir(parents=True, exist_ok=True)
        file_path = upload_dir / file.filename# type: ignore

        await save_upload_file(file, file_path)
        logger.info(f"File saved: {file_path}")

        # Parse lesson
        logger.info("Parsing lesson content...")
        # Ensure path uses forward slashes
        result = await lesson_parser_agent.run(Path(file_path).as_posix())
        lesson_summary: LessonSummary = result.output# type: ignore
        logger.info(f"Lesson parsed: {lesson_summary.title}")

        # Save lesson to database if classroom_id is provided
        if classroom_id:
            lesson = create_lesson(
                db=db,
                title=lesson_summary.title,
                subject=lesson_summary.subject,
                grade=lesson_summary.grade,
                classroom_id=classroom_id,
                uploaded_by_id=current_user.id,  # type: ignore
                original_filename=file.filename,# type: ignore
                file_path=str(file_path),
                file_size=file_path.stat().st_size if file_path.exists() else None,  # type: ignore
                parsed_content=lesson_summary.dict()
            )
            logger.info(f"Lesson saved to database: {lesson.id}")

        return LessonParseResponse(
            lesson_summary=lesson_summary,
            job_id=job_id
        )

    except Exception as e:
        logger.error(f"Error parsing lesson: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/skills/map")
async def map_skills(
    lesson_summary: LessonSummary,
    current_user: User = Depends(get_current_active_user)
):
    """
    Map skills from a lesson summary
    
    - **lesson_summary**: Lesson summary from parse_lesson endpoint
    
    Returns: SkillSet with identified skills and dependencies
    
    Requires authentication.
    """
    try:
        logger.info("Mapping skills...")
        result = await skill_mapper_agent.run(lesson_summary.model_dump_json())
        skill_set: SkillSet = result.output# type: ignore
        logger.info(f"Mapped {len(skill_set.skills)} skills")
        
        job_id = str(uuid.uuid4())
        
        return SkillMapResponse(
            skill_set=skill_set,
            job_id=job_id
        )
        
    except Exception as e:
        logger.error(f"Error mapping skills: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/diagnostic/build")
async def build_diagnostic(
    skill_set: SkillSet,
    current_user: User = Depends(get_current_active_user)
):
    """
    Build a diagnostic assessment from a skill set
    
    - **skill_set**: Skill set from map_skills endpoint
    
    Returns: Diagnostic with questions to assess each skill
    
    Requires authentication.
    """
    try:
        logger.info("Building diagnostic...")
        result = await diagnostic_builder_agent.run(skill_set.model_dump_json())
        diagnostic: Diagnostic = result.output# type: ignore
        logger.info(f"Diagnostic built with {len(diagnostic.questions)} questions")
        
        job_id = str(uuid.uuid4())
        
        return DiagnosticResponse(
            diagnostic=diagnostic,
            job_id=job_id
        )
        
    except Exception as e:
        logger.error(f"Error building diagnostic: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# Import and include routers
from api.routes import auth, classrooms, students, lessons, grouping, files, jobs, teaching_packs

app.include_router(auth.router)
app.include_router(classrooms.router)
app.include_router(students.router)
app.include_router(lessons.router)
app.include_router(grouping.router)
app.include_router(files.router)
app.include_router(jobs.router)
app.include_router(teaching_packs.router)

# Set shared dependencies for route modules
files.set_output_dir(OUTPUT_DIR)


