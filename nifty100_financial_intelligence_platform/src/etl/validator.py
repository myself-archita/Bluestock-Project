from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import pandas as pd


@dataclass
class ValidationResult:
    file_name: str
    passed: bool
    failures: int
    notes: str


def validate_frame(name: str, df: pd.DataFrame) -> ValidationResult:
    failures = 0
    notes = []
    if df.empty:
        failures += 1
        notes.append("empty frame")
    if df.columns.duplicated().any():
        failures += 1
        notes.append("duplicate columns")
    if df.isna().all(axis=1).any():
        failures += 1
        notes.append("blank rows")
    if df.shape[1] < 2:
        failures += 1
        notes.append("too few columns")
    return ValidationResult(name, failures == 0, failures, "; ".join(notes) or "ok")


def run_validations(frames: dict[str, pd.DataFrame], output_csv: str | Path) -> pd.DataFrame:
    results = [validate_frame(name, df) for name, df in frames.items()]
    out = pd.DataFrame([r.__dict__ for r in results])
    Path(output_csv).parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(output_csv, index=False)
    return out
