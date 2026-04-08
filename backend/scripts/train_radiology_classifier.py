from __future__ import annotations

import runpy
from pathlib import Path


if __name__ == "__main__":
    project_root = Path(__file__).resolve().parents[2]
    runpy.run_path(str(project_root / "scripts" / "train_radiology_classifier.py"), run_name="__main__")
