"""
Student grouping routes
Handles student list uploads, parsing, and intelligent group creation
"""
import uuid
from pathlib import Path
from fastapi import APIRouter, HTTPException, File, UploadFile, Form
from loguru import logger

from api.dependencies import CurrentUser, DBSession
from models.database_service import (
    get_classroom_by_id, get_students_by_classroom
)
from utils.workflow_helpers import parse_student_list_with_scores
from utils.basetools.heterogeneous_grouping import ai_grouping_by_subject

# Output directory configuration
OUTPUT_DIR = Path("outputs")
OUTPUT_DIR.mkdir(exist_ok=True)

router = APIRouter(prefix="/api/classrooms/{classroom_id}", tags=["Grouping"])


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


@router.post("/upload-students-and-group")
async def upload_students_and_create_groups(
    classroom_id: int,
    student_list_file: UploadFile = File(...),
    num_groups: int = Form(4),
    current_user: CurrentUser = ...,
    db: DBSession = ...
):
    """
    API 1: Upload student list with scores and create heterogeneous groups
    
    - **student_list_file**: Excel/CSV file with columns: Name, Toan, Van, Anh, etc.
    - **num_groups**: Number of groups to create (default: 4)
    
    Returns: Group configuration and saves to classroom
    
    This creates smart groups where weak students in a subject are paired with
    strong students for peer learning.
    """
    try:
        # Validate classroom ownership
        classroom = get_classroom_by_id(db, classroom_id)
        if not classroom or classroom.teacher_id != current_user.id:  # type: ignore
            raise HTTPException(status_code=404, detail="Classroom not found")
        
        # Save uploaded file
        upload_id = str(uuid.uuid4())
        upload_dir = OUTPUT_DIR / "uploads" / upload_id
        upload_dir.mkdir(parents=True, exist_ok=True)
        file_path = upload_dir / student_list_file.filename  # type: ignore
        
        await save_upload_file(student_list_file, file_path)
        logger.info(f"Student list file saved: {file_path}")
        
        # Parse student list with scores
        students_data = parse_student_list_with_scores(str(file_path))
        
        if not students_data:
            raise HTTPException(status_code=400, detail="No students found in file")
        
        logger.info(f"Parsed {len(students_data)} students with scores")
        
        # Use AI agent for intelligent heterogeneous grouping based on classroom subject
        subject = classroom.subject  # type: ignore
        logger.info(f"Using AI Grouping Agent for subject '{subject}'")
        
        # AI agent returns complete groups_configuration with profiles
        groups_configuration = await ai_grouping_by_subject(students_data, subject, num_groups)  # type: ignore
        
        # Save or update students in database
        from models.database_models import Student
        
        # Clear existing students in classroom
        db.query(Student).filter(Student.classroom_id == classroom_id).delete()
        
        # Add new students with their group assignments
        # groups_configuration structure: {group_id: {group_id, students: [ids], profile: {...}}}
        student_id_to_data = {s['student_id']: s for s in students_data}
        
        for group_id, group_info in groups_configuration.items():
            student_ids = group_info['students']
            for student_id in student_ids:
                if student_id in student_id_to_data:
                    student_data = student_id_to_data[student_id]
                    new_student = Student(
                        student_id=student_data["student_id"],
                        full_name=student_data["full_name"],
                        email=student_data.get("email", f"{student_data['student_id']}_{classroom_id}@example.com"),
                        classroom_id=classroom_id,
                        subject_scores=student_data.get("subject_scores", {}),
                        grade_level=student_data.get("grade_level"),
                        notes=student_data.get("notes"),
                        group_id=group_id
                    )
                    db.add(new_student)
        
        # Save groups configuration to classroom
        classroom.groups_configuration = groups_configuration  # type: ignore
        classroom.student_count = len(students_data)  # type: ignore
        
        db.commit()
        db.refresh(classroom)
        
        logger.info(f"Successfully created {num_groups} groups for classroom {classroom_id}")
        
        return {
            "message": f"Successfully uploaded {len(students_data)} students and created {num_groups} groups",
            "num_students": len(students_data),
            "num_groups": num_groups,
            "groups": groups_configuration,
            "classroom": {
                "id": classroom.id,
                "name": classroom.name,
                "subject": classroom.subject,
                "grade": classroom.grade
            }
        }
        
    except ValueError as ve:
        logger.error(f"Validation error: {str(ve)}")
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logger.error(f"Error uploading students and creating groups: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/create-groups")
async def create_groups_from_existing_students(
    classroom_id: int,
    num_groups: int = 4,
    current_user: CurrentUser = ...,
    db: DBSession = ...
):
    """
    API: Create groups from existing students in classroom
    
    - **num_groups**: Number of groups to create (default: 4)
    
    Returns: Group configuration and updates classroom
    
    This creates smart groups where weak students in a subject are paired with
    strong students for peer learning, using existing student data.
    """
    try:
        # Validate classroom ownership
        classroom = get_classroom_by_id(db, classroom_id)
        if not classroom or classroom.teacher_id != current_user.id:  # type: ignore
            raise HTTPException(status_code=404, detail="Classroom not found")
        
        # Get existing students
        students = get_students_by_classroom(db, classroom_id)
        if not students:
            raise HTTPException(status_code=400, detail="No students found in classroom")
        
        # Convert to format expected by grouping function
        students_data = []
        for student in students:
            students_data.append({
                "student_id": student.student_id,
                "full_name": student.full_name,
                "email": student.email,
                "subject_scores": student.subject_scores or {},
                "grade_level": student.grade_level,
                "notes": student.notes
            })
        
        logger.info(f"Found {len(students_data)} existing students in classroom {classroom_id}")
        
        # Use AI agent for intelligent heterogeneous grouping based on classroom subject
        subject = classroom.subject  # type: ignore
        logger.info(f"Using AI Grouping Agent for subject '{subject}'")
        
        # AI agent returns complete groups_configuration with profiles
        groups_configuration = await ai_grouping_by_subject(students_data, subject, num_groups)  # type: ignore
        
        # Update students with their group assignments
        from models.database_models import Student
        
        for group_id, group_info in groups_configuration.items():
            student_ids = group_info['students']
            for student_id in student_ids:
                # Find student in database and update group_id
                student = db.query(Student).filter(
                    Student.student_id == student_id,
                    Student.classroom_id == classroom_id
                ).first()
                if student:
                    student.group_id = group_id
        
        # Save groups configuration to classroom
        classroom.groups_configuration = groups_configuration  # type: ignore
        
        db.commit()
        db.refresh(classroom)
        
        logger.info(f"Successfully created {num_groups} groups for classroom {classroom_id}")
        
        return {
            "message": f"Successfully created {num_groups} groups from {len(students_data)} existing students",
            "num_students": len(students_data),
            "num_groups": num_groups,
            "groups": groups_configuration,
            "classroom": {
                "id": classroom.id,
                "name": classroom.name,
                "subject": classroom.subject,
                "grade": classroom.grade
            }
        }
        
    except ValueError as ve:
        logger.error(f"Validation error: {str(ve)}")
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logger.error(f"Error creating groups from existing students: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/groups")
async def get_classroom_groups(
    classroom_id: int,
    pack_id: int = None,
    current_user: CurrentUser = ...,
    db: DBSession = ...
):
    """Get groups configuration for a classroom"""
    from models.database_models import TeachingPack
    
    classroom = get_classroom_by_id(db, classroom_id)
    if not classroom or classroom.teacher_id != current_user.id:  # type: ignore
        raise HTTPException(status_code=404, detail="Classroom not found")
    
    if not classroom.groups_configuration:  # type: ignore
        return {
            "message": "No groups configured yet",
            "groups": {}
        }
    
    # Get the groups configuration
    groups_config = classroom.groups_configuration  # type: ignore
    
    # Enhance groups with data from TeachingPack table
    teaching_packs = db.query(TeachingPack).filter(
        TeachingPack.classroom_id == classroom_id
    ).all()
    
    # First, collect video_urls and slides_urls from their respective fields (per-group storage)
    # Use urls from the specified pack_id if provided, otherwise latest
    video_urls_map = {}
    slides_urls_map = {}
    flashcard_urls_map = {}
    if teaching_packs:
        if pack_id:
            selected_tp = next((tp for tp in teaching_packs if tp.id == pack_id), None)
            if not selected_tp:
                raise HTTPException(status_code=404, detail=f"Teaching pack {pack_id} not found")
        else:
            selected_tp = max(teaching_packs, key=lambda tp: tp.id)
        
        if selected_tp.video_urls:
            for group_key, video_url in selected_tp.video_urls.items():
                if video_url:
                    # Normalize group keys
                    original_key = str(group_key).replace('pack-' + str(selected_tp.id) + '-', '')
                    normalized_key = original_key.replace('_', ' ').title()
                    video_urls_map[original_key] = video_url
                    video_urls_map[normalized_key] = video_url
                    logger.info(f"Found video URL for {original_key}: {video_url}")
        if selected_tp.slides_urls:
            for group_key, slides_url in selected_tp.slides_urls.items():
                if slides_url:
                    # Normalize group keys
                    original_key = str(group_key).replace('pack-' + str(selected_tp.id) + '-', '')
                    normalized_key = original_key.replace('_', ' ').title()
                    slides_urls_map[original_key] = slides_url
                    slides_urls_map[normalized_key] = slides_url
                    logger.info(f"Found slides URL for {original_key}: {slides_url}")
        if selected_tp.flashcard_urls:
            for group_key, fl_url in selected_tp.flashcard_urls.items():
                if fl_url:
                    original_key = str(group_key).replace('pack-' + str(selected_tp.id) + '-', '')
                    normalized_key = original_key.replace('_', ' ').title()
                    flashcard_urls_map[original_key] = fl_url
                    flashcard_urls_map[normalized_key] = fl_url
                    logger.info(f"Found flashcard URL for {original_key}: {fl_url}")
    
    # Create a map of pack data by group id/focus
    pack_data_map = {}
    for tp in teaching_packs:
        if tp.teaching_pack_data:
            teaching_pack_data = tp.teaching_pack_data
            logger.info(f"Processing teaching pack {tp.id}, data keys: {list(teaching_pack_data.keys())}")
            
            # If there are teaching_packs, find the pack for each group
            if "teaching_packs" in teaching_pack_data and isinstance(teaching_pack_data["teaching_packs"], list):
                logger.info(f"Found {len(teaching_pack_data['teaching_packs'])} teaching packs")
                for idx, pack in enumerate(teaching_pack_data["teaching_packs"]):
                    group_key = None
                    if "group" in pack and isinstance(pack["group"], dict):
                        group_key = pack["group"].get("group_id")
                    if not group_key:
                        group_key = pack.get("group_id") or pack.get("focus")
                    
                    logger.info(f"Pack {idx}: group_key={group_key}, video_url={pack.get('video_url')}")
                    
                    if group_key:
                        # Store with both original and normalized keys for flexible matching
                        original_key = str(group_key)
                        normalized_key = str(group_key).replace('_', ' ').title()  # 'group_1' -> 'Group 1'
                        
                        # Only overwrite if this pack has video_url and existing doesn't, or if no existing data
                        should_update = False
                        if original_key not in pack_data_map:
                            should_update = True
                        elif pack.get('video_url') and not pack_data_map[original_key].get('video_url'):
                            # Prioritize packs with video_url
                            should_update = True
                            logger.info(f"Overwriting {original_key} with pack that has video_url")
                        
                        if should_update:
                            pack_data_map[original_key] = pack
                            pack_data_map[normalized_key] = pack
                            logger.info(f"Mapped pack to keys: {original_key}, {normalized_key}")
            else:
                # Fallback to root level matching
                group_key = None
                if "group" in teaching_pack_data and isinstance(teaching_pack_data["group"], dict):
                    group_key = teaching_pack_data["group"].get("group_id")
                if not group_key:
                    group_key = teaching_pack_data.get("group_id") or teaching_pack_data.get("focus")
                if group_key:
                    original_key = str(group_key)
                    normalized_key = str(group_key).replace('_', ' ').title()
                    
                    # Only overwrite if this pack has video_url and existing doesn't, or if no existing data
                    should_update = False
                    if original_key not in pack_data_map:
                        should_update = True
                    elif teaching_pack_data.get('video_url') and not pack_data_map[original_key].get('video_url'):
                        should_update = True
                        logger.info(f"Overwriting {original_key} with root pack that has video_url")
                    
                    if should_update:
                        pack_data_map[original_key] = teaching_pack_data
                        pack_data_map[normalized_key] = teaching_pack_data
    
    # Merge pack data into groups configuration
    logger.info(f"Pack data map keys: {list(pack_data_map.keys())}")
    logger.info(f"Groups config keys: {list(groups_config.keys()) if isinstance(groups_config, dict) else 'Not a dict'}")
    
    if isinstance(groups_config, dict):
        for group_key, group_data in groups_config.items():
            # Add group_id and group_name to each group
            group_data["group_id"] = group_key
            group_data["group_name"] = str(group_key).replace('_', ' ').title()  # 'group_1' -> 'Group 1'
            
            logger.info(f"Processing group: {group_key}")
            
            # Try to find pack data with both original and normalized keys
            pack_data = None
            if group_key in pack_data_map:
                pack_data = pack_data_map[group_key]
                logger.info(f"Found pack data for {group_key} using original key")
            else:
                normalized_group_key = str(group_key).replace('_', ' ').title()
                if normalized_group_key in pack_data_map:
                    pack_data = pack_data_map[normalized_group_key]
                    logger.info(f"Found pack data for {group_key} using normalized key {normalized_group_key}")
            
            if pack_data:
                group_data.update({
                    "video_url": None,  # Only set from video_urls_map override
                    "slides_url": pack_data.get("slides_url"),
                    "video_thumbnail": pack_data.get("video_thumbnail"),
                    "pack_plan": pack_data.get("pack_plan"),
                    "slides": pack_data.get("slides"),
                    "video": pack_data.get("video"),
                    "quiz": pack_data.get("quiz"),
                    "teaching_pack_id": pack_data.get("teaching_pack_id"),
                    "errors": pack_data.get("errors", [])
                })
            else:
                logger.warning(f"No pack data found for group {group_key}")
                # Set defaults
                group_data.update({
                    "video_url": None,
                    "slides_url": None,
                    "video_thumbnail": None
                })
            
            # Override with video URL from video_urls field if available (higher priority)
            if group_key in video_urls_map:
                group_data["video_url"] = video_urls_map[group_key]
                logger.info(f"Overriding video_url for {group_key} from video_urls field: {video_urls_map[group_key]}")
            elif str(group_key).replace('_', ' ').title() in video_urls_map:
                normalized_key = str(group_key).replace('_', ' ').title()
                group_data["video_url"] = video_urls_map[normalized_key]
                logger.info(f"Overriding video_url for {group_key} from video_urls field (normalized): {video_urls_map[normalized_key]}")
            
            # Override with slides URL from slides_urls field if available (higher priority)
            if group_key in slides_urls_map:
                group_data["slides_url"] = slides_urls_map[group_key]
                logger.info(f"Overriding slides_url for {group_key} from slides_urls field: {slides_urls_map[group_key]}")
            elif str(group_key).replace('_', ' ').title() in slides_urls_map:
                normalized_key = str(group_key).replace('_', ' ').title()
                group_data["slides_url"] = slides_urls_map[normalized_key]
                logger.info(f"Overriding slides_url for {group_key} from slides_urls field (normalized): {slides_urls_map[normalized_key]}")
            
            # Override with flashcard URL from flashcard_urls field if available (higher priority)
            if group_key in flashcard_urls_map:
                group_data["flashcard_url"] = flashcard_urls_map[group_key]
                logger.info(f"Overriding flashcard_url for {group_key} from flashcard_urls field: {flashcard_urls_map[group_key]}")
            elif str(group_key).replace('_', ' ').title() in flashcard_urls_map:
                normalized_key = str(group_key).replace('_', ' ').title()
                group_data["flashcard_url"] = flashcard_urls_map[normalized_key]
                logger.info(f"Overriding flashcard_url for {group_key} from flashcard_urls field (normalized): {flashcard_urls_map[normalized_key]}")
            
            logger.info(f"Final video_url for {group_key}: {group_data.get('video_url')}")
            logger.info(f"Final slides_url for {group_key}: {group_data.get('slides_url')}")
            logger.info(f"Final flashcard_url for {group_key}: {group_data.get('flashcard_url')}")
    
    return {
        "classroom_id": classroom_id,
        "num_groups": len(groups_config) if isinstance(groups_config, dict) else 0,  # type: ignore
        "groups": groups_config
    }
