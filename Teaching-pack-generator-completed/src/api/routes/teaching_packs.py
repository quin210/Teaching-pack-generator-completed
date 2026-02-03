"""
Teaching Pack Routes
Handles all teaching pack related endpoints including generation, management, and asset creation.
"""
import asyncio
import os
import uuid
import json
import requests
import tempfile
from datetime import datetime
from typing import Dict, Optional
from pathlib import Path
from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Depends
from fastapi.responses import FileResponse
from pydantic import BaseModel
from loguru import logger
from sqlalchemy.orm.attributes import flag_modified

# Import dependencies
from api.dependencies import CurrentUser, DBSession
from api.auth import get_current_active_user
from models.database import get_db
from api.queue import get_queue
from utils.r2_storage import upload_bytes_to_r2, upload_fileobj_to_r2, download_r2_to_path
from utils.r2_public import r2_public_url, safe_key

# Import database models
from models.database_models import (
    User, Lesson, TeachingPack, WorkflowJob, Classroom, Student
)
from api.main import flashcard_agent, flashcard_group_agent

# Import database services
from models.database_service import (
    get_classroom_by_id, get_students_by_classroom, create_lesson,
    create_teaching_pack, update_teaching_pack_status
)

# Import teaching pack models
from models.teaching_pack_models import (
    LessonSummary, SkillSet, Diagnostic, GroupProfile,
    PackPlan, Slides, Video, Quiz
)

# Import workflow helpers
from utils.workflow_helpers import (
    load_lesson_content, load_student_list, generate_mock_diagnostic_results,
    export_diagnostic_results, format_diagnostic_questions,
    parse_student_list_with_scores, export_quiz_to_word, export_final_results
)

# Import tools
from utils.basetools.grouping_utils import profile_groups_by_quartile
from utils.basetools.heterogeneous_grouping import (
    heterogeneous_grouping_by_subject, ai_grouping_by_subject
)
from utils.basetools.slide_tools import generate_slides_from_text, search_themes
from utils.basetools.video_tools import generate_video_from_prompt
from utils.basetools.pdf_parser import extract_text_from_pdf
from utils.basetools.flashcard_tools import generate_flashcards_html

# Import AgentClient and prompts
from llm.base import AgentClient
from data.prompts.teaching_pack_prompts import (
    LESSON_PARSER_PROMPT, SKILL_MAPPER_PROMPT, DIAGNOSTIC_BUILDER_PROMPT,
    GROUP_LABELER_PROMPT, PACK_PLANNER_PROMPT, SLIDE_AUTHOR_PROMPT,
    QUIZ_PRACTICE_PROMPT, VIDEO_GENERATOR_PROMPT, SLIDE_DRAFTER_PROMPT, 
    VIDEO_DRAFTER_PROMPT
)

# Import model and provider
from pydantic_ai.models.google import GoogleModel
from pydantic_ai.providers.google import GoogleProvider

# Note: These will be imported from main module
# They need to be accessible for the routes to work
from api.main import (
    lesson_parser_agent, skill_mapper_agent, diagnostic_builder_agent,
    group_labeler_agent, pack_planner_agent, slide_drafter_agent,
    quiz_practice_agent, video_drafter_agent, theory_question_agent,
    OUTPUT_DIR
)

# Create router with prefix
router = APIRouter(prefix="/api", tags=["teaching-packs"])


# ============= REQUEST/RESPONSE MODELS =============

class JobStatus(BaseModel):
    job_id: str
    status: str  # queued, processing, completed, failed
    progress: float = 0.0
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


class SaveVideoUrlRequest(BaseModel):
    video_url: str
    group_id: str = "default"


class GenerateDraftRequest(BaseModel):
    type: str  # 'slides' or 'video'


class EvaluationItem(BaseModel):
    code: str
    label: str
    question: str
    rating: int
    section: Optional[str] = None
    reverse: bool = False


class EvaluationRequest(BaseModel):
    items: list[EvaluationItem]
    notes: Optional[str] = None


class LessonParseResponse(BaseModel):
    lesson_summary: LessonSummary
    job_id: str


class SkillMapResponse(BaseModel):
    skill_set: SkillSet
    job_id: str


class DiagnosticResponse(BaseModel):
    diagnostic: Diagnostic
    job_id: str


class CommitPackRequest(BaseModel):
    job_id: str
    group_id: str


class CommitAllPacksRequest(BaseModel):
    job_id: str


# ============= HELPER FUNCTIONS =============

async def save_upload_file(upload_file: UploadFile, destination: Path) -> Path:
    """Save uploaded file to destination"""
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("wb") as f:
        while True:
            chunk = await upload_file.read(1024 * 1024)
            if not chunk:
                break
            f.write(chunk)
    await upload_file.close()
    return destination


def upsert_workflow_job(db, job_id: str, **fields) -> WorkflowJob:
    job_record = db.query(WorkflowJob).filter(WorkflowJob.id == job_id).first()
    if not job_record:
        job_record = WorkflowJob(id=job_id, **fields)
        db.add(job_record)
    else:
        for key, value in fields.items():
            setattr(job_record, key, value)
    db.commit()
    return job_record


def run_process_full_workflow(
    lesson_file_path: str,
    num_groups: int,
    num_students: int,
    job_id: str,
    user_id: int,
    classroom_id: int,
    student_list_file_path: Optional[str] = None,
) -> None:
    try:
        asyncio.run(
            process_full_workflow(
                lesson_file_path,
                num_groups,
                num_students,
                job_id,
                user_id,
                classroom_id,
                student_list_file_path,
            )
        )
    except RuntimeError:
        loop = asyncio.new_event_loop()
        try:
            asyncio.set_event_loop(loop)
            loop.run_until_complete(
                process_full_workflow(
                    lesson_file_path,
                    num_groups,
                    num_students,
                    job_id,
                    user_id,
                    classroom_id,
                    student_list_file_path,
                )
            )
        finally:
            loop.close()


def run_process_asset_generation(
    job_id: str,
    teaching_pack_id: int,
    slides_content: Optional[Dict],
    video_content: Optional[Dict],
    generate_video: bool,
    generate_slides: bool = True,
    group_id: Optional[str] = None,
) -> None:
    try:
        asyncio.run(
            process_asset_generation(
                job_id,
                teaching_pack_id,
                slides_content,
                video_content,
                generate_video,
                generate_slides,
                group_id,
            )
        )
    except RuntimeError:
        loop = asyncio.new_event_loop()
        try:
            asyncio.set_event_loop(loop)
            loop.run_until_complete(
                process_asset_generation(
                    job_id,
                    teaching_pack_id,
                    slides_content,
                    video_content,
                    generate_video,
                    generate_slides,
                    group_id,
                )
            )
        finally:
            loop.close()


