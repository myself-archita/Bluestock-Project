from __future__ import annotations

from pathlib import Path
import pandas as pd


def normalize_year(value):
    if pd.isna(value):
        return None
    text = str(value).strip()
    digits = "".join(ch for ch in text if ch.isdigit())
    if len(digits) >= 4:
        return int(digits[:4])
    if len(digits) == 2:
        num = int(digits)
        return 2000 + num if num < 50 else 1900 + num
    return None


def normalize_ticker(value):
    if pd.isna(value):
        return None
    text = str(value).strip().upper()
    for suffix in (".NS", ".BO", "-EQ"):
        text = text.replace(suffix, "")
    return text.replace(" ", "")


def load_excel(path: str | Path, header: int = 1) -> pd.DataFrame:
    return pd.read_excel(path, header=header)


def load_all_excels(folder: str | Path) -> dict[str, pd.DataFrame]:
    folder = Path(folder)
    return {item.stem: load_excel(item) for item in folder.glob("*.xlsx")}
