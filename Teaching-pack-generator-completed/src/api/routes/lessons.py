"""
Lesson management routes
Handles lesson upload and retrieval
"""
from fastapi import APIRouter, HTTPException
from api.dependencies import CurrentUser, DBSession
from models.database_models import Lesson, UserRole
from models.database_service import get_lessons_by_classroom
from api.main import flashcard_agent, theory_question_agent
from utils.workflow_helpers import load_lesson_content
from sqlalchemy.orm.attributes import flag_modified
import logging
import os
import tempfile
import uuid
from pathlib import Path
from utils.r2_storage import download_r2_to_path

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/lessons", tags=["Lessons"])


def resolve_lesson_file_path(file_path: str) -> str:
    if not file_path:
        return file_path
    if os.path.isfile(file_path):
        return file_path
    lower_path = file_path.lower()
    if not lower_path.endswith((".pdf", ".txt")):
        return file_path
    tmp_dir = tempfile.gettempdir()
    tmp_path = os.path.join(tmp_dir, f"lesson_{uuid.uuid4().hex}_{Path(file_path).name}")
    try:
        download_r2_to_path(file_path, tmp_path)
        return tmp_path
    except Exception as e:
        logger.warning(f"Failed to download lesson file from R2: {file_path}. Error: {e}")
        return ""


@router.get("")
async def get_user_lessons(current_user: CurrentUser, db: DBSession):
    """Get all lessons uploaded by the current user"""
    lessons = db.query(Lesson).filter(Lesson.uploaded_by_id == current_user.id).all()  # type: ignore
    return [
        {
            "id": l.id,
            "title": l.title,
            "subject": l.subject,
            "grade": l.grade,
            "original_filename": l.original_filename,
            "file_size": l.file_size,
            "created_at": l.created_at,
            "classroom": {
                "id": l.classroom.id,
                "name": l.classroom.name
            } if l.classroom else None
        }
        for l in lessons
    ]


@router.get("/classrooms/{classroom_id}")
async def get_classroom_lessons(classroom_id: int, current_user: CurrentUser, db: DBSession):
    """Get all lessons in a classroom"""
    lessons = get_lessons_by_classroom(db, classroom_id)
    return [
        {
            "id": l.id,
            "title": l.title,
            "subject": l.subject,
            "grade": l.grade,
            "original_filename": l.original_filename,
            "file_size": l.file_size,
            "created_at": l.created_at,
            "uploaded_by": {
                "id": l.uploaded_by.id,
                "full_name": l.uploaded_by.full_name,
                "email": l.uploaded_by.email
            } if l.uploaded_by else None
        }
        for l in lessons
    ]