async def process_full_workflow(
    lesson_file_path: str,
    num_groups: int,
    num_students: int,
    job_id: str,
    user_id: int,
    classroom_id: int,
    student_list_file_path: Optional[str] = None
):
    """Process the full teaching pack generation workflow with error recovery"""
    from models.database import SessionLocal

    tmp_dir = tempfile.gettempdir()
    lesson_source_key = lesson_file_path
    lesson_tmp_path = os.path.join(tmp_dir, f"{job_id}_{Path(lesson_file_path).name}")
    download_r2_to_path(lesson_source_key, lesson_tmp_path)
    lesson_file_path = lesson_tmp_path

    if student_list_file_path:
        student_tmp_path = os.path.join(
            tmp_dir, f"{job_id}_{Path(student_list_file_path).name}"
        )
        download_r2_to_path(student_list_file_path, student_tmp_path)
        student_list_file_path = student_tmp_path

    # Ensure file paths use forward slashes to avoid escape character issues with LLM
    if lesson_file_path:
        lesson_file_path = Path(lesson_file_path).as_posix()
    if student_list_file_path:
        student_list_file_path = Path(student_list_file_path).as_posix()
    
    results = {
        "lesson_summary": None,
        "skill_set": None,
        "diagnostic": None,
        "groups": [],
        "teaching_packs": [],
        "errors": []
    }
    
    db = SessionLocal()
    try:
        upsert_workflow_job(
            db,
            job_id,
            status="processing",
            progress=0.01,
            message="Processing"
        )
        
        # Load student list from classroom, file, or generate mock students
        if classroom_id:
            # Check if classroom has students
            existing_students = get_students_by_classroom(db, classroom_id)
            if existing_students:
                logger.info(f"Using {len(existing_students)} existing students from classroom {classroom_id}")
                student_list = []
                for student in existing_students:
                    student_list.append({
                        "student_id": student.student_id,
                        "full_name": student.full_name,
                        "email": student.email,
                        "subject_scores": student.subject_scores or {},
                        "grade_level": student.grade_level,
                        "notes": student.notes,
                        "group_id": student.group_id
                    })
            elif student_list_file_path:
                logger.info(f"Loading student list from file: {student_list_file_path}")
                student_list = load_student_list(student_list_file_path, default_count=num_students)
                logger.info(f"Loaded {len(student_list)} students from uploaded file")
            else:
                student_list = load_student_list(None, default_count=num_students)
                logger.info(f"Generated {len(student_list)} mock students")
        else:
            # Fallback for cases without classroom_id
            if student_list_file_path:
                logger.info(f"Loading student list from file: {student_list_file_path}")
                student_list = load_student_list(student_list_file_path, default_count=num_students)
                logger.info(f"Loaded {len(student_list)} students from uploaded file")
            else:
                student_list = load_student_list(None, default_count=num_students)
                logger.info(f"Generated {len(student_list)} mock students")
        
        # Stage 1: Parse lesson
        try:
            logger.info("Parsing lesson content...")
            result = await lesson_parser_agent.run(lesson_file_path)
            lesson_summary: LessonSummary = result.output # type: ignore
            results["lesson_summary"] = lesson_summary
            logger.info(f"Lesson parsed: {lesson_summary.title}")
            
            # Create lesson record in database
            lesson_record = create_lesson(
                db=db,
                title=lesson_summary.title,
                subject=lesson_summary.subject or "General",
                grade=lesson_summary.grade or "General",
                classroom_id=classroom_id,  # Use the provided classroom_id
                uploaded_by_id=user_id,
                original_filename=Path(lesson_file_path).name,
                file_path=lesson_source_key,
                parsed_content=lesson_summary.model_dump()
            )
            lesson_id = lesson_record.id
            logger.info(f"Lesson saved to database with ID: {lesson_id}")

            # Generate Theory Questions
            try:
                logger.info("Generating theory questions...")
                content = load_lesson_content(lesson_file_path)
                tq_result = await theory_question_agent.run(content)
                lesson_record.theory_questions = tq_result.output.model_dump()
                flag_modified(lesson_record, "theory_questions")
                db.commit()
                db.refresh(lesson_record)
                logger.info("Theory questions generated and saved.")
            except Exception as e:
                logger.error(f"Failed to generate theory questions: {str(e)}")
                # We do not raise here, as this is an auxiliary feature
                results["errors"].append(f"Theory question generation failed: {str(e)}")
            
        except Exception as e:
            logger.error(f"Failed to parse lesson: {str(e)}")
            results["errors"].append(f"Lesson parsing failed: {str(e)}")
            raise  # Cannot continue without lesson summary
        
        # Stage 2: Map skills
        try:
            logger.info("Mapping skills...")
            result = await skill_mapper_agent.run(lesson_summary.model_dump_json())
            skill_set: SkillSet = result.output# type: ignore
            results["skill_set"] = skill_set
            logger.info(f"Mapped {len(skill_set.skills)} skills")
        except Exception as e:
            logger.error(f"Failed to map skills: {str(e)}")
            results["errors"].append(f"Skill mapping failed: {str(e)}")
            raise  # Cannot continue without skills
        
        # Stage 3: Build diagnostic
        try:
            logger.info("Building diagnostic...")
            result = await diagnostic_builder_agent.run(skill_set.model_dump_json())
            diagnostic: Diagnostic = result.output# type: ignore
            results["diagnostic"] = diagnostic
            logger.info(f"Diagnostic built with {len(diagnostic.questions)} questions")
        except Exception as e:
            logger.error(f"Failed to build diagnostic: {str(e)}")
            results["errors"].append(f"Diagnostic building failed: {str(e)}")
            raise  # Cannot continue without diagnostic
        
        # Stage 4: Generate diagnostic results or use existing groups
        try:
            # Check if classroom has existing groups
            classroom = get_classroom_by_id(db, classroom_id)
            if classroom and classroom.groups_configuration:  # type: ignore
                logger.info(f"Using existing groups from classroom {classroom_id}")
                # Convert existing groups to GroupProfile format
                labeled_groups = []
                for group_id, group_data in classroom.groups_configuration.items():
                    # Map existing group data to GroupProfile
                    mastery_mapping = {
                        "foundation": "low",
                        "medium": "medium", 
                        "high": "high",
                        "advanced": "advanced"
                    }
                    
                    group_profile = GroupProfile(
                        group_id=group_id,
                        group_name=f"Group {group_id.split('_')[1]}",
                        description=group_data.get("characteristics", ""),
                        mastery_level=mastery_mapping.get(group_data.get("level", "medium"), "medium"),  # type: ignore
                        skill_mastery={},  # Will be filled later if needed
                        common_misconceptions=[],  # Not available
                        learning_pace="moderate",  # Default
                        students=group_data.get("students", []),
                        recommended_activities=[group_data.get("recommended_exercises", "")]
                    )
                    labeled_groups.append(group_profile)
                logger.info(f"Using {len(labeled_groups)} existing groups")
                
                # Skip diagnostic results generation since we have groups
                diagnostic_results = []
            else:
                # Generate mock diagnostic results
                diagnostic_results = generate_mock_diagnostic_results(student_list, diagnostic, skill_set)
                logger.info(f"Mock results generated for {len(diagnostic_results)} students")
                
                # Stage 5: Profile groups
                grouping_result = profile_groups_by_quartile(skill_set, diagnostic_results, num_groups)
                
                # Stage 6: Label groups
                labeled_groups = []
                for group in grouping_result.groups:
                    logger.info(f"Labeling group {group.group_id}...")
                    context = {"group": group.model_dump(), "skill_set": skill_set.model_dump()}
                    result = await group_labeler_agent.run(str(context))
                    labeled_group: GroupProfile = result.output# type: ignore
                    labeled_groups.append(labeled_group)
                    logger.info(f"Group labeled: {labeled_group.group_name}")
        except Exception as e:
            logger.error(f"Failed to process groups: {str(e)}")
            results["errors"].append(f"Group processing failed: {str(e)}")
            raise
        
        results["groups"] = labeled_groups
        
        # Stage 7: Generate teaching packs (with error recovery for each pack)
        teaching_packs = []
        for group in labeled_groups:
            pack_data = {
                "group": group.model_dump(),
                "pack_plan": None,
                "slides": None,
                "video": None,
                "errors": []
            }
            
            try:
                # Plan pack
                logger.info(f"Planning pack for {group.group_name}...")
                context = {
                    "group": group.model_dump(),
                    "lesson_summary": lesson_summary.model_dump(),
                    "skill_set": skill_set.model_dump()
                }
                result = await pack_planner_agent.run(str(context))
                pack_plan: PackPlan = result.output# type: ignore
                pack_data["pack_plan"] = pack_plan.model_dump()
                logger.info(f"Pack planned with {len(pack_plan.slide_outline)} slides")
                
                # Generate quiz and practice questions
                try:
                    logger.info(f"Generating quiz for {group.group_name}...")
                    result = await quiz_practice_agent.run(pack_plan.model_dump_json())
                    quiz_data = result.output# type: ignore
                    pack_data["quiz"] = quiz_data.model_dump() if hasattr(quiz_data, 'model_dump') else quiz_data  # type: ignore
                    logger.info(f"Quiz generated with {len(quiz_data.questions) if hasattr(quiz_data, 'questions') else 'unknown'} questions")  # type: ignore
                except Exception as e:
                    logger.error(f"Failed to generate quiz for {group.group_name}: {str(e)}")
                    pack_data["errors"].append(f"Quiz generation failed: {str(e)}")
                    pack_data["quiz"] = {"questions": [], "practice_exercises": [], "answer_key": []}
                
                # Initialize slides structure
                try:
                    logger.info(f"Initializing slides structure for {group.group_name}...")
                    # Use lightweight initialization based on pack plan
                    pack_data["slides"] = {
                        "slides": [
                            {"slide_id": f"slide_{i+1}", "title": outline.get("title", f"Slide {i+1}"), 
                             "content": outline.get("content", "")}
                            for i, outline in enumerate(pack_plan.slide_outline)
                        ],
                        "generated_url": None
                    }
                    pack_data["slides_url"] = None
                    logger.info(f"Slides structure initialized with {len(pack_plan.slide_outline)} slides")
                except Exception as e:
                    logger.error(f"Failed to draft slides for {group.group_name}: {str(e)}")
                    pack_data["errors"].append(f"Slides drafting failed: {str(e)}")
                    # Fallback to mock slides
                    pack_title = getattr(pack_plan, 'title', None) or f"Teaching Pack for {group.group_name}"
                    pack_data["slides"] = {
                        "slides": [
                            {"slide_id": f"slide_{i+1}", "title": outline.get("title", f"Slide {i+1}"), 
                             "content": outline.get("content", "")}
                            for i, outline in enumerate(pack_plan.slide_outline)
                        ],
                        "generated_url": None
                    }
                    pack_data["slides_url"] = None

                # Draft video script and visuals
                try:
                    logger.info(f"Drafting video script for {group.group_name}...")
                    agent_result = await video_drafter_agent.run(pack_plan.model_dump_json())
                    video_data = agent_result.output.model_dump() if hasattr(agent_result.output, 'model_dump') else agent_result.output  # type: ignore

                    if isinstance(video_data, str):
                        cleaned = video_data.strip()
                        if "```json" in cleaned:
                            cleaned = cleaned.split("```json")[1].split("```")[0].strip()
                        elif "```" in cleaned:
                            cleaned = cleaned.split("```")[1].split("```")[0].strip()
                        try:
                            video_data = json.loads(cleaned)
                        except json.JSONDecodeError:
                            pass

                    if not isinstance(video_data, dict):
                        raise ValueError("Invalid video draft format")

                    video_data.setdefault("title", f"Video for {group.group_name}")
                    video_data.setdefault("script", "")
                    video_data.setdefault("visual_description", "")
                    video_data.setdefault("key_concepts", [])
                    video_data.setdefault("duration_seconds", 45)
                    video_data.setdefault("generated_url", None)
                    video_data.setdefault("thumbnail_url", None)
                    pack_data["video"] = video_data
                except Exception as e:
                    logger.error(f"Failed to draft video for {group.group_name}: {str(e)}")
                    pack_data["errors"].append(f"Video drafting failed: {str(e)}")
                    pack_data["video"] = {
                        "title": "Video unavailable",
                        "script": "Video script not available",
                        "visual_description": "Visual description not available",
                        "url": "",
                        "thumbnail": ""
                    }
                pack_data["video_url"] = None
                pack_data["video_thumbnail"] = None
                
                # Create teaching pack record in database
                # MODIFIED: Skip DB insertion for "Preview" stage.
                # Just add local placeholder ID (null) to indicate it's not committed.
                pack_data["teaching_pack_id"] = None
                pack_data["status"] = "preview"
                logger.info(f"Teaching Pack prepared for preview (No DB insert yet): {group.group_name}")
                
                teaching_packs.append(pack_data)
                
            except Exception as e:
                logger.error(f"Failed to generate pack for {group.group_name}: {str(e)}")
                pack_data["errors"].append(f"Pack generation failed: {str(e)}")
                results["errors"].append(f"Pack for {group.group_name} failed: {str(e)}")
                
                pack_data["teaching_pack_id"] = None
                pack_data["status"] = "failed"
                
                # Add partial pack data
                teaching_packs.append(pack_data)
        
        results["teaching_packs"] = teaching_packs

        try:
            output_file_name = export_final_results(
                lesson_summary,
                skill_set,
                diagnostic,
                labeled_groups,
                teaching_packs,
                len(student_list) if isinstance(student_list, list) else 0,
            )
            results["output_file"] = output_file_name
        except Exception as e:
            logger.error(f"Failed to export output file: {e}")
            results["errors"].append(f"Output file export failed: {str(e)}")
        
        # Create ONE teaching pack record containing all groups
        try:
            lesson_title = lesson_summary.title if lesson_summary else "Untitled Lesson"
            output_file_path = None
            if results.get("output_file"):
                output_file_path = str(Path("outputs") / results["output_file"])
            teaching_pack = create_teaching_pack(
                db=db,
                title=f"Teaching Packs - {lesson_title}",
                classroom_id=classroom_id,
                lesson_id=lesson_id,
                created_by_id=user_id,
                group_configuration={
                    "num_groups": len(teaching_packs),
                    "groups": [pack.get("group", {}) for pack in teaching_packs]
                },
                output_file_path=output_file_path
            )

            for pack in teaching_packs:
                pack["teaching_pack_id"] = teaching_pack.id
            
            # Store all data in the teaching_pack_data JSON field
            teaching_pack.teaching_pack_data = {
                "lesson_summary": lesson_summary.model_dump() if lesson_summary else None,
                "skill_set": skill_set.model_dump() if skill_set else None,
                "diagnostic": diagnostic.model_dump() if diagnostic else None,
                "groups": [g.model_dump() for g in labeled_groups] if labeled_groups else [],
                "teaching_packs": teaching_packs,
                "output_file": results.get("output_file"),
                "teaching_pack_id": teaching_pack.id,
                "lesson_id": lesson_id
            }  # type: ignore
            flag_modified(teaching_pack, "teaching_pack_data")
            teaching_pack.status = "processing"  # type: ignore
            db.commit()
            db.refresh(teaching_pack)
            
            logger.info(f" Created single Teaching Pack record (ID: {teaching_pack.id}) containing {len(teaching_packs)} groups")
            results["saved_to_db"] = True
            results["teaching_pack_id"] = teaching_pack.id
            
        except Exception as e:
            logger.error(f"Failed to save teaching pack to database: {str(e)}")
            results["errors"].append(f"Database save failed: {str(e)}")
            db.rollback()
        
        # Update job status
        if len(results["errors"]) == 0:
            job_message = f"Successfully generated {len(teaching_packs)} teaching packs"
        else:
            job_message = f"Generated {len(teaching_packs)} teaching packs with {len(results['errors'])} errors"
        
        final_result_dict = {
            "lesson_summary": results["lesson_summary"].model_dump() if results["lesson_summary"] else None,
            "skill_set": results["skill_set"].model_dump() if results["skill_set"] else None,
            "diagnostic": results["diagnostic"].model_dump() if results["diagnostic"] else None,
            "groups": [g.model_dump() for g in results["groups"]],
            "teaching_packs": results["teaching_packs"],
            "teaching_pack_id": results.get("teaching_pack_id"),
            "lesson_id": lesson_id,  # Include lesson_id for frontend reference
            "output_file": results.get("output_file"),
            "errors": results["errors"]
        }
        
        # Save to DB (WorkflowJob)
        try:
            upsert_workflow_job(
                db,
                job_id,
                status="completed",
                progress=1.0,
                message=job_message,
                result_json=final_result_dict
            )
            logger.info(f"Saved WorkflowJob {job_id} to database")
        except Exception as db_e:
            logger.error(f"Failed to save WorkflowJob to DB: {db_e}")
        
        logger.info(f"Job {job_id} completed with {len(results['errors'])} errors")
        
    except Exception as e:
        logger.error(f"Job {job_id} failed critically: {str(e)}")
        failed_result_dict = {
            "lesson_summary": results["lesson_summary"].model_dump() if results["lesson_summary"] else None,
            "skill_set": results["skill_set"].model_dump() if results["skill_set"] else None,
            "diagnostic": results["diagnostic"].model_dump() if results["diagnostic"] else None,
            "groups": [g.model_dump() for g in results["groups"]],
            "teaching_packs": results["teaching_packs"],
            "errors": results["errors"] + [str(e)]
        }
        
        # Save failure to DB
        try:
            upsert_workflow_job(
                db,
                job_id,
                status="failed",
                progress=1.0,
                message=str(e),
                result_json=failed_result_dict
            )
        except Exception as db_e:
            logger.error(f"Failed to save failed WorkflowJob to DB: {db_e}")

    finally:
        db.close()


