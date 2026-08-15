"""
Extract text from uploaded documents (PDF, TXT).
"""
import io
from PyPDF2 import PdfReader
from app.core.logging import logger


async def extract_text_from_file(file_bytes: bytes, filename: str) -> str:
    """
    Extract text from a file.
    Supports PDF and plain text files.
    """
    filename_lower = filename.lower()
    
    if filename_lower.endswith(".pdf"):
        return await _extract_from_pdf(file_bytes)
    elif filename_lower.endswith(".txt"):
        # Plain text file - decode bytes to string
        return file_bytes.decode("utf-8", errors="ignore")
    else:
        # Try to read as text anyway
        logger.warning(f"Unknown file type: {filename}, attempting text decode")
        return file_bytes.decode("utf-8", errors="ignore")


async def _extract_from_pdf(file_bytes: bytes) -> str:
    """
    Extract text from PDF using PyPDF2.
    """
    try:
        # io.BytesIO wraps bytes so PyPDF2 can read them like a file
        pdf_file = io.BytesIO(file_bytes)
        reader = PdfReader(pdf_file)
        
        text = ""
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
        
        extracted = text.strip()
        logger.info(f"Extracted {len(extracted)} characters from PDF")
        return extracted
        
    except Exception as e:
        logger.error(f"PDF extraction failed: {e}")
        raise ValueError(f"Could not parse PDF file: {e}")