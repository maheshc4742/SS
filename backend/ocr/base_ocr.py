from abc import ABC, abstractmethod
from typing import Dict, Optional, List

class BaseOCR(ABC):
    """
    Abstract Base Class for OCR providers.
    Extracts handwritten descriptive answers from image or PDF bytes,
    returning a structured mapping of question number -> extracted answer string.
    """

    @abstractmethod
    async def extract_answers(
        self,
        file_bytes: bytes,
        filename: str,
        questions_hint: Optional[List[str]] = None
    ) -> Dict[str, str]:
        """
        Extract answers from the provided file.
        
        Args:
            file_bytes: Raw bytes of the uploaded file (.png, .jpg, .jpeg, .pdf)
            filename: Name of the uploaded file to detect extension/type
            questions_hint: Optional list of question keys to look for (e.g. ["1", "2", "3"])
            
        Returns:
            Dict[str, str]: Mapping of question number to extracted answer text.
            Example: {"1": "Student answer 1...", "2": "Student answer 2..."}
        """
        pass