async def process_asset_generation(
    job_id: str,
    teaching_pack_id: int,
    slides_content: Optional[Dict],
    video_content: Optional[Dict],
    generate_video: bool,
    generate_slides: bool = True,
    group_id: Optional[str] = None
):
    """
    Process asset generation (Slides and optional Video) for a teaching pack.
    """
    from models.database import SessionLocal
    from models.database_models import TeachingPack
    from models.database_service import get_db, update_teaching_pack_status
    
    db = SessionLocal()
    try:
        upsert_workflow_job(
            db,
            job_id,
            status="processing",
            progress=0.01,
            message="Processing assets"
        )
        
        # Get Teaching Pack
        teaching_pack = db.query(TeachingPack).filter(TeachingPack.id == teaching_pack_id).first()
        if not teaching_pack:
            raise ValueError(f"Teaching pack {teaching_pack_id} not found")
        
        # Get Teaching Pack data from database
        if teaching_pack.teaching_pack_data is None:
            raise ValueError(f"Teaching pack data not found for teaching pack {teaching_pack_id}")
        
        target_pack = teaching_pack.teaching_pack_data

        # 1. Generate Slides
        if generate_slides and slides_content:
            try:
                logger.info("Generating slides...")
                # Convert slides content to text for the tool
                # Assuming slides_content is the Slides object dict
                slides_text = ""
                for slide in slides_content.get("slides", []):
                    slides_text += f"# {slide.get('title', '')}\n{slide.get('content', '')}\n\n"
                
                # Extract theme_id from teacher notes or use default (TODO: Pass theme_id in request)
                # Default theme
                theme_id = "default" 
                
                # Use generate_slides_from_text directly
                # Note: This tool might expect specific format.
                slide_result = generate_slides_from_text(slides_text, theme_id=theme_id)
                
                # Check for downloadUrl in the response data
                download_url = slide_result.get('data', {}).get('downloadUrl') or slide_result.get('downloadUrl')
                if download_url:
                    # Download the file and save it locally
                    try:
                        response = requests.get(download_url)
                        response.raise_for_status()
                        
                        # Generate unique filename
                        slides_filename = f"generated_slides_{uuid.uuid4().hex[:8]}.pptx"
                        slides_path = OUTPUT_DIR / slides_filename
                        
                        # Save the file
                        with open(slides_path, 'wb') as f:
                            f.write(response.content)
                        
                        # Convert PPTX to images for preview
                        try:
                            from pptx import Presentation
                            from PIL import Image
                            import io
                            
                            # Load the presentation
                            presentation = Presentation(str(slides_path))
                            
                            # Create images directory
                            images_dir = OUTPUT_DIR / f"{slides_filename}_images"
                            images_dir.mkdir(exist_ok=True)
                            
                            # Convert each slide to image
                            slide_images = []
                            for i, slide in enumerate(presentation.slides):
                                # For now, just create a simple placeholder - full conversion would need more complex setup
                                # We'll implement a simpler approach
                                pass
                            
                            # For now, just serve the PPTX directly with better headers
                            
                        except Exception as img_error:
                            logger.warning(f"Could not convert slides to images: {img_error}")
                        
                        gid = group_id or "default"
                        r2_key = safe_key(
                            f"assets/{teaching_pack_id}/{gid}/slides_{uuid.uuid4().hex[:8]}.pptx"
                        )
                        with open(slides_path, "rb") as f:
                            upload_fileobj_to_r2(
                                f,
                                r2_key,
                                content_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
                            )
                        slides_url = r2_public_url(r2_key)
                        if group_id:
                            # Set slides_url in the specific group pack
                            if "teaching_packs" in target_pack:
                                for pack in target_pack["teaching_packs"]:  # type: ignore
                                    pack_group = pack.get("group", {})
                                    if isinstance(pack_group, dict):
                                        pack_group_id = pack_group.get("group_id") or pack_group.get("focus")
                                    else:
                                        pack_group_id = pack.get("group_id") or pack.get("focus")
                                    if (str(pack_group_id) == str(group_id) or
                                        str(pack_group_id).replace('_', ' ').title() == str(group_id).replace('_', ' ').title()):
                                        pack["slides_url"] = slides_url  # type: ignore
                                        if "slides" in pack:
                                            pack["slides"]["generated_url"] = slides_url  # type: ignore
                                        break
                        else:
                            target_pack["slides_url"] = slides_url  # type: ignore

                        # Update the slides object too
                        if "slides" in target_pack:
                            target_pack["slides"]["generated_url"] = slides_url  # type: ignore

                        current_slides_urls = dict(teaching_pack.slides_urls) if teaching_pack.slides_urls else {}
                        current_slides_urls[gid] = slides_url
                        teaching_pack.slides_urls = current_slides_urls
                        flag_modified(teaching_pack, "slides_urls")

                        logger.info(f"Slides uploaded to R2: {slides_url}")
                    except Exception as download_error:
                        logger.error(f"Failed to download slides: {download_error}")
                        # Fallback to remote URL
                        target_pack["slides_url"] = download_url  # type: ignore
                        if "slides" in target_pack:
                            target_pack["slides"]["generated_url"] = download_url  # type: ignore
                        current_slides_urls = dict(teaching_pack.slides_urls) if teaching_pack.slides_urls else {}
                        current_slides_urls[group_id or "default"] = download_url
                        teaching_pack.slides_urls = current_slides_urls
                        flag_modified(teaching_pack, "slides_urls")
                        logger.info(f"Slides generated (remote): {download_url}")
                else:
                    logger.error(f"Slide generation returned no URL: {slide_result}")
            except Exception as e:
                logger.error(f"Failed to generate slides: {e}")
                target_pack["errors"] = target_pack.get("errors", []) + [f"Slide generation failed: {str(e)}"]  # type: ignore

        # 2. Generate Video (if requested)
        if generate_video and video_content:
            try:
                logger.info("Generating video...")
                script = video_content.get("script", "")
                visuals = video_content.get("visual_description", "")
                prompt = f"Create a video with this script: {script}\n\nVisuals: {visuals}"
                
                video_result = generate_video_from_prompt(prompt, duration_seconds=8)
                
                if video_result.get("success"):
                    gid = group_id or "default"
                    video_url = video_result.get("video_url")
                    video_thumbnail = video_result.get("thumbnail_url")
                    if not video_url:
                        video_path = video_result.get("video_path")
                        if not video_path:
                            raise RuntimeError(
                                f"Video generator did not return video_path. Got: {video_result}"
                            )
                        video_path_obj = Path(video_path)
                        if not video_path_obj.exists():
                            raise RuntimeError(f"Video file not found at path: {video_path_obj}")

                        r2_key = safe_key(
                            f"assets/{teaching_pack_id}/{gid}/{video_path_obj.name}"
                        )
                        with open(video_path_obj, "rb") as f:
                            upload_fileobj_to_r2(f, r2_key, content_type="video/mp4")
                        video_url = r2_public_url(r2_key)

                    if group_id:
                        # Set video_url in the specific group pack
                        if "teaching_packs" in target_pack:
                            for pack in target_pack["teaching_packs"]:  # type: ignore
                                pack_group = pack.get("group", {})
                                if isinstance(pack_group, dict):
                                    pack_group_id = pack_group.get("group_id") or pack_group.get("focus")
                                else:
                                    pack_group_id = pack.get("group_id") or pack.get("focus")
                                logger.info(f"Checking pack with group_id: {pack_group_id}")
                                # Try both original and normalized matching
                                if (str(pack_group_id) == str(group_id) or
                                    str(pack_group_id).replace('_', ' ').title() == str(group_id).replace('_', ' ').title()):
                                    logger.info(f"Found matching pack, setting video_url: {video_url}")
                                    pack["video_url"] = video_url  # type: ignore
                                    pack["video_thumbnail"] = video_thumbnail  # type: ignore
                                    if "video" in pack:
                                        pack["video"]["generated_url"] = video_url  # type: ignore
                                        pack["video"]["thumbnail_url"] = video_thumbnail  # type: ignore
                                    break
                    else:
                        # Set video_url at root level for backward compatibility
                        target_pack["video_url"] = video_url  # type: ignore
                        target_pack["video_thumbnail"] = video_thumbnail  # type: ignore
                    if "video" in target_pack:
                        target_pack["video"]["generated_url"] = video_url  # type: ignore
                        target_pack["video"]["thumbnail_url"] = video_thumbnail  # type: ignore

                    current_video_urls = dict(teaching_pack.video_urls) if teaching_pack.video_urls else {}
                    current_video_urls[gid] = video_url
                    teaching_pack.video_urls = current_video_urls
                    flag_modified(teaching_pack, "video_urls")

                    logger.info(f"Video uploaded to R2: {video_url}")
                else:
                    logger.error(f"Video generation failed: {video_result.get('error')}")
            except Exception as e:
                logger.error(f"Failed to generate video: {e}")
                target_pack["errors"] = target_pack.get("errors", []) + [f"Video generation failed: {str(e)}"]  # type: ignore

        # Save updated data to database
        teaching_pack.teaching_pack_data = target_pack  # type: ignore
        # Force SQLAlchemy to detect the change in JSON field
        flag_modified(teaching_pack, "teaching_pack_data")
        db.commit()
        db.refresh(teaching_pack)
        logger.info(f"Teaching pack {teaching_pack_id} updated with slides_url: {target_pack.get('slides_url')}")
        logger.info(f"Teaching pack {teaching_pack_id} updated with video_url: {target_pack.get('video_url')}")
        logger.info(f"Teaching pack data keys: {list(target_pack.keys())}")
        if "teaching_packs" in target_pack:
            logger.info(f"Number of teaching packs: {len(target_pack['teaching_packs'])}")
            for i, pack in enumerate(target_pack["teaching_packs"]):
                logger.info(f"Pack {i} video_url: {pack.get('video_url')}")
                logger.info(f"Pack {i} group: {pack.get('group', {}).get('group_id') if isinstance(pack.get('group'), dict) else pack.get('group_id')}")
            
        # Update DB status
        update_teaching_pack_status(db, teaching_pack_id, "completed")
        
        try:
            upsert_workflow_job(
                db,
                job_id,
                status="completed",
                progress=1.0,
                message="Assets generated",
                result_json=target_pack
            )
        except Exception as db_e:
            logger.error(f"Failed to save asset WorkflowJob to DB: {db_e}")
        
    except Exception as e:
        logger.error(f"Asset generation failed: {e}")
        try:
            upsert_workflow_job(
                db,
                job_id,
                status="failed",
                progress=1.0,
                message=str(e)
            )
        except Exception as db_e:
            logger.error(f"Failed to save failed asset WorkflowJob to DB: {db_e}")
    finally:
        db.close()


