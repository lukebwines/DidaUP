"""Immutable historical baseline read directly from a chosen DidaUP export ZIP.

Only the five byte-identical original XLSX files are used as the authoritative
comparison baseline. Live source mappings, annuality filters, assignment-title
exclusions and workload settings are intentionally never consulted.
"""
from __future__ import annotations

import hashlib
import io
from pathlib import Path
from zipfile import ZipFile, BadZipFile

from python_calamine import CalamineWorkbook

from .department_workbooks import ALL_HEADERS, HISTORIC_HEADERS, VISIBLE_HEADERS, _display

MAX_REFERENCE_EXCEL_BYTES = 32 * 1024 * 1024
MAX_REFERENCE_ROWS = 60_000


class ReferenceSnapshotError(ValueError):
    pass


def read_reference_snapshot(path: Path) -> dict:
    """Verify ZIP, identical five files, technical IDs and sixth audit register."""
    if not path.is_file() or path.is_symlink():
        raise ReferenceSnapshotError("Pacchetto di riferimento non disponibile")
    if path.stat().st_size > 120 * 1024 * 1024:
        raise ReferenceSnapshotError("Pacchetto di riferimento troppo grande")
    try:
        archive_digest = hashlib.sha256(path.read_bytes()).hexdigest()
        with ZipFile(path) as archive:
            names = archive.namelist()
            if len(names) != 6 or len(set(names)) != 6:
                raise ReferenceSnapshotError(
                    "Il riferimento deve contenere cinque Excel e un registro interno"
                )
            referents = []
            for number in range(1, 6):
                found = [
                    name for name in names
                    if name.endswith(f"_Dipartimento_{number:02d}.xlsx")
                ]
                if len(found) != 1:
                    raise ReferenceSnapshotError(
                        f"File del referente {number} assente o duplicato"
                    )
                referents.append(found[0])
            audits = [name for name in names if name.endswith("_CONTROLLO_INTERNO.xlsx")]
            if len(audits) != 1 or set(referents + audits) != set(names):
                raise ReferenceSnapshotError(
                    "Struttura dei sei file dell'estrazione non valida"
                )
            for name in names:
                member = archive.getinfo(name)
                if (member.is_dir() or member.file_size > MAX_REFERENCE_EXCEL_BYTES
                        or "/" in name or "\\" in name):
                    raise ReferenceSnapshotError("Nome o dimensione interna non ammessa")
            xlsx = archive.read(referents[0])
            digest = hashlib.sha256(xlsx).digest()
            for name in referents[1:]:
                if hashlib.sha256(archive.read(name)).digest() != digest:
                    raise ReferenceSnapshotError(
                        "I cinque Excel originali del pacchetto non sono identici"
                    )
            audit = archive.read(audits[0])
    except ReferenceSnapshotError:
        raise
    except (BadZipFile, OSError, ValueError, RuntimeError) as exc:
        raise ReferenceSnapshotError("Pacchetto ZIP di riferimento non leggibile") from exc

    try:
        with CalamineWorkbook.from_filelike(io.BytesIO(xlsx)) as workbook:
            if workbook.sheet_names != ["Proposte SSD"]:
                raise ReferenceSnapshotError("Foglio del riferimento non valido")
            sheet = workbook.get_sheet_by_name("Proposte SSD")
            if sheet.width != len(ALL_HEADERS) or sheet.height > MAX_REFERENCE_ROWS + 6:
                raise ReferenceSnapshotError("Dimensioni del riferimento non valide")
            rows = sheet.to_python(skip_empty_area=False)
        if len(rows) < 7 or list(rows[5]) != ALL_HEADERS:
            raise ReferenceSnapshotError("Intestazioni del riferimento non valide")
        expected = {}
        for number, row in enumerate(rows[6:], start=7):
            if len(row) != len(ALL_HEADERS):
                raise ReferenceSnapshotError(
                    f"Riga {number} incompleta nel riferimento"
                )
            row_type, origin, proposal, activity = (
                _display(row[i]) for i in range(37, 41)
            )
            if (row_type != "STORICO" or not origin or origin != proposal
                    or not activity or origin in expected):
                raise ReferenceSnapshotError(
                    f"Identificativo storico incoerente nel riferimento, riga {number}"
                )
            if any(_display(row[i]) for i in range(29, 33)):
                raise ReferenceSnapshotError(
                    "Il pacchetto di riferimento contiene proposte compilate"
                )
            expected[origin] = {
                "activity_id": activity,
                "data": {
                    header: row[i] for i, header in enumerate(VISIBLE_HEADERS)
                },
            }
        with CalamineWorkbook.from_filelike(io.BytesIO(audit)) as workbook:
            if workbook.sheet_names != ["Righe escluse"]:
                raise ReferenceSnapshotError("Registro interno di esclusione non valido")
            audit_rows = workbook.get_sheet_by_name("Righe escluse").to_python(
                skip_empty_area=False
            )
        if len(audit_rows) < 5:
            raise ReferenceSnapshotError("Registro interno incompleto")
        excluded_ids = set()
        for number, row in enumerate(audit_rows[5:], start=6):
            origin_column = len(HISTORIC_HEADERS) + 4
            origin = _display(row[origin_column]) if len(row) > origin_column else ""
            if not origin or origin in excluded_ids or origin in expected:
                raise ReferenceSnapshotError(
                    f"Riga {number} del registro interno non riconciliata"
                )
            excluded_ids.add(origin)
        if not expected:
            raise ReferenceSnapshotError("Nessuna riga storica nel riferimento")
    except ReferenceSnapshotError:
        raise
    except (OSError, ValueError, RuntimeError, IndexError) as exc:
        raise ReferenceSnapshotError("Excel del riferimento non leggibile") from exc

    return {
        "archive_sha256": archive_digest,
        "expected": expected,
        "historical_rows": len(expected),
        "excluded_rows": len(excluded_ids),
    }
