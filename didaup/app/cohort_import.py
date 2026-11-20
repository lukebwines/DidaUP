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


def course_years(value: Any) -> tuple[int, ...] | None:
    """Read explicit years only. A multi-year list describes multiple annualities.

    Accept 1,2,3 and 1; 2 and 1/2, never silently assign an unspecified year.
    Duplicates are deduplicated. Unsupported strings become review anomalies.
    """
    raw = plain(value)
    if not re.fullmatch(r"(?:[1-9]|1[0-2])(?:\s*[,;/]\s*(?:[1-9]|1[0-2]))*", raw):
        return None
    return tuple(sorted({int(v) for v in re.split(r"\s*[,;/]\s*", raw)}))


def course_year(value: Any) -> int | None:
    """Compatibility API: single course year only."""
    years = course_years(value)
    return years[0] if years and len(years) == 1 else None


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

    rows = sheet.to_python(skip_empty_area=False)
    groups: dict[tuple[str, str, int], dict] = {}
    names: dict[tuple[str, str, int], set[str]] = defaultdict(set)
    typologies: dict[tuple[str, str, int], set[str]] = defaultdict(set)
    assignment_titles: dict[tuple[str, str, int], set[str]] = defaultdict(set)
    anomalies: list[dict] = []
    total_invalid = 0
    blank_rows = 0
    valid_rows = 0
    multi_year_source_rows = 0
    anomalous_by_typology: dict[str, int] = defaultdict(int)
    anomalous_examples_by_typology: dict[str, list[dict]] = defaultdict(list)

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
        typology = field("cds_tipologia")
        assignment_title = field("titolo_affidamento")
        year_raw = field("anno_corso")
        study_years = course_years(year_raw)
        if not code or not name or not campus or study_years is None:
            issue(number, "Codice CdS, denominazione, sede o anno di corso assente/non valido")
            typology_label = typology or "Tipologia non indicata"
            anomalous_by_typology[typology_label] += 1
            examples = anomalous_examples_by_typology[typology_label]
            if len(examples) < 12:
                examples.append({
                    "row": number, "course_name": name[:150],
                    "course_code": code[:40], "year_value": year_raw[:50],
                })
            continue
        if not re.fullmatch(r"[A-Za-z0-9._-]{1,40}", code):
            issue(number, "Codice CdS non compatibile con il formato del registro")
            continue
        if len(name) < 2 or len(name) > 500 or len(campus) > 80:
            issue(number, "Descrizione CdS o sede fuori dai limiti ammessi")
            continue
        # The report is already linked by the operator to the selected
        # archive year. Row-level A.A. is historic context, not an exclusion
        # criterion (including school-of-specialization conventions).
        if len(study_years) > 1:
            multi_year_source_rows += 1
        # An explicit list such as "1,2,3" represents all three annualities.
        # It does not authorize marking them excluded; the saved checkboxes
        # remain the sole source of administrative exclusion decisions.
        for study_year in study_years:
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
            typologies[key].add(typology)
            assignment_titles[key].add(assignment_title)
            if len(groups) > MAX_COHORTS:
                raise CohortExtractionError("Troppe annualità distinte nel file")
        valid_rows += 1

    ambiguous_groups = 0
    filtered = []
    for key, entry in groups.items():
        if len(names[key]) > 1:
            ambiguous_groups += 1
            issue(0, "Denominazioni CdS discordanti per lo stesso codice, sede e anno: da riconciliare")
        else:
            # Preserve every source typology for a CdS/year, including blank values.
            # One annuality may appear in activities with different typologies.
            entry["course_types"] = sorted(typologies[key], key=str.casefold)
            entry["assignment_titles"] = sorted(
                assignment_titles[key], key=str.casefold
            )
            filtered.append(entry)
    filtered.sort(key=lambda v: (v["course_name"].casefold(), v["campus"].casefold(),
                                 v["study_year"], v["course_code"]))
    return {
        "sheet_name": sheet_name,
        "header_row": header_row,
        "source_rows": sheet.height - header_row,
        "valid_rows": valid_rows,
        "multi_year_source_rows": multi_year_source_rows,
        "invalid_source_rows_by_typology": [
            {
                "typology": name, "count": count,
                "examples": anomalous_examples_by_typology[name],
            }
            for name, count in sorted(
                anomalous_by_typology.items(), key=lambda item: item[0].casefold()
            )
        ],
        "blank_rows": blank_rows,
        "anomaly_count": total_invalid,
        "anomaly_examples": anomalies,
        "ambiguous_groups": ambiguous_groups,
        "cohorts": filtered,
        "cohort_count": len(filtered),
        "typology_mapped": "cds_tipologia" in assigned,
        "assignment_title_mapped": "titolo_affidamento" in assigned,
        "notice": (
            "Anteprima non distruttiva. Le anomalie sono escluse dall'elenco "
            "e devono essere risolte oppure esplicitamente accettate dall'amministratore."
        ),
    }
