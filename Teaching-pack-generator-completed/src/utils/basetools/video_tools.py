"""
Video Tools
Tools for generating short video content using Gemini AI and Google Veo3
"""
import os
import time
import uuid
from pathlib import Path
from google import genai
from google.genai import types
from typing import Optional, Dict, Any

from utils.r2_storage import upload_fileobj_to_r2
from utils.r2_public import r2_public_url, safe_key


def generate_video_from_prompt(
    prompt: str,
    duration_seconds: int = 5,
    aspect_ratio: str = "16:9",
    negative_prompt: str = "",
    resolution: str = "720p",
    api_key: Optional[str] = None
) -> Dict[str, Any]:
    """
    Generate a short video from text prompt using Google Veo3 and upload to R2.
    """
    if not api_key:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("Gemini API key not found. Please set GEMINI_API_KEY environment variable.")

    try:
        client = genai.Client(api_key=api_key)
        operation = client.models.generate_videos(
            model="veo-3.1-generate-preview",
            prompt=prompt,
            config=types.GenerateVideosConfig(
                negative_prompt=negative_prompt if negative_prompt else None,
                aspect_ratio=aspect_ratio,
                resolution=resolution,
                duration_seconds=duration_seconds,
            ),
        )

        if isinstance(operation, str):
            return {"success": False, "error": "Unexpected operation response from Veo3"}

        while not operation.done:
            time.sleep(10)
            operation = client.operations.get(operation)

        if operation.error:
            return {"success": False, "error": f"Video generation failed: {operation.error}"}

        generated_videos = getattr(operation.response, "generated_videos", None) if operation.response else None
        if not generated_videos:
            return {"success": False, "error": "No video generated"}

        generated_video = generated_videos[0]
        video_ref = getattr(generated_video, "video", None)
        if not video_ref:
            return {"success": False, "error": "Missing video reference in response"}

        outputs_dir = Path(os.getenv("OUTPUT_DIR", "outputs"))
        outputs_dir.mkdir(parents=True, exist_ok=True)

        video_filename = f"generated_video_{uuid.uuid4().hex[:8]}.mp4"
        video_path = outputs_dir / video_filename

        download = client.files.download(file=video_ref)
        if hasattr(download, "read"):
            video_bytes = download.read()
        elif isinstance(download, bytes):
            video_bytes = download
        elif hasattr(download, "data"):
            video_bytes = download.data
        else:
            return {"success": False, "error": "Unexpected download response"}

        video_path.write_bytes(video_bytes)

        r2_key = safe_key(f"assets/videos/{video_filename}")
        with open(video_path, "rb") as f:
            upload_fileobj_to_r2(f, r2_key, content_type="video/mp4")

        return {
            "success": True,
            "video_path": str(video_path).replace("\\", "/"),
            "video_url": r2_public_url(r2_key),
            "thumbnail_url": getattr(generated_video, "thumbnail_url", None),
            "duration_seconds": duration_seconds,
            "aspect_ratio": aspect_ratio,
            "resolution": resolution,
            "file_size": video_path.stat().st_size
        }
    except Exception as e:
        return {"success": False, "error": f"Error generating video: {str(e)}"}


def generate_video_script(
    topic: str,
    duration_seconds: int = 60,
    style: str = "educational",
    api_key: Optional[str] = None
) -> str:
    """
    Generate a short video script using Gemini AI
    
    Args:
        topic: The main topic for the video
        duration_seconds: Target duration in seconds (default: 60)
        style: Video style (educational, promotional, tutorial, etc.)
        api_key: Gemini API key (optional, uses GEMINI_API_KEY env var)
    
    Returns:
        Generated video script as string
    """
    if not api_key:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("Gemini API key not found. Please set GEMINI_API_KEY environment variable.")
    
    import google.generativeai as genai_old
    genai_old.configure(api_key=api_key)
    model = genai_old.GenerativeModel('gemini-2.0-flash')
    
    prompt = f"""
    Create a script for a short {style} video about: {topic}
    
    Requirements:
    - Target duration: approximately {duration_seconds} seconds
    - Include spoken narration text
    - Suggest visual elements and transitions
    - Keep it engaging and concise
    - Format as a professional video script
    
    Structure the script with:
    1. Opening hook
    2. Main content
    3. Key points
    4. Call to action/closing
    
    Make it suitable for {style} content.
    """
    
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"Error generating video script: {str(e)}"


def generate_video_description(
    topic: str,
    platform: str = "YouTube",
    api_key: Optional[str] = None
) -> Dict[str, str]:
    """
    Generate video title, description, and tags using Gemini AI
    
    Args:
        topic: The video topic
        platform: Target platform (YouTube, TikTok, Instagram, etc.)
        api_key: Gemini API key (optional, uses GEMINI_API_KEY env var)
    
    Returns:
        Dict with title, description, and tags
    """
    if not api_key:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("Gemini API key not found. Please set GEMINI_API_KEY environment variable.")
    
    import google.generativeai as genai_old
    genai_old.configure(api_key=api_key)
    model = genai_old.GenerativeModel('gemini-2.0-flash')
    
    prompt = f"""
    Create optimized content for a {platform} video about: {topic}
    
    Provide:
    1. Catchy title (under 60 characters)
    2. Engaging description (150-200 words)
    3. Relevant tags (10-15 tags)
    
    Optimize for {platform} algorithm and audience engagement.
    Format as JSON with keys: title, description, tags (as array)
    """
    
    try:
        response = model.generate_content(prompt)
        # Parse JSON response
        import json
        result = json.loads(response.text.strip())
        return result
    except Exception as e:
        return {
            "title": f"Video about {topic}",
            "description": f"A video exploring {topic}",
            "tags": [topic],
            "error": str(e)
        }


def generate_video_storyboard(
    script: str,
    api_key: Optional[str] = None
) -> str:
    """
    Generate a storyboard description from a video script using Gemini AI
    
    Args:
        script: The video script text
        api_key: Gemini API key (optional, uses GEMINI_API_KEY env var)
    
    Returns:
        Storyboard description as string
    """
    if not api_key:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("Gemini API key not found. Please set GEMINI_API_KEY environment variable.")
    
    import google.generativeai as genai_old
    genai_old.configure(api_key=api_key)
    model = genai_old.GenerativeModel('gemini-2.0-flash')
    
    prompt = f"""
    Create a detailed storyboard for this video script:
    
    {script}
    
    For each scene, describe:
    - Visual elements
    - Camera angles
    - Text overlays
    - Transitions
    - Timing
    
    Format as a numbered list of scenes.
    """
    
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"Error generating storyboard: {str(e)}"
