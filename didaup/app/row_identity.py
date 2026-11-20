"""Technical identity for imported spreadsheet rows.

Used as an internal reference inside one immutable source snapshot only.
It is NOT an official UGOV coverage identifier and must never be used
to infer equivalence of teaching assignments between academic years.

The source SHA-256, sheet name and 1-based row number together distinguish
even textually identical source rows without processing personal data here.
"""
from __future__ import annotations

import hashlib
import json
import re


def source_row_id(source_sha256: str, sheet_name: str, excel_row: int) -> str:
    if not re.fullmatch(r"[0-9a-f]{64}", source_sha256):
        raise ValueError("SHA-256 del report non valido")
    if not isinstance(sheet_name, str) or not sheet_name or len(sheet_name) > 100:
        raise ValueError("Nome foglio non valido")
    if isinstance(excel_row, bool) or not isinstance(excel_row, int) or excel_row < 1:
        raise ValueError("Numero riga Excel non valido")
    identity = json.dumps(
        [source_sha256, sheet_name, excel_row],
        ensure_ascii=False, separators=(",", ":"),
    ).encode("utf-8")
    return "SRC-" + hashlib.sha256(identity).hexdigest()[:32]
