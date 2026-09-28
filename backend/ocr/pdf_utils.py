import io
from typing import List
import pymupdf as fitz

def render_pdf_to_images(pdf_bytes: bytes, dpi: int = 200) -> List[bytes]:
    """
    Renders each page of a PDF document into PNG image bytes using PyMuPDF (fitz).
    Does NOT use Tesseract or any external binaries.
    
    Args:
        pdf_bytes: Raw bytes of the PDF file
        dpi: Resolution for rendering (default 200 DPI for clear OCR)
        
    Returns:
        List of PNG image bytes, one per page.
    """
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    page_images: List[bytes] = []
    
    # Render with zoom corresponding to desired DPI (72 is default PDF points)
    zoom = dpi / 72.0
    matrix = fitz.Matrix(zoom, zoom)
    
    for page in doc:
        pix = page.get_pixmap(matrix=matrix, alpha=False)
        img_bytes = pix.tobytes("png")
        page_images.append(img_bytes)
        
    doc.close()
    return page_images

def is_pdf(filename: str) -> bool:
    """Check if the filename has a PDF extension."""
    return filename.lower().endswith(".pdf")