# ============= ROUTE ENDPOINTS =============

@router.get("/teaching-packs")
async def get_user_teaching_packs(
    current_user: CurrentUser,
    db: DBSession
):
    """Get all teaching packs created by the current user"""
    teaching_packs = db.query(TeachingPack).filter(TeachingPack.created_by_id == current_user.id).all()
    return [
        {
            "id": tp.id,
            "title": tp.title,
            "status": tp.status,
            "created_at": tp.created_at,
            "completed_at": tp.completed_at,
            "lesson_summary": tp.teaching_pack_data.get("lesson_summary") if tp.teaching_pack_data else None,
            "skill_set": tp.teaching_pack_data.get("skill_set") if tp.teaching_pack_data else None,
            "diagnostic": tp.teaching_pack_data.get("diagnostic") if tp.teaching_pack_data else None,
            "groups": tp.teaching_pack_data.get("groups") if tp.teaching_pack_data else None,
            "teaching_pack_data": tp.teaching_pack_data,
            "video_urls": tp.video_urls,
            "slides_urls": tp.slides_urls,
            "flashcard_urls": tp.flashcard_urls,
            "video_urls": tp.video_urls,
            "slides_urls": tp.slides_urls,
            "flashcard_urls": tp.flashcard_urls,
            "classroom": {
                "id": tp.classroom.id,  # type: ignore
                "name": tp.classroom.name
            } if tp.classroom else None,
            "lesson": {
                "id": tp.lesson.id,  # type: ignore
                "title": tp.lesson.title
            } if tp.lesson else None
        }
        for tp in teaching_packs
    ]


