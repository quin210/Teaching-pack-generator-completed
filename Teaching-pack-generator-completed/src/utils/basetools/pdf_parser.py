"""
PDF Parser Tool
Extracts text content from PDF files with OCR support
"""
import PyPDF2
from typing import Optional, Literal
import pytesseract
from pdf2image import convert_from_path
from PIL import Image



def extract_text_from_pdf(
    pdf_path: str, 
    max_pages: Optional[int] = None,
    use_ocr: bool = False,
    lang: str = 'vie+eng'
) -> str:
    """
    Extract text content from a PDF file with optional OCR support
    
    Args:
        pdf_path: Path to PDF file
        max_pages: Maximum number of pages to extract (None = all pages)
        use_ocr: If True, use OCR for image-based PDFs (requires pytesseract and pdf2image)
        lang: OCR language(s), default 'vie+eng' for Vietnamese and English
    
    Returns:
        Extracted text content
        
    Raises:
        Exception: If file reading fails or OCR dependencies are missing
    """
    text = ""
    
    try:
        # Try standard text extraction first
        if not use_ocr:
            with open(pdf_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                num_pages = len(pdf_reader.pages)
                
                pages_to_read = min(num_pages, max_pages) if max_pages else num_pages
                
                for page_num in range(pages_to_read):
                    page = pdf_reader.pages[page_num]
                    extracted = page.extract_text()
                    
                    # If no text found, fall back to OCR
                    if not extracted.strip():
                        return extract_text_from_pdf(pdf_path, max_pages, use_ocr=True, lang=lang)
                    
                    text += extracted + "\n\n"
        else:
            # Convert PDF to images
            images = convert_from_path(pdf_path)
            num_pages = len(images)
            pages_to_read = min(num_pages, max_pages) if max_pages else num_pages
            
            # Extract text from each page image using OCR
            for page_num in range(pages_to_read):
                page_text = pytesseract.image_to_string(images[page_num], lang=lang)
                text += page_text + "\n\n"
    
    except Exception as e:
        raise Exception(f"Error reading PDF file: {str(e)}")
    
    return text.strip()


def extract_text_with_ocr(image_path: str, lang: str = 'vie+eng') -> str:
    """
    Extract text from an image file using OCR
    
    Args:
        image_path: Path to image file (jpg, png, etc.)
        lang: OCR language(s), default 'vie+eng' for Vietnamese and English
    
    Returns:
        Extracted text content
        
    Raises:
        Exception: If OCR dependencies are missing or image reading fails
    """
    
    try:
        image = Image.open(image_path)
        text = pytesseract.image_to_string(image, lang=lang)
        return text.strip()
    except Exception as e:
        raise Exception(f"Error performing OCR on image: {str(e)}")


def read_text_file(file_path: str) -> str:
    """
    Read text from a plain text file
    
    Args:
        file_path: Path to text file
    
    Returns:
        File content
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        raise Exception(f"Error reading text file: {str(e)}")
