import json
import random
import logging
from typing import Tuple, List, Dict, Any
from pathlib import Path
from backend.core.config import DATA_DIR
from backend.training.dataset import ScriptSenseDataset

logger = logging.getLogger(__name__)

def split_and_prepare_dataset(
    source_file: Path = DATA_DIR / "verified_training.jsonl",
    train_ratio: float = 0.70,
    val_ratio: float = 0.15,
    test_ratio: float = 0.15,
    seed: int = 42
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Splits verified training data into Train, Validation, and Test sets.
    Never trains and tests on the same examples.
    """
    loader = ScriptSenseDataset(source_file)
    records = loader.load_verified_data()

    if not records:
        raise ValueError(f"No verified training samples found in {source_file}")

    random.seed(seed)
    shuffled = list(records)
    random.shuffle(shuffled)

    n = len(shuffled)
    n_train = int(n * train_ratio)
    n_val = int(n * val_ratio)

    train_set = shuffled[:n_train]
    val_set = shuffled[n_train:n_train + n_val]
    test_set = shuffled[n_train + n_val:]

    # Save to disk for inspection and reproducibility
    for filename, split_data in [
        ("train_split.jsonl", train_set),
        ("val_split.jsonl", val_set),
        ("test_split.jsonl", test_set)
    ]:
        out_path = DATA_DIR / filename
        with open(out_path, "w", encoding="utf-8") as f:
            for item in split_data:
                f.write(json.dumps(item) + "\n")
        logger.info(f"Saved {len(split_data)} records to {out_path}")

    return train_set, val_set, test_set
