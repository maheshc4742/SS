from typing import Optional
from backend.ocr.base_ocr import BaseOCR
from backend.ocr.gemini_ocr import GeminiOCR
from backend.ocr.qwen_ocr import QwenOCR
from backend.core.config import settings

def get_ocr_engine(provider: Optional[str] = None) -> BaseOCR:
    """
    Factory function to instantiate the selected OCR provider.
    Switchable between Local Qwen and Gemini API without changing application code.
    
    Args:
        provider: 'qwen' or 'gemini'. If None, uses settings.OCR_PROVIDER.
        
    Returns:
        BaseOCR instance (GeminiOCR or QwenOCR).
    """
    selected = (provider or settings.OCR_PROVIDER).strip().lower()
    
    if selected == "qwen":
        return QwenOCR()
    elif selected == "gemini":
        return GeminiOCR()
    else:
        # Default fallback
        return GeminiOCR()