@router.get("/classrooms/{classroom_id}/teaching-packs")
async def get_classroom_teaching_packs(
    classroom_id: int,
    current_user: CurrentUser,
    db: DBSession
):
    """Get all teaching packs for a specific classroom"""
    # Check if classroom belongs to current user
    classroom = get_classroom_by_id(db, classroom_id)
    if not classroom or classroom.teacher_id != current_user.id:  # type: ignore
        raise HTTPException(status_code=404, detail="Classroom not found")
    
    teaching_packs = db.query(TeachingPack).filter(TeachingPack.classroom_id == classroom_id).all()
    return [
        {
            "id": tp.id,  # type: ignore
            "title": tp.title,
            "status": tp.status,
            "created_at": tp.created_at,
            "completed_at": tp.completed_at,
            "lesson_summary": tp.teaching_pack_data.get("lesson_summary") if tp.teaching_pack_data else None,  # type: ignore
            "skill_set": tp.teaching_pack_data.get("skill_set") if tp.teaching_pack_data else None,  # type: ignore
            "diagnostic": tp.teaching_pack_data.get("diagnostic") if tp.teaching_pack_data else None,  # type: ignore
            "groups": tp.teaching_pack_data.get("groups") if tp.teaching_pack_data else None,  # type: ignore
            "teaching_pack_data": tp.teaching_pack_data,
            "video_urls": tp.video_urls,
            "slides_urls": tp.slides_urls,
            "lesson": {
                "id": tp.lesson.id,  # type: ignore
                "title": tp.lesson.title
            } if tp.lesson else None
        }
        for tp in teaching_packs
    ]


@router.post("/teaching-packs/commit-all")
async def commit_all_teaching_packs(
    request: CommitAllPacksRequest,
    current_user: CurrentUser,
    db: DBSession
):
    """
    Commit all teaching packs from a job as a single Teaching Pack record.
    This creates ONE teaching pack record containing all groups.
    """
    try:
        # Load data from DB (WorkflowJob)
        job_record = db.query(WorkflowJob).filter(WorkflowJob.id == request.job_id).first()
        
        if not job_record:
            raise HTTPException(status_code=404, detail="Job data not found or expired. Please regenerate.")
        full_data = job_record.result_json

        if not full_data:
            raise HTTPException(status_code=404, detail="Job data is empty")
        
        # Check if already committed
        if full_data.get("teaching_pack_id"):
            return {"teaching_pack_id": full_data.get("teaching_pack_id"), "status": "already_committed"}
        
        # Extract data for DB
        # Look up most recent lesson by user
        last_lesson = db.query(Lesson).filter(Lesson.uploaded_by_id == current_user.id).order_by(Lesson.created_at.desc()).first()
        if not last_lesson:
            raise HTTPException(status_code=400, detail="No lesson found for user")
        lesson_id = last_lesson.id
        
        # Get lesson summary for title
        lesson_summary = full_data.get("lesson_summary", {})
        title = f"Teaching Packs - {lesson_summary.get('title', 'Untitled Lesson')}"
        output_file_name = full_data.get("output_file")
        output_file_path = str(Path("outputs") / output_file_name) if output_file_name else ""
        
        # Create ONE teaching pack record for all groups
        teaching_pack = create_teaching_pack(
            db=db,
            title=title,
            classroom_id=None,
            lesson_id=lesson_id,
            created_by_id=current_user.id,
            group_configuration={
                "num_groups": len(full_data.get("teaching_packs", [])),
                "groups": [pack.get("group", {}) for pack in full_data.get("teaching_packs", [])]
            },
            output_file_path=output_file_path
        )

        full_data["teaching_pack_id"] = teaching_pack.id
        for pack in full_data.get("teaching_packs", []):
            pack["teaching_pack_id"] = teaching_pack.id
        
        # Store all data in teaching_pack_data field
        teaching_pack.lesson_summary = full_data.get("lesson_summary")  # type: ignore
        teaching_pack.skill_set = full_data.get("skill_set")  # type: ignore
        teaching_pack.diagnostic = full_data.get("diagnostic")  # type: ignore
        teaching_pack.groups = full_data.get("groups")  # type: ignore
        teaching_pack.teaching_pack_data = full_data  # type: ignore
        teaching_pack.status = "processing"  # type: ignore
        flag_modified(teaching_pack, "teaching_pack_data")
        db.commit()
        
        # Update job record with teaching_pack_id
        if job_record:
            job_record.result_json = full_data
            flag_modified(job_record, "result_json")
            db.commit()
        
        logger.info(f"Committed all teaching packs as single record (ID: {teaching_pack.id})")
        return {"teaching_pack_id": teaching_pack.id, "status": "committed"}
    
    except Exception as e:
        logger.error(f"Commit all failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/teaching-packs/commit")
