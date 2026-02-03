"""
Slide Tools
Tools for generating slides using 2Slides API
"""
import os
import requests
from typing import Optional, Dict, Any
from loguru import logger  # Added for logging

def generate_slides_from_text(
    user_input: str,
    theme_id: str,
    api_key: Optional[str] = None,
    response_language: str = "en",
    mode: str = "sync"
) -> Dict[str, Any]:
    """
    Generate slides from text input using 2Slides API
    """
    env_key = os.getenv("TWOSLIDES_API_KEY")
    
    # Debug logging
    logger.info(f"TWOSLIDES_API_KEY from env: {'SET' if env_key else 'NOT SET'} (length: {len(env_key) if env_key else 0})")

    if not api_key:
        api_key = env_key
        if not api_key:
            raise ValueError("2Slides API key not found. Please set TWOSLIDES_API_KEY environment variable.")

    # FIX: Remove any potential whitespace/newlines from the key
    api_key = api_key.strip()
    
    # Debug: Log first/last few chars of key
    logger.info(f"Using API key: {api_key[:8]}...{api_key[-4:]} (length: {len(api_key)})")
    
    url = "https://2slides.com/api/v1/slides/generate"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    # Correct payload according to 2Slides API documentation
    payload = {
        "userInput": user_input,
        "themeId": theme_id,
        "responseLanguage": response_language
    }

    try:
        # FIX: Use Session with trust_env=False to explicitly disable environment settings (proxies, netrc)
        # requests.post() does not accept trust_env as a direct argument.
        with requests.Session() as session:
            session.trust_env = False
            response = session.post(
                url, 
                json=payload, 
                headers=headers, 
                timeout=60
            )
        
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"Slide generation request failed: {e}")
        return {"error": str(e)}


def get_slide_generation_status(job_id: str, api_key: Optional[str] = None) -> Dict[str, Any]:
    """
    Check the status of a slide generation job
    
    Args:
        job_id: The job ID from generate_slides_from_text
        api_key: API key for 2Slides (optional, uses config if not provided)
    
    Returns:
        Dict containing job status and results
    """
    if not api_key:
        api_key = os.getenv("TWOSLIDES_API_KEY")
        if not api_key:
            raise ValueError("2Slides API key not found. Please set TWOSLIDES_API_KEY environment variable.")
    
    url = f"https://2slides.com/api/v1/jobs/{job_id}"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    try:
        with requests.Session() as session:
            session.trust_env = False
            response = session.get(url, headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        return {"error": str(e)}



def search_themes(query: str, api_key: Optional[str] = None, limit: int = 20) -> Dict[str, Any]:
    """
    Search for slide themes
    
    Args:
        query: Search query for themes
        api_key: API key for 2Slides (optional, uses config if not provided)
        limit: Maximum number of results (default: 20, max: 100)
    
    Returns:
        Dict containing matched themes
    """
    if not api_key:
        api_key = os.getenv("TWOSLIDES_API_KEY")
        if not api_key:
            raise ValueError("2Slides API key not found. Please set TWOSLIDES_API_KEY environment variable.")
    
    url = "https://2slides.com/api/v1/themes/search"
    headers = {
        "Authorization": f"Bearer {api_key}"
    }
    params = {
        "query": query,
        "limit": limit
    }
    
    try:
        with requests.Session() as session:
            session.trust_env = False
            response = session.get(url, headers=headers, params=params)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        return {"error": str(e)}


def create_slides_from_image(
    user_input: str,
    reference_image_url: str,
    api_key: Optional[str] = None,
    response_language: str = "Auto",
    aspect_ratio: str = "16:9",
    resolution: str = "2K",
    page: int = 1,
    content_detail: str = "concise"
) -> Dict[str, Any]:
    """
    Generate slides from a reference image using 2Slides API (Nano Banana Pro)
    
    Args:
        user_input: The text content to generate slides from
        reference_image_url: URL of the reference image
        api_key: API key for 2Slides (optional, uses env if not provided)
        response_language: Language for the response (default: Auto)
        aspect_ratio: Aspect ratio of slides (default: 16:9)
        resolution: Resolution of slides (default: 2K)
        page: Number of pages (0 for auto-detect, >=1 for specified, max: 100, default: 1)
        content_detail: Detail level (concise/standard, default: concise)
    
    Returns:
        Dict containing jobId, status, downloadUrl, jobUrl, slidePageCount or error
    """
    if not api_key:
        api_key = os.getenv("TWOSLIDES_API_KEY")
        if not api_key:
            raise ValueError("2Slides API key not found. Please set TWOSLIDES_API_KEY environment variable.")
    
    url = "https://2slides.com/api/v1/slides/create-like-this"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    payload = {
        "userInput": user_input,
        "referenceImageUrl": reference_image_url,
        "responseLanguage": response_language,
        "aspectRatio": aspect_ratio,
        "resolution": resolution,
        "page": page,
        "contentDetail": content_detail
    }
    
    try:
        with requests.Session() as session:
            session.trust_env = False
            response = session.post(url, json=payload, headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        return {"error": str(e)}