@router.post("/{lesson_id}/flashcards")
async def generate_flashcards(lesson_id: int, current_user: CurrentUser, db: DBSession):
    """Generate flashcards for a lesson"""
    lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()
    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")
    
    # Only teacher (owner) can generate... Or any teacher in that classroom...
    # Simple check: owner
    if lesson.uploaded_by_id != current_user.id:
         raise HTTPException(status_code=403, detail="Not authorized to generate flashcards for this lesson")

    # Load content
    try:
        resolved_path = resolve_lesson_file_path(lesson.file_path)
        content = load_lesson_content(resolved_path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load lesson content: {str(e)}")

    # Prepare input for agent including grouping info if available
    agent_input = f"Lesson Content:\n{content}\n\n"
    
    logger.info(f"generate_flashcards: lesson_id={lesson_id}, classroom_id={lesson.classroom_id}")

    if lesson.classroom and lesson.classroom.groups_configuration:
        import json
        try:
            groups_config = lesson.classroom.groups_configuration
            
            # Format dict to clear list of profiles for LLM
            if isinstance(groups_config, dict):
                profiles = []
                for gid, gdata in groups_config.items():
                    # infer level and assign standard group name
                    desc = str(gdata).lower()
                    if "foundation" in desc or "low" in desc:
                        level = "low"
                        g_name = "Beginner"
                    elif "advanced" in desc or "high" in desc:
                        level = "high"
                        g_name = "Advanced"
                    elif "medium" in desc:
                        level = "medium"
                        g_name = "Intermediate"
                    else:
                        level = "standard"
                        g_name = "General"

                    profiles.append({
                        "group_name": g_name,
                        "proficiency_level": level,
                        "description": gdata.get("characteristics", "") if isinstance(gdata, dict) else str(gdata)
                    })
                groups_str = json.dumps(profiles, indent=2, ensure_ascii=False)
            else:
                groups_str = json.dumps(groups_config, indent=2, ensure_ascii=False)

            agent_input += f"Grouping Information:\n{groups_str}\n"
            logger.info(f"Attached grouping info to flashcard prompt: {groups_str[:200]}...")
        except Exception as e:
            logger.warning(f"Failed to attach groups to flashcard prompt: {e}")
    else:
        logger.info("No grouping information available for this lesson.")

    # Add strict JSON requirement
    agent_input += """
Return STRICT JSON only (no markdown) with schema:
{
  "groups": [
    {
      "group_name": "Group name (General or specific group)",
      "proficiency_level": "optional level",
      "flashcards": [
         {"type": "...", "front": "...", "back": "...", "difficulty": "..."}
      ]
    }
  ]
}
If grouping info is provided, you MUST use the exact "group_name" values from the Grouping Information (e.g. "Beginner", "Intermediate", "Advanced").
Generate a "General" group AND the specific groups found in Grouping Information.
"""

    # Generate flashcards
    try:
        # Run agent
        result = await flashcard_agent.run(agent_input)
        
        # Handle different pydantic-ai versions
        if hasattr(result, 'data'):
            raw_data = result.data.model_dump()
        elif hasattr(result, 'output'):
            raw_data = result.output.model_dump()
        else:
             raw_data = result.model_dump()
        
        logger.info(f"AI flashcards raw_data keys: {list(raw_data.keys()) if isinstance(raw_data, dict) else type(raw_data)}")
        logger.info(f"AI raw_data preview: {str(raw_data)[:1200]}")

        # Normalize to ensure "groups" key exists
        if "groups" in raw_data:
            final_data = raw_data
        elif "flashcards" in raw_data:
            # Legacy/fallback: AI returned old format {flashcards: [...]}
            final_data = {
                "groups": [
                    {
                        "group_name": "General",
                        "flashcards": raw_data["flashcards"]
                    }
                ]
            }
        else:
             final_data = {"groups": []}

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
             
        lesson.flashcards = final_data
        
        flag_modified(lesson, "flashcards")
        db.commit()
        db.refresh(lesson)
    except Exception as e:
        logger.exception("AI Agent failed for flashcards")
        raise HTTPException(status_code=500, detail=f"Failed to generate flashcards: {str(e)}")
    
    return lesson.flashcards or {"groups": []}


@router.get("/{lesson_id}/flashcards")
async def get_flashcards(lesson_id: int, current_user: CurrentUser, db: DBSession):
    """Get flashcards for a lesson"""
    lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()
    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")
    
    # Authorization: Owner or Student in the classroom
    # If user is admin or teacher owner, ok.
    # If user is student, check if they belong to the classroom.
    
    if current_user.role == UserRole.ADMIN:
        pass
    elif current_user.id == lesson.uploaded_by_id:
        pass
    elif lesson.classroom_id:
        pass
    
    data = lesson.flashcards
    if not data:
        return {"groups": []}

    # Legacy migration: if stored as list
    if isinstance(data, list):
         return {
            "groups": [
                {"group_name": "General", "flashcards": data}
            ]
        }
    
    # Legacy migration: if stored as old FlashcardSet {flashcards: [], group_flashcards: ...}
    if isinstance(data, dict):
        if "groups" in data:
            return data
        
        # Construct groups from old format
        groups = []
        
        # 1. General flashcards
        if data.get("flashcards"):
            groups.append({
                "group_name": "General",
                "flashcards": data.get("flashcards")
            })
            
        # 2. Group flashcards
        if data.get("group_flashcards"):
            for g in data.get("group_flashcards", []):
                groups.append({
                    "group_name": g.get("group_name", "Unknown Group"),
                    "proficiency_level": g.get("proficiency_level"),
                    "flashcards": g.get("flashcards", [])
                })
        
        if not groups and not data.get("groups"):
             # Empty or unrecognizable object logic
             return {"groups": []}

        return {"groups": groups}
        
    return {"groups": []}


@router.post("/{lesson_id}/theory-questions")
async def generate_theory_questions(lesson_id: int, current_user: CurrentUser, db: DBSession):
    """Generate theory questions for a lesson"""
    logger.info(f"POST theory-questions lesson_id={lesson_id}")

    try:
        lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()
        if not lesson:
            raise HTTPException(status_code=404, detail="Lesson not found")
        
        if lesson.uploaded_by_id != current_user.id:
             raise HTTPException(status_code=403, detail="Not authorized")

        # Load content
        try:
            resolved_path = resolve_lesson_file_path(lesson.file_path)
            content = load_lesson_content(resolved_path)
        except Exception as e:
            logger.error(f"Failed to load lesson content: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to load lesson content: {str(e)}")

        # Prepare input for agent including grouping info if available
        agent_input = f"Lesson Content:\n{content}\n\n"
        
        logger.info(f"generate_theory_questions: lesson_id={lesson_id}, classroom_id={lesson.classroom_id}")

        if lesson.classroom and lesson.classroom.groups_configuration:
            import json
            try:
                groups_config = lesson.classroom.groups_configuration

                # Format dict to clear list of profiles for LLM
                if isinstance(groups_config, dict):
                    profiles = []
                    for gid, gdata in groups_config.items():
                        desc = str(gdata).lower()
                        # Infer level and name
                        if "foundation" in desc or "low" in desc:
                            level = "low"
                            g_name = "Beginner"
                        elif "advanced" in desc or "high" in desc:
                            level = "high"
                            g_name = "Advanced"
                        elif "medium" in desc:
                            level = "medium"
                            g_name = "Intermediate"
                        else:
                            level = "standard"
                            name_part = gid.split('_')[-1] if '_' in gid else gid
                            g_name = f"Group {name_part}"

                        profiles.append({
                            "group_name": g_name,
                            "proficiency_level": level,
                            "description": gdata.get("characteristics", "") if isinstance(gdata, dict) else str(gdata)
                        })
                    groups_str = json.dumps(profiles, indent=2, ensure_ascii=False)
                else:
                    groups_str = json.dumps(groups_config, indent=2, ensure_ascii=False)

                agent_input += f"Grouping Information:\n{groups_str}\n"
                logger.info(f"Attached grouping info to theory prompt: {groups_str[:200]}...")
            except Exception as e:
                logger.warning(f"Failed to attach groups to theory questions prompt: {e}")
        else:
            logger.info("No grouping information available for this lesson.")

        # Add strict requirements for groups
        agent_input += """
Return STRICT JSON only (no markdown) with schema:
{
  "groups": [
    {
      "group_name": "Group name (use the exact name from Grouping Information if provided e.g. Beginner, Intermediate)",
      "group_description": "Target learners / proficiency",
      "questions": [{"question": "...", "answer": "..."}]
    }
  ]
}

You MUST create groups corresponding to the Grouping Information provided.
Each group must have 6-12 questions.
"""

        # Generate questions
        try:
            result = await theory_question_agent.run(agent_input)
            
            # Handle diff versions
            if hasattr(result, 'data'):
                # pydantic-ai 0.0.x
                raw_data = result.data.model_dump()
            elif hasattr(result, 'output'):
                 # pydantic-ai 1.x
                raw_data = result.output.model_dump()
            else:
                 raw_data = result.model_dump()
            
            logger.info(f"AI raw_data keys: {list(raw_data.keys()) if isinstance(raw_data, dict) else type(raw_data)}")
            logger.info(f"AI raw_data preview: {str(raw_data)[:1000]}")

            # Normalize to ensure "groups" key exists
            # If AI returned just a list of groups (unlikely with our model but possible), wrap it
            if isinstance(raw_data, list):
                final_data = {"groups": raw_data}
            elif "groups" in raw_data:
                final_data = raw_data
            else:
                # Fallback: maybe AI returned old format {questions: []}
                # Wrap it into a General group
                questions = raw_data.get("questions", [])
                final_data = {
                    "groups": [
                        {
                            "group_name": "General", 
                            "group_description": "Standard Set", 
                            "questions": questions
                        }
                    ]
                }
            
            # Assign IDs robustly
            qid = 1
            for group in final_data.get("groups", []) or []:
                questions_list = group.get("questions", [])
                if not isinstance(questions_list, list): 
                    continue
                for q in questions_list:
                    if isinstance(q, dict) and not q.get("id"):
                        q["id"] = qid
                        qid += 1

            lesson.theory_questions = final_data
            
            flag_modified(lesson, "theory_questions")
            db.commit()
            db.refresh(lesson)
        except Exception as e:
            logger.exception("AI Agent failed")
            raise HTTPException(status_code=500, detail=f"Failed to generate questions: {str(e)}")
        
        return lesson.theory_questions or {"groups": []}

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Unexpected error in generate_theory_questions")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{lesson_id}/theory-questions")
async def get_theory_questions(lesson_id: int, current_user: CurrentUser, db: DBSession):
    """Get theory questions for a lesson"""
    lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()
    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")
    
    # Simple auth check
    if current_user.role != UserRole.ADMIN and current_user.id != lesson.uploaded_by_id and not lesson.classroom_id:
         raise HTTPException(status_code=403, detail="Not authorized")
    
    data = lesson.theory_questions
    if not data:
        return {"groups": []}
        
    # Legacy migration: if stored as list (old format)
    if isinstance(data, list):
         return {
            "groups": [
                {"group_name": "General", "questions": data}
            ]
        }
    
    # Legacy migration: if stored as {questions: [], group_questions: ...} (previous attempt)
    if isinstance(data, dict) and "questions" in data and "groups" not in data:
         # Convert old mixed format to strictly groups
         groups = []
         # 1. Add general questions as a group
         if data.get("questions"):
             groups.append({"group_name": "General", "questions": data.get("questions") or []})
         
         # 2. Add specific groups
         # Mapped from old schema: group_id -> group_name
         for g in (data.get("group_questions") or []):
             groups.append({
                 "group_name": g.get("group_name") or g.get("group_id") or "Group",
                 "proficiency_level": g.get("proficiency_level"),
                 "questions": g.get("questions") or []
             })
             
         return {"groups": groups}

    # Final validation to ensure strict schema match for Frontend
    if not isinstance(data, dict):
        return {"groups": []}
    if "groups" not in data:
        return {"groups": []}

    return data