async def commit_teaching_pack(
    request: CommitPackRequest,
    current_user: CurrentUser,
    db: DBSession
):
    """
    [DEPRECATED] Commit a single teaching pack group from Preview stage.
    Use /teaching-packs/commit-all instead to save all groups in one record.
    """
    try:
        # FIX: Load data from DB (WorkflowJob) instead of parsing file
        job_record = db.query(WorkflowJob).filter(WorkflowJob.id == request.job_id).first()
        
        if not job_record:
             raise HTTPException(status_code=404, detail="Job data not found or expired. Please regenerate.")
        full_data = job_record.result_json

        if not full_data:
             raise HTTPException(status_code=404, detail="Job data is empty")
             
        # Find the group
        target_pack = None
        target_index = -1
        
        # Parse index from group_id if it follows "group-{N}" pattern
        target_index_from_id = -1
        if isinstance(request.group_id, str) and request.group_id.startswith("group-"):  # type: ignore
            try:
                target_index_from_id = int(request.group_id.split("-")[1])
            except ValueError:
                pass
        
        for idx, pack in enumerate(full_data.get("teaching_packs", [])):
            # Check by group_id inside group object OR by index
            if (pack.get("group", {}).get("group_id") == request.group_id) or (idx == target_index_from_id):
                target_pack = pack
                target_index = idx
                break
        
        if not target_pack:
            raise HTTPException(status_code=404, detail=f"Group {request.group_id} not found in results")
            
        # Check if already committed
        if target_pack.get("teaching_pack_id"):
             return {"teaching_pack_id": target_pack.get("teaching_pack_id"), "status": "already_committed"}

        # Extract data for DB
        # Look up most recent lesson by user
        last_lesson = db.query(Lesson).filter(Lesson.uploaded_by_id == current_user.id).order_by(Lesson.created_at.desc()).first()
        if not last_lesson:
             raise HTTPException(status_code=400, detail="No lesson found for user")
        lesson_id = last_lesson.id

        # Insert DB Record
        group_profile = target_pack.get("group", {})
        pack_plan = target_pack.get("pack_plan", {})
        
        # Re-construct output_path for compatibility
        output_file_name = full_data.get("output_file")
        output_path = Path("outputs") / output_file_name if output_file_name else None
        output_path_str = str(output_path) if output_path else ""
        
        teaching_pack = create_teaching_pack(
            db=db,
            title=f"Teaching Pack for {group_profile.get('group_name', 'Group')}",
            classroom_id=None, # Or pass from frontend if needed
            lesson_id=lesson_id,  # type: ignore
            created_by_id=current_user.id,  # type: ignore
            group_configuration={
                "group_name": group_profile.get("group_name"),
                "group_profile": group_profile,
                "pack_plan": pack_plan
            },
            output_file_path=output_path_str
        )
        
        # Update JSON in DB (WorkflowJob) - CRITICAL for future steps using this job data
        if job_record:
            full_data["teaching_packs"][target_index]["teaching_pack_id"] = teaching_pack.id  # type: ignore
            full_data["teaching_packs"][target_index]["status"] = "processing"  # type: ignore
            
            job_record.result_json = full_data
            flag_modified(job_record, "result_json")
            db.commit()
            
        # Update JSON file with new ID (Legacy support - Try but ignore errors)
        if output_path and output_path.exists():
            try:
                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump(full_data, f, indent=2, ensure_ascii=False)
            except Exception as e:
                logger.warning(f"Could not update legacy output file: {e}")
            
        return {"teaching_pack_id": teaching_pack.id, "status": "committed"}

    except Exception as e:
        logger.error(f"Commit failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/teaching-packs/{teaching_pack_id}/draft-content")
async def draft_pack_content(
    teaching_pack_id: int,
    request: GenerateDraftRequest,
    current_user: CurrentUser,
    db: DBSession
):
    """
    Draft content for slides or video using AI usage agents on demand.
    """
    # Verify ownership
    pack = db.query(TeachingPack).filter(TeachingPack.id == teaching_pack_id).first()
    if not pack or pack.created_by_id != current_user.id:  # type: ignore
        raise HTTPException(status_code=404, detail="Teaching pack not found")

    # Load pack data from DB first, fallback to legacy output file if needed
    output_file_path = pack.output_file_path
    full_data = pack.teaching_pack_data
    if not full_data:
        if not output_file_path or not os.path.exists(output_file_path):  # type: ignore
            raise HTTPException(status_code=404, detail="Teaching pack data not found")
        with open(output_file_path, 'r', encoding='utf-8') as f:  # type: ignore
            full_data = json.load(f)

    try:
        # Find specific pack data
        target_pack = None
        for p in full_data.get("teaching_packs", []):
            if p.get("teaching_pack_id") == teaching_pack_id:
                target_pack = p
                break
        
        if not target_pack:
            raise HTTPException(status_code=404, detail="Pack data not found in file")
            
        # Extract context
        group_profile = target_pack.get("group", {})
        pack_plan = target_pack.get("pack_plan", {})
        
        # Run Agent
        result_data = None
        if request.type == 'slides':
            logger.info(f"Drafting slides on demand for pack {teaching_pack_id}...")
            agent_result = await slide_drafter_agent.run(json.dumps(pack_plan))
            result_data = agent_result.output.model_dump() # type: ignore
            # Update local data
            target_pack["slides"] = result_data
            
        elif request.type == 'video':
            logger.info(f"Drafting video on demand for pack {teaching_pack_id}...")
            agent_result = await video_drafter_agent.run(json.dumps(pack_plan))
            result_data = agent_result.output.model_dump() if hasattr(agent_result.output, 'model_dump') else agent_result.output # type: ignore

            if isinstance(result_data, str):
                cleaned = result_data.strip()
                if "```json" in cleaned:
                    cleaned = cleaned.split("```json")[1].split("```")[0].strip()
                elif "```" in cleaned:
                    cleaned = cleaned.split("```")[1].split("```")[0].strip()
                try:
                    result_data = json.loads(cleaned)
                except json.JSONDecodeError:
                    pass

            if not isinstance(result_data, dict):
                # Fallback
                result_data = {
                    "title": "Draft Video",
                    "script": "Content unavailable",
                    "visual_description": ""
                }
            target_pack["video"] = result_data

        else:
            raise HTTPException(status_code=400, detail="Invalid draft type")

        # Save back to DB
        pack.teaching_pack_data = full_data  # type: ignore
        flag_modified(pack, "teaching_pack_data")
        db.commit()
        db.refresh(pack)

        # Save back to file (legacy support)
        if output_file_path and os.path.exists(output_file_path):  # type: ignore
            try:
                with open(output_file_path, 'w', encoding='utf-8') as f:  # type: ignore
                    json.dump(full_data, f, indent=2, ensure_ascii=False)
            except Exception as e:
                logger.warning(f"Could not update legacy output file: {e}")
            
        return result_data

    except Exception as e:
        logger.error(f"Drafting failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/teaching-packs/{teaching_pack_id}/generate-assets")
async def generate_pack_assets_endpoint(
    teaching_pack_id: int,
    request: GenerateAssetsRequest,
    current_user: CurrentUser,
    db: DBSession
):
    """
    Generate actual assets (Slides, Video) for a teaching pack from refined content.
    """
    # Verify ownership
    pack = db.query(TeachingPack).filter(TeachingPack.id == teaching_pack_id).first()
    if not pack or pack.created_by_id != current_user.id:  # type: ignore
        raise HTTPException(status_code=404, detail="Teaching pack not found")
        
    # Use UUID only (36 chars) - database column is varchar(36)
    job_id = str(uuid.uuid4())
    upsert_workflow_job(
        db,
        job_id,
        status="queued",
        progress=0.0,
        message="Asset generation queued",
        created_by_id=current_user.id  # type: ignore
    )
    
    q = get_queue()
    q.enqueue(
        run_process_asset_generation,
        job_id,
        teaching_pack_id,
        request.slides_content,
        request.video_content,
        request.generate_video,
        request.generate_slides,
        request.group_id,
        job_timeout=60 * 60
    )
    
    return {
        "job_id": job_id,
        "status": "queued",
        "message": "Asset generation started"
    }


