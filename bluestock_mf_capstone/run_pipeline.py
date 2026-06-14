from __future__ import annotations

"""Master execution script for the Bluestock mutual fund capstone."""

import subprocess
import sys
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
PYTHON = sys.executable


def run_script(script_name: str, *args: str) -> None:
    script_path = BASE_DIR / "scripts" / script_name
    subprocess.run([PYTHON, str(script_path), *args], check=True)


def main() -> None:
    run_script("etl_pipeline.py")
    run_script("compute_metrics.py")
    run_script("eda_analysis.py")
    run_script("performance_analytics.py")
    run_script("recommender.py", "Moderate")
    run_script("live_nav_fetch.py")


if __name__ == "__main__":
    main()
