"""Limited and non-executing inspection of legacy XLS/XLSX uploads.

The uploaded workbook is retained only inside the private add-on /data.
This stage does NOT infer assignments or map columns automatically.
"""
from __future__ import annotations

from pathlib import Path

from python_calamine import CalamineWorkbook

MAX_UPLOAD_BYTES = 32 * 1024 * 1024
MAX_SHEETS = 100
MAX_COLUMNS = 500
MAX_ROWS = 500_000


def check_signature(path: Path, suffix: str):
    with path.open("rb") as stream:
        header = stream.read(8)
    is_xls = header == bytes.fromhex("D0CF11E0A1B11AE1")
    is_zip = header[:4] == b"PK\x03\x04"
    if suffix == ".xls" and not is_xls:
        raise ValueError("Il file non è un vero Excel .xls")
    if suffix == ".xlsx" and not is_zip:
        raise ValueError("Il file non è un vero Excel .xlsx")


def inspect_workbook(path: Path) -> list[dict]:
    # Calamine reads values, never executes formulas or VBA.
    workbook = CalamineWorkbook.from_path(path)
    names = workbook.sheet_names
    if not names or len(names) > MAX_SHEETS:
        raise ValueError("Numero di fogli non consentito")
    metadata: list[dict] = []
    for name in names:
        sheet = workbook.get_sheet_by_name(name)
        if sheet.width > MAX_COLUMNS or sheet.height > MAX_ROWS:
            raise ValueError("Il file supera i limiti delle dimensioni consentite")
        sample = sheet.to_python(skip_empty_area=False, nrows=6)
        preview = []
        for row in sample:
            preview.append([str(value)[:120] if value is not None else "" for value in row[:12]])
        metadata.append({
            "name": name[:100],
            "rows": sheet.height,
            "columns": sheet.width,
            "preview": preview,
        })
    return metadata