@router.post("/lesson/parse")
async def parse_lesson(
    current_user: CurrentUser,
    db: DBSession,
    file: UploadFile = File(...),
    classroom_id: Optional[int] = None
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


@router.post("/skills/map")
async def map_skills(
    lesson_summary: LessonSummary,
    current_user: CurrentUser
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


@router.post("/diagnostic/build")
async def build_diagnostic(
    skill_set: SkillSet,
    current_user: CurrentUser
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


@router.post("/packs/generate")
async def generate_teaching_packs(
    current_user: CurrentUser,
    db: DBSession,
    file: UploadFile = File(...),
    classroom_id: int = Form(...),
    num_groups: int = 4,
    num_students: int = 30,
    student_list_file: Optional[UploadFile] = File(None)
):
    """
    Generate complete teaching packs from a lesson file (Full workflow)
    
    - **file**: Lesson file (PDF or TXT format)
    - **classroom_id**: ID of the classroom to associate the teaching packs with
    - **num_groups**: Number of student groups (default: 4)
    - **num_students**: Number of mock students if no student list file provided (default: 30)
    - **student_list_file**: Optional student list file (Excel, CSV, TXT, JSON)
    
    Returns: Job ID to track processing status
    
    This endpoint runs the complete workflow:
    1. Parse lesson
    2. Map skills
    3. Build diagnostic
    4. Generate diagnostic results (using real student list if provided)
    5. Group students by performance
    6. Label groups
    7. Generate differentiated teaching packs (slides, videos)
    
    Requires authentication.
    """
    try:
        # Validate file type
        if not file.filename.endswith(('.pdf', '.txt')):# type: ignore
            raise HTTPException(status_code=400, detail="Only PDF and TXT files are supported")

        # Upload lesson file to R2
        job_id = str(uuid.uuid4())
        r2_key = f"uploads/{job_id}/{file.filename}"  # type: ignore
        file.file.seek(0)
        upload_fileobj_to_r2(
            file.file, r2_key, content_type=file.content_type or "application/pdf"
        )
        await file.close()
        logger.info(f"Lesson file uploaded to R2: {r2_key}")

        # Upload student list file if provided
        student_list_key = None
        if student_list_file and student_list_file.filename:
            student_list_key = f"uploads/{job_id}/{student_list_file.filename}"  # type: ignore
            student_list_file.file.seek(0)
            upload_fileobj_to_r2(
                student_list_file.file,
                student_list_key,
                content_type=student_list_file.content_type
                or "application/octet-stream",
            )
            await student_list_file.close()
            logger.info(f"Student list file uploaded to R2: {student_list_key}")
        
        # Validate classroom ownership
        classroom = get_classroom_by_id(db, classroom_id)
        if not classroom or classroom.teacher_id != current_user.id:  # type: ignore
            raise HTTPException(status_code=404, detail="Classroom not found")
        
        upsert_workflow_job(
            db,
            job_id,
            status="queued",
            progress=0.0,
            message="Queued for processing",
            created_by_id=current_user.id  # type: ignore
        )
        
        # Enqueue job for worker
        q = get_queue()
        rq_job = q.enqueue(
            run_process_full_workflow,
            r2_key,
            num_groups,
            num_students,
            job_id,
            current_user.id,  # type: ignore
            classroom_id,
            student_list_key,
            job_timeout=60 * 60,
            job_id=job_id
        )
        logger.info(
            f"Enqueued job to RQ: rq_id={rq_job.id}, queue={q.name}, redis={os.getenv('REDIS_URL')}"
        )
        
        return {
            "job_id": job_id,
            "status": "queued",
            "message": "Teaching pack generation started. Use /api/jobs/{job_id} to check status."
        }
        
    except Exception as e:
        logger.error(f"Error starting job: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/teaching-packs/{teaching_pack_id}/video-url")
async def save_video_url(
    teaching_pack_id: int,
    request: SaveVideoUrlRequest,
    current_user: CurrentUser,
    db: DBSession
):
    """
    Save video URL for a specific group in a teaching pack.
    """
    try:
        # Find the teaching pack
        teaching_pack = db.query(TeachingPack).filter(TeachingPack.id == teaching_pack_id).first()
        if not teaching_pack:
            raise HTTPException(status_code=404, detail="Teaching pack not found")

        # Check if user owns the teaching pack
        if teaching_pack.created_by_id != current_user.id:
            raise HTTPException(status_code=403, detail="Not authorized to modify this teaching pack")

        # Initialize video_urls if None
        if teaching_pack.video_urls is None:
            teaching_pack.video_urls = {}

        # Update the video URL for the group
        teaching_pack.video_urls[request.group_id] = request.video_url

        # Mark as modified for SQLAlchemy
        flag_modified(teaching_pack, "video_urls")

        # Commit to database
        db.commit()

        logger.info(f"Saved video URL for teaching pack {teaching_pack_id}, group {request.group_id}: {request.video_url}")

        return {"message": "Video URL saved successfully", "group_id": request.group_id, "video_url": request.video_url}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to save video URL: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/slides/{filename}")
async def get_slides_file(filename: str):
    """
    Serve slides files
    
    - **filename**: Name of the slides file
    """
    slides_path = OUTPUT_DIR / filename
    
    if not slides_path.exists():
        raise HTTPException(status_code=404, detail=f"Slides file {filename} not found")
    
    # Create response with headers optimized for embedding
    response = FileResponse(
        path=str(slides_path),
        filename=filename,
        media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation"
    )
    
    # Add headers to allow embedding and cross-origin access
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, HEAD, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "*"
    
    return response


@router.get("/teaching-packs/download-quiz/{pack_id}")
async def download_quiz_word(
    pack_id: int,
    current_user: CurrentUser,
    db: DBSession,
    group_id: str = None
):
    """
    Download quiz as Word document
    """
    logger.info(f"Download quiz request for pack_id: {pack_id}, group_id: {group_id}, user_id: {current_user.id}")
    
    # Get teaching pack
    pack = db.query(TeachingPack).filter(
        TeachingPack.id == pack_id,
        TeachingPack.created_by_id == current_user.id
    ).first()
    
    if not pack:
        logger.warning(f"Teaching pack not found: pack_id={pack_id}, user_id={current_user.id}")
        raise HTTPException(status_code=404, detail="Teaching pack not found")
    
    logger.info(f"Found pack: {pack.id}, pack_data keys: {list(pack.teaching_pack_data.keys()) if pack.teaching_pack_data else 'None'}")
    
    # Get quiz data for the specific group
    pack_data = pack.teaching_pack_data
    if not pack_data or 'teaching_packs' not in pack_data:
        logger.warning(f"Teaching packs not found in pack_data: {pack_data}")
        raise HTTPException(status_code=404, detail="Teaching packs not found in teaching pack")
    
    teaching_packs = pack_data['teaching_packs']
    quiz_data = None
    group_name = "Quiz"
    
    if group_id:
        # Find the specific group's pack
        for group_pack in teaching_packs:
            if group_pack.get('group', {}).get('group_id') == group_id:
                quiz_data = group_pack.get('quiz')
                group_name = group_pack.get('group', {}).get('group_name', f'Group {group_id}')
                break
    else:
        # If no group_id specified, use the first group's quiz
        if teaching_packs and len(teaching_packs) > 0:
            quiz_data = teaching_packs[0].get('quiz')
            group_name = teaching_packs[0].get('group', {}).get('group_name', 'Quiz')
    
    if not quiz_data:
        logger.warning(f"Quiz not found for group_id: {group_id}")
        raise HTTPException(status_code=404, detail="Quiz not found for the specified group")
    
    lesson_title = pack_data.get('lesson_summary', {}).get('title', 'Quiz')
    
    logger.info(f"Exporting quiz with {len(quiz_data.get('questions', []))} questions")
    
    try:
        # Export quiz to Word
        word_file_path = export_quiz_to_word(quiz_data, f"{lesson_title} - {group_name}")
        
        logger.info(f"Quiz exported to: {word_file_path}")
        
        # Return file response
        filename = f"{lesson_title.replace(' ', '_')}_{group_name.replace(' ', '_')}_quiz.docx"
        response = FileResponse(
            path=word_file_path,
            filename=filename,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
        
        # Add CORS headers
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Methods"] = "GET, HEAD, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "*"
        
        return response
        
    except ImportError:
        logger.error("python-docx not available")
        raise HTTPException(
            status_code=500, 
            detail="Word export functionality not available. Please install python-docx."
        )
    except Exception as e:
        logger.error(f"Failed to export quiz to Word: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to export quiz: {str(e)}")

def map_mastery_to_level(mastery: str | None) -> str:
    m = (mastery or "").lower()
    if "low" in m or "foundation" in m:
        return "beginner"
    if "medium" in m:
        return "intermediate"
    if "high" in m or "advanced" in m:
        return "advanced"
    return "general"

@router.post("/teaching-packs/{teaching_pack_id}/groups/{group_id}/flashcards")
async def generate_group_flashcards(teaching_pack_id: int, group_id: str, current_user=Depends(get_current_active_user), db=Depends(get_db)):
    tp = db.query(TeachingPack).filter(TeachingPack.id == teaching_pack_id).first()
    if not tp or tp.created_by_id != current_user.id:
        raise HTTPException(status_code=404, detail="Teaching pack not found")

    data = tp.teaching_pack_data or {}
    packs = data.get("teaching_packs", []) or []

    target = None
    for p in packs:
        if (p.get("group") or {}).get("group_id") == group_id:
            target = p
            break
    if not target:
        raise HTTPException(status_code=404, detail="Group not found in teaching pack")

    group_profile = target.get("group") or {}
    mastery_level = group_profile.get("mastery_level")
    level_name = map_mastery_to_level(mastery_level)

    lesson_summary = data.get("lesson_summary") or {}
    pack_plan = target.get("pack_plan") or {}

    agent_input = f"""
TARGET LEVEL: {level_name}
MASTERY: {mastery_level}

LESSON CONTENT:
{json.dumps(lesson_summary, ensure_ascii=False, indent=2)}

GROUP DETAILS:
{json.dumps(group_profile, ensure_ascii=False, indent=2)}

PACK PLAN:
{json.dumps(pack_plan, ensure_ascii=False, indent=2)}
"""

    result = await flashcard_group_agent.run(agent_input)

    if hasattr(result, "data"):
        raw = result.data.model_dump()
    elif hasattr(result, "output"):
        raw = result.output.model_dump()
    else:
        raw = result.model_dump()

    # normalize
    groups = []
    if isinstance(raw, dict) and isinstance(raw.get("groups"), list):
        groups = raw.get("groups") or []

    # --- ENFORCE: only keep 1 group by level_name ---
    target_level = (level_name or "general").strip()
    target_level_lc = target_level.lower()

    def norm(s: str | None) -> str:
        return (s or "").strip().lower()

    # filter by group_name / proficiency_level
    picked = [g for g in groups if norm(g.get("group_name")) == target_level_lc]
    if not picked:
        picked = [g for g in groups if target_level_lc in norm(g.get("group_name"))]
    if not picked:
        picked = [g for g in groups if target_level_lc in norm(g.get("proficiency_level"))]

    # fallback: take first if model wrong
    if not picked and groups:
        picked = [groups[0]]

    # if still none -> empty
    only_group = picked[0] if picked else {"group_name": target_level, "flashcards": []}

    # force correct level name + mastery
    only_group["group_name"] = target_level
    only_group["proficiency_level"] = mastery_level

    final_data = {"groups": [only_group]}
    
    # Assign IDs robustly
    fid = 1
    for group in final_data.get("groups", []) or []:
        fc_list = group.get("flashcards", [])
        if not isinstance(fc_list, list): 
            continue
        for fc in fc_list:
            if isinstance(fc, dict) and not fc.get("id"):
                fc["id"] = fid
                fid += 1

    # store into teaching_pack_data at target pack level
    target["flashcards"] = final_data
    data["teaching_packs"] = packs

    # Generate Flashcards HTML and save URL
    try:
        flashcards_list = only_group.get("flashcards", [])
        html_title = f"{tp.title} - Group {group_id} Flashcards ({target_level})"
        html_content = generate_flashcards_html(html_title, flashcards_list)

        gid = group_id
        r2_key = safe_key(
            f"assets/{teaching_pack_id}/{gid}/flashcards_{uuid.uuid4().hex[:8]}.html"
        )
        upload_bytes_to_r2(
            html_content.encode("utf-8"),
            r2_key,
            content_type="text/html; charset=utf-8",
        )
        flashcard_url = r2_public_url(r2_key)

        current_urls = dict(tp.flashcard_urls) if tp.flashcard_urls else {}
        current_urls[gid] = flashcard_url
        tp.flashcard_urls = current_urls
        flag_modified(tp, "flashcard_urls")

        final_data["flashcard_url"] = flashcard_url
        logger.info(f"Flashcards uploaded to R2 for group {gid}: {flashcard_url}")
    except Exception as e:
        logger.error(f"Failed to upload flashcards HTML to R2: {e}")

    tp.teaching_pack_data = data
    flag_modified(tp, "teaching_pack_data")
    db.commit()
    db.refresh(tp)

    return final_data


@router.get("/teaching-packs/{teaching_pack_id}/groups/{group_id}/flashcards")
async def get_group_flashcards(teaching_pack_id: int, group_id: str, current_user=Depends(get_current_active_user), db=Depends(get_db)):
    tp = db.query(TeachingPack).filter(TeachingPack.id == teaching_pack_id).first()
    if not tp or tp.created_by_id != current_user.id:
        raise HTTPException(status_code=404, detail="Teaching pack not found")

    data = tp.teaching_pack_data or {}
    for p in (data.get("teaching_packs") or []):
        if (p.get("group") or {}).get("group_id") == group_id:
            return p.get("flashcards") or {"groups": []}

    raise HTTPException(status_code=404, detail="Group not found in teaching pack")


@router.post("/teaching-packs/{teaching_pack_id}/groups/{group_id}/evaluation")
async def submit_group_evaluation(
    teaching_pack_id: int,
    group_id: str,
    request: EvaluationRequest,
    current_user: CurrentUser,
    db: DBSession
):
    """
    Save teacher evaluation to R2 under evaluation/ for a specific group.
    """
    tp = db.query(TeachingPack).filter(TeachingPack.id == teaching_pack_id).first()
    if not tp:
        raise HTTPException(status_code=404, detail="Teaching pack not found")
    if tp.created_by_id != current_user.id:  # type: ignore
        raise HTTPException(status_code=403, detail="Not authorized to evaluate this teaching pack")

    if not request.items:
        raise HTTPException(status_code=400, detail="Evaluation items are required")

    ratings: list[int] = []
    for item in request.items:
        if item.rating < 1 or item.rating > 5:
            raise HTTPException(status_code=400, detail=f"Invalid rating for {item.code}: {item.rating}")
        ratings.append(item.rating)

    avg_rating = round(sum(ratings) / len(ratings), 2) if ratings else None
    submitted_at = datetime.utcnow().isoformat() + "Z"

    group_meta = None
    data = tp.teaching_pack_data or {}
    if isinstance(data, dict):
        for pack in data.get("teaching_packs", []) or []:
            pack_group = pack.get("group", {}) if isinstance(pack, dict) else {}
            candidates = [
                pack.get("group_id") if isinstance(pack, dict) else None,
                pack.get("focus") if isinstance(pack, dict) else None,
                pack_group.get("group_id") if isinstance(pack_group, dict) else None,
                pack_group.get("group_name") if isinstance(pack_group, dict) else None,
                pack_group.get("focus") if isinstance(pack_group, dict) else None,
            ]
            for candidate in [c for c in candidates if c]:
                if str(candidate).strip().lower() == str(group_id).strip().lower():
                    group_meta = pack_group
                    break
            if group_meta:
                break

    payload = {
        "teaching_pack_id": teaching_pack_id,
        "group_id": group_id,
        "teacher_id": current_user.id,  # type: ignore
        "teacher_email": current_user.email,  # type: ignore
        "submitted_at": submitted_at,
        "average_rating": avg_rating,
        "items": [item.model_dump() for item in request.items],
        "notes": request.notes,
        "group": group_meta
    }

    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    r2_key = safe_key(
        f"evaluation/{teaching_pack_id}/{group_id}/evaluation_{timestamp}_{uuid.uuid4().hex[:6]}.json"
    )
    upload_bytes_to_r2(
        json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8"),
        r2_key,
        content_type="application/json"
    )
    evaluation_url = r2_public_url(r2_key)

    return {
        "message": "Evaluation saved",
        "evaluation_url": evaluation_url,
        "average_rating": avg_rating,
        "count": len(ratings)
    }
