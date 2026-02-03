"""
Job status routes
Handles async job status monitoring
"""
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict
from models.database_models import WorkflowJob
from api.dependencies import CurrentUser, DBSession
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/jobs", tags=["Jobs"])


class JobStatus(BaseModel):
    job_id: str
    status: str  # queued, processing, completed, failed
    progress: float = 0.0
    has_errors: bool = False
    error_count: int = 0
    message: Optional[str] = None
    result: Optional[Dict] = None
    error: Optional[str] = None


@router.get("/{job_id}")
async def get_job_status(
    job_id: str,
    current_user: CurrentUser,
    db: DBSession
):
    """
    Get the status of a teaching pack generation job
    
    - **job_id**: Job ID from generate_teaching_packs endpoint
    
    Returns: Job status (queued, processing, completed, failed)
    
    Requires authentication.
    """
    job = db.query(WorkflowJob).filter(WorkflowJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    if job.created_by_id and job.created_by_id != current_user.id:  # type: ignore
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    raw_status = (job.status or "queued").lower()
    status_map = {
        "pending": "queued",
        "completed_with_errors": "completed"
    }
    normalized_status = status_map.get(raw_status, raw_status)
    if normalized_status not in {"queued", "processing", "completed", "failed"}:
        normalized_status = "queued"

    stale_message = None
    if normalized_status == "processing" and job.updated_at:
        updated_at = job.updated_at  # type: ignore
        if updated_at.tzinfo is None:
            updated_at = updated_at.replace(tzinfo=timezone.utc)
        if datetime.now(timezone.utc) - updated_at > timedelta(minutes=30):
            normalized_status = "failed"
            stale_message = "Job appears stale (worker may have restarted). Please retry."

    errors = []
    if isinstance(job.result_json, dict):  # type: ignore
        errors = job.result_json.get("errors") or []  # type: ignore
    has_errors = isinstance(errors, list) and len(errors) > 0
    error_count = len(errors) if has_errors else 0

    message = job.message  # type: ignore
    if stale_message:
        message = stale_message if not message else f"{message} {stale_message}"

    return JobStatus(
        job_id=str(job.id),
        status=normalized_status,
        progress=job.progress or 0.0,  # type: ignore
        has_errors=has_errors,
        error_count=error_count,
        message=message,  # type: ignore
        result=job.result_json if normalized_status == "completed" else None,  # type: ignore
        error=message if normalized_status == "failed" else None  # type: ignore
    )
