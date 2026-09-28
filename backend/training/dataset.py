import json
import logging
from typing import List, Dict, Any
from pathlib import Path
from backend.core.config import DATA_DIR

logger = logging.getLogger(__name__)

class ScriptSenseDataset:
    """
    Dataset loader for verified training records.
    Only loads records where human_verified == True.
    """

    def __init__(self, file_path: Path = DATA_DIR / "verified_training.jsonl"):
        self.file_path = file_path

    def load_verified_data(self) -> List[Dict[str, Any]]:
        if not self.file_path.exists():
            logger.warning(f"Training data file {self.file_path} does not exist.")
            return []

        records = []
        with open(self.file_path, "r", encoding="utf-8") as f:
            for idx, line in enumerate(f):
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    # Strictly ensure only human_verified records are used
                    if data.get("human_verified") is True:
                        records.append(data)
                except Exception as e:
                    logger.error(f"Error parsing line {idx} in {self.file_path}: {e}")

        logger.info(f"Loaded {len(records)} verified training records from {self.file_path}.")
        return records
