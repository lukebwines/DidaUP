"""Conservative, synthetic-testable extraction of CdS annualities.

Each result is derived solely from the explicitly saved mapping and uploaded
source snapshot. No formulas, external service, guessed course codes, or
invented academic years. Invalid rows are listed, not silently accepted.
"""
from __future__ import annotations

import re
from pathlib import Path
from collections import defaultdict
from typing import Any

from python_calamine import CalamineWorkbook

REQUIRED = ("cds_codice", "cds_nome", "sede", "anno_corso")
MAX_ROWS = 100_000
MAX_COLUMNS = 250
MAX_COHORTS = 5_000
MAX_ANOMALY_EXAMPLES = 35
ACADEMIC = re.compile(r"^\s*(20\d{2})\s*[/\-]\s*(\d{2}|20\d{2})\s*$")


class CohortExtractionError(ValueError):
    """A source cannot be safely extracted with the saved mapping."""


def plain(value: Any) -> str:
    if value is None or isinstance(value, bool):
        return ""
    if isinstance(value, (float, int)) and float(value).is_integer():
        return str(int(value))
    return " ".join(str(value).split()).strip()


def course_year(value: Any) -> int | None:
    raw = plain(value)
    if re.fullmatch(r"(?:[1-9]|1[0-2])", raw):
        return int(raw)
    return None


def academic_year(value: Any) -> str | None:
    raw = plain(value)
    # A four-digit starting year can identify the corresponding academic year
    # when explicitly stored under the "Anno Accademico" column.
    if re.fullmatch(r"20\d{2}", raw):
        start = int(raw)
        return f"{start}/{(start + 1) % 100:02d}"
    result = ACADEMIC.fullmatch(raw)
    if not result:
        return None
    start, end = int(result.group(1)), int(result.group(2))
    if end != (start + 1) % 100 and end != start + 1:
        return None
    return f"{start}/{(start + 1) % 100:02d}"


def extract_cohorts(
    path: Path, sheet_name: str, header_row: int,
    assigned: dict[str, int], expected_aa: str,
) -> dict:
    missing = [key for key in REQUIRED if key not in assigned]
    if missing:
        raise CohortExtractionError(
            "La mappatura deve contenere codice CdS, denominazione CdS, sede e anno di corso. "
            "Campi assenti: " + ", ".join(missing)
        )
    wb = CalamineWorkbook.from_path(path)
    if sheet_name not in wb.sheet_names:
        raise CohortExtractionError("Il foglio non è più presente nel report")
    sheet = wb.get_sheet_by_name(sheet_name)
    if (sheet.height > MAX_ROWS or sheet.width > MAX_COLUMNS or
            header_row < 1 or header_row >= sheet.height):
        raise CohortExtractionError("Dimensioni o riga delle intestazioni non valide")
    for key, column in assigned.items():
        if isinstance(column, bool) or not isinstance(column, int) or not 0 <= column < sheet.width:
            raise CohortExtractionError("Mappatura non valida per il campo: " + key)
    if sheet.height < 2:
        raise CohortExtractionError("Il report non contiene righe di dati")

    from .academic_year_rules import classify_source_year
    rows = sheet.to_python(skip_empty_area=False)
    convention_rows = 0
    groups: dict[tuple[str, str, int], dict] = {}
    names: dict[tuple[str, str, int], set[str]] = defaultdict(set)
    anomalies: list[dict] = []
    total_invalid = 0
    blank_rows = 0
    valid_rows = 0

    def issue(row_number: int, message: str):
        nonlocal total_invalid
        total_invalid += 1
        if len(anomalies) < MAX_ANOMALY_EXAMPLES:
            anomalies.append({"row": row_number, "reason": message})

    for number, row in enumerate(rows[header_row:], start=header_row + 1):
        if not any(plain(value) for value in row):
            blank_rows += 1
            continue
        def field(key: str) -> str:
            idx = assigned.get(key)
            return plain(row[idx]) if idx is not None and idx < len(row) else ""

        code = field("cds_codice")
        name = field("cds_nome")
        campus = field("sede")
        year_raw = field("anno_corso")
        study_year = course_year(year_raw)
        if not code or not name or not campus or study_year is None:
            issue(number, "Codice CdS, denominazione, sede o anno di corso assente/non valido")
            continue
        if not re.fullmatch(r"[A-Za-z0-9._-]{1,40}", code):
            issue(number, "Codice CdS non compatibile con il formato del registro")
            continue
        if len(name) < 2 or len(name) > 120 or len(campus) > 80:
            issue(number, "Descrizione CdS o sede fuori dai limiti ammessi")
            continue
        source_aa = field("anno_accademico_report")
        if "anno_accademico_report" in assigned:
            year_relation = classify_source_year(
                source_aa, expected_aa,
                course_type=field("cds_tipologia"),
                course_name=name,
            )
            if year_relation == "invalid":
                issue(number, "Anno accademico del report assente, non riconosciuto o diverso dall'A.A. selezionato")
                continue
            if year_relation == "specialization_convention":
                convention_rows += 1
        key = (code, campus, study_year)
        entry = groups.get(key)
        if entry is None:
            groups[key] = {
                "course_code": code, "course_name": name,
                "campus": campus, "study_year": study_year, "source_rows": 0,
            }
            entry = groups[key]
        entry["source_rows"] += 1
        names[key].add(name)
        valid_rows += 1
        if len(groups) > MAX_COHORTS:
            raise CohortExtractionError("Troppe annualità distinte nel file")

    ambiguous_groups = 0
    filtered = []
    for key, entry in groups.items():
        if len(names[key]) > 1:
            ambiguous_groups += 1
            issue(0, "Denominazioni CdS discordanti per lo stesso codice, sede e anno: da riconciliare")
        else:
            filtered.append(entry)
    filtered.sort(key=lambda v: (v["course_name"].casefold(), v["campus"].casefold(),
                                 v["study_year"], v["course_code"]))
    return {
        "sheet_name": sheet_name,
        "header_row": header_row,
        "source_rows": sheet.height - header_row,
        "valid_rows": valid_rows,
        "specialization_convention_rows": convention_rows,
        "blank_rows": blank_rows,
        "anomaly_count": total_invalid,
        "anomaly_examples": anomalies,
        "ambiguous_groups": ambiguous_groups,
        "cohorts": filtered,
        "cohort_count": len(filtered),
        "notice": (
            "Anteprima non distruttiva. Le anomalie sono escluse dall'elenco "
            "e devono essere risolte oppure esplicitamente accettate dall'amministratore."
        ),
    }
