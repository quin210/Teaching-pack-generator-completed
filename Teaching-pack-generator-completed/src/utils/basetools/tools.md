# Tools and Extensions

## Overview

The system provides a rich set of tools to extend the capabilities of AI agents. These tools are designed in a reusable pattern and are easy to integrate.

## Built-in Tools

### 1. Slide Generation Tool

Tools for generating presentation slides using 2Slides API.

```python
from utils.basetools.slide_tools import generate_slides_from_text, get_slide_generation_status, search_themes, create_slides_from_image

# Generate slides from text
result = generate_slides_from_text(
    user_input="Your presentation content here",
    theme_id="theme-123",
    response_language="en"
)

# Check job status
status = get_slide_generation_status(job_id=result['jobId'])

# Search for themes
themes = search_themes(query="business", limit=10)

# Create slides from reference image
image_result = create_slides_from_image(
    user_input="Presentation content",
    reference_image_url="https://example.com/image.jpg",
    aspect_ratio="16:9",
    resolution="2K"
)
```

**Features:**

* Generate slides from text content
* Generate slides from reference images (Nano Banana Pro)
* Asynchronous job processing
* Theme search and selection
* Multiple language support
* Status checking for long-running jobs
* Customizable aspect ratio and resolution

**Use cases:**

* Automated presentation creation
* Educational content visualization
* Business report generation
* Marketing material creation

**API Requirements:**

* 2Slides API key (set TWOSLIDES_API_KEY environment variable)
* Internet connection for API calls

---

### 4. Video Generation Tool

Tools for generating short video content using Google Gemini AI and Veo3.

```python
from utils.basetools.video_tools import generate_video_script, generate_video_description, generate_video_storyboard, generate_video_from_prompt

# Generate video script
script = generate_video_script(
    topic="Machine Learning Basics",
    duration_seconds=90,
    style="educational"
)

# Generate video metadata
metadata = generate_video_description(
    topic="Machine Learning Basics",
    platform="YouTube"
)

# Create storyboard from script
storyboard = generate_video_storyboard(script)

# Generate actual video using Veo3
video_result = generate_video_from_prompt(
    prompt="A beautiful sunset over mountains with birds flying",
    duration_seconds=5,
    aspect_ratio="16:9",
    negative_prompt="dark, stormy",
    resolution="720p"
)
```

**Features:**

* AI-powered script generation for short videos
* Optimized titles, descriptions, and tags for social platforms
* Detailed storyboard creation from scripts
* Video generation from text prompts using Google Veo3.1
* Customizable duration and style
* Multi-platform optimization (YouTube, TikTok, Instagram)

**Use cases:**

* Educational video content creation
* Social media video production
* Marketing video scripts
* Tutorial and how-to videos
* Promotional content generation
* AI-generated video content

**API Requirements:**

* Google Gemini API key (set GEMINI_API_KEY environment variable)
* Internet connection for API calls
