"""
Base tools and utilities package for the CodeBase.

This package provides a comprehensive collection of utility tools and functions
for various common tasks including:

- Text classification and semantic search
- Document processing and chunking
- File operations (reading, merging, searching)
- HTTP requests and web scraping
- Email sending and communication
- Calculator and mathematical operations
- FAQ and knowledge base management

All tools follow strong typing principles with proper input/output models,
comprehensive error handling, and detailed documentation. Each tool is designed
to be modular, reusable, and maintainable following enterprise software standards.

Key Features:
- Strong typing with no use of 'Any' types
- Comprehensive docstrings for all functions and classes
- Enum-based configuration for better type safety
- Structured input/output models using Pydantic
- Proper error handling and status reporting
- Factory functions for tool configuration
- Multilingual language support where applicable

Usage:
    from src.utils.basetools import classification_tool, faq_tool, http_tool

    # Use tools with proper input models
    result = classification_tool(SearchInput(query="text"), labels=["label1", "label2"])
"""

# Import all tools for easy access
# NOTE: These modules don't exist yet - commented out to prevent import errors
# from .classfication_tool import (
#     SearchInput as ClassificationInput,
#     SearchOutput as ClassificationOutput,
#     classify_scholarship_http,
#     ClassificationMode,
# )

# from .semantic_splitter import (
#     SemanticSplitter,
#     load_txt,
#     load_pdf,
#     load_docx,
#     Language,
#     FileType,
# )

from .slide_tools import (
    generate_slides_from_text,
    get_slide_generation_status,
    search_themes,
    create_slides_from_image,
)

from .video_tools import (
    generate_video_from_prompt,
)
__author__ = "Anonymous"
__description__ = "Base tools and utilities for the CodeBase"
