"""
File serving routes
Handles serving output files, videos, and slides
"""
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pathlib import Path

router = APIRouter(prefix="/api", tags=["Files"])

# Will be imported from main module
OUTPUT_DIR = None


def set_output_dir(output_dir: Path):
    """Set OUTPUT_DIR from main module"""
    global OUTPUT_DIR
    OUTPUT_DIR = output_dir


@router.get("/outputs/{filename}")
async def get_output_file(filename: str):
    """
    Download output file
    
    - **filename**: Name of the output file
    """
    # Strip "outputs/" prefix if present
    if filename.startswith("outputs/"):
        filename = filename[len("outputs/"):]
    
    file_path = OUTPUT_DIR / filename
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail=f"File {filename} not found")
    
    media_type = "application/octet-stream"
    if filename.endswith(".json"):
        media_type = "application/json"
    elif filename.endswith(".html"):
        media_type = "text/html"
    elif filename.endswith(".pdf"):
        media_type = "application/pdf"
    
    return FileResponse(
        path=str(file_path),
        filename=filename,
        media_type=media_type
    )


@router.get("/outputs")
async def list_outputs():
    """
    List all output files
    """
    output_files = [f.name for f in OUTPUT_DIR.glob("*.json")]
    return {
        "files": output_files,
        "count": len(output_files)
    }


@router.get("/videos/{filename}")
async def get_video_file(filename: str):
    """
    Serve video files
    
    - **filename**: Name of the video file
    """
    video_path = OUTPUT_DIR / filename
    
    if not video_path.exists():
        raise HTTPException(status_code=404, detail=f"Video file {filename} not found")
    
    return FileResponse(
        path=str(video_path),
        filename=filename,
        media_type="video/mp4"
    )


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
    response.headers["Content-Disposition"] = f"inline; filename=\"{filename}\""
    response.headers["Cache-Control"] = "public, max-age=3600"
    
    return response
