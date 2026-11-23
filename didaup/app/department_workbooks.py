"""Generate FIVE byte-identical departmental workbooks from one saved offer report.

This is a working-stage export, NOT approval, publication or automatic teaching
assignment. The five copies intentionally contain the same complete scope:
there is no department filter. Source data never leave private /data except
when an authorized user explicitly downloads the generated working ZIP.
"""
from __future__ import annotations

import hashlib
import io
import json
import math
import secrets
from datetime import datetime, timezone
from itertools import combinations
import re
import unicodedata
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from python_calamine import CalamineWorkbook
import xlsxwriter

from .column_mapping import OFFER_HEADER_TO_FIELD, source_header_conflicts, normalize_header
from .row_identity import source_row_id
from .workload import (
    WorkloadRuleError, validate_rules, apply_workload, is_missing_planned_hours,
    matching_rule_indices, workload_cap_applied,
)

# Order of the pre-existing outgoing referent layout (not the 110-col source).
HISTORIC_HEADERS = [
    "SEDE CORSO", "CODICE CORSO", "CDS", "ANNO ACCADEMICO",
    "CFU TOTALI INS", "CODICE INS", "TIPOEROGAZIONE", "INSEGNAMENTO",
    "CODICE UGOV", "DISCRIMINANTE DI OI", "MODULO", "UL",
    "DISCRIMINANTE MODULO", "ANNO", "MUTUAZIONE", "Ins. Erogante",
    "TAF", "FUORI PIANO", "SSD INSEGNAMENTO", "CFU", "MOODLE",
    "MATRICOLA DOCENTE", "NOME DOCENTE", "COGNOME DOCENTE",
    "OREPREVLEZ", "CREDITITIR", "CODICE SSD DOCENTE NUOVO",
    "TOT ORE PREVISTE", "TOT ORE EFFETTIVE",
    "PERIODO INIZIO", "PERIODO FINE", "DIPARTIMENTO AFFERENZA DOCENTE",
    "TITOLO AFFIDAMENTO",
]
# Columns requested to be invisible to referents in ALL five workbooks.
# Hidden is a presentation rule, not secure redaction: values remain in XLSX.
HIDDEN_REFERENT_HEADERS = (
    "CODICE CORSO", "CFU TOTALI INS", "CODICE INS",
    "TIPOEROGAZIONE", "FUORI PIANO", "MOODLE",
    "MATRICOLA DOCENTE",
)
PROPOSAL_HEADERS = ("Tipo variazione", "Nuovo docente", "Ore", "Note")
# Position after TOT ORE EFFETTIVE, as agreed; 33 + 4 = 37 visible.
VISIBLE_HEADERS = HISTORIC_HEADERS[:29] + list(PROPOSAL_HEADERS) + HISTORIC_HEADERS[29:]
TECH_HEADERS = (
    "DIDAUP_TIPO_RIGA", "DIDAUP_ID_ORIGINE",
    "DIDAUP_ID_PROPOSTA", "DIDAUP_ID_ATTIVITA",
)
ALL_HEADERS = VISIBLE_HEADERS + list(TECH_HEADERS)
PROPOSAL_START = 29
PROPOSAL_END = 32
DATA_START_EXCEL_ROW = 7
MAX_EXPORT_ROWS = 60_000
MAX_STRING_LENGTH = 32_000
NUM_COPIES = 5

# The year in the source is historical; a prospective year is a label,
# never an assertion that the assignments have already been confirmed.
ACADEMIC = re.compile(r"20\d{2}/\d{2}\Z")


class WorkbookGenerationError(ValueError):
    pass


def next_academic_year(academic: str) -> str:
    if not ACADEMIC.fullmatch(academic):
        raise WorkbookGenerationError("Anno accademico dello storico non valido")
    start, end = int(academic[:4]), int(academic[-2:])
    if end != (start + 1) % 100:
        raise WorkbookGenerationError("Anno accademico incoerente")
    return f"{start+1}/{(start+2)%100:02d}"


def _display(value):
    if value is None or isinstance(value, bool):
        return ""
    if isinstance(value, float):
        if not math.isfinite(value):
            raise WorkbookGenerationError("Valore numerico non finito nel report")
        if value.is_integer():
            return str(int(value))
    return str(value).strip()


def _write_safe(sheet, row, col, value, locked):
    # write_string is intentional: NEVER evaluate source strings as Excel
    # formulas, hyperlinks or external links.
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if not math.isfinite(float(value)):
            raise WorkbookGenerationError("Valore numerico non valido nel report")
        sheet.write_number(row, col, value, locked)
    else:
        sheet.write_string(row, col, _display(value)[:MAX_STRING_LENGTH], locked)


def _activity_id(data: dict[str, object], historical_id: str) -> str:
    """Internal key only, never an official teaching-activity code.

    If neither course/UGOV code is available, the stable snapshot-row ID
    keeps the line distinct rather than guessing equivalences with other
    records. It is reproducible on all five copies and during re-review.
    """
    fields = [
        "CODICE CORSO", "SEDE CORSO", "ANNO", "CODICE INS",
        "CODICE UGOV", "DISCRIMINANTE DI OI", "MODULO", "UL",
        "DISCRIMINANTE MODULO", "SSD INSEGNAMENTO",
    ]
    payload = [_display(data.get(key)) for key in fields]
    if not (_display(data.get("CODICE INS")) or _display(data.get("CODICE UGOV"))):
        return "ACT-ROW-" + hashlib.sha256(
            historical_id.encode("utf-8")
        ).hexdigest()[:32]
    return "ACT-" + hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode()
    ).hexdigest()[:32]


def _canonical(value: object) -> str:
    """Only casing, Unicode width and whitespace; no invented code aliases."""
    return " ".join(unicodedata.normalize("NFKC", _display(value)).split()).casefold()


WORKBOOK_EXCLUSION_FILTER_KEYS = {
    "titoli": "titolo_affidamento",
    "tipologie": "cds_tipologia",
    "cds": "cds_codice",
    "sedi": "sede",
    "annualita": "anno_corso",
    "taf": "taf",
}


def _workbook_exclusion_cds_value(code: object, name: object) -> str:
    return json.dumps(
        [_display(code), _display(name)],
        ensure_ascii=False, separators=(",", ":"),
    )


def workbook_exclusion_choices(
    source: Path, source_sha256: str, sheet_name: str, header_row: int,
    assigned: dict[str, int], allowed_source_ids: set[str] | None = None,
) -> dict:
    """Distinct, counted exclusion facets from the rows retained for export."""
    if not re.fullmatch(r"[0-9a-f]{64}", source_sha256) or not source.is_file():
        raise WorkbookGenerationError("Fonte non valida per i filtri di esclusione")
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    if digest != source_sha256:
        raise WorkbookGenerationError("Il report non corrisponde alla fonte selezionata")
    workbook = CalamineWorkbook.from_path(source)
    if sheet_name not in workbook.sheet_names:
        raise WorkbookGenerationError("Foglio non presente nella fonte selezionata")
    sheet = workbook.get_sheet_by_name(sheet_name)
    if not 1 <= header_row <= 40 or sheet.height <= header_row:
        raise WorkbookGenerationError("Intestazione non valida per i filtri di esclusione")
    rows = sheet.to_python(skip_empty_area=False)
    mapped = {
        "titoli": "titolo_affidamento" in assigned,
        "tipologie": "cds_tipologia" in assigned,
        "cds": "cds_codice" in assigned or "cds_nome" in assigned,
        "sedi": "sede" in assigned,
        "annualita": "anno_corso" in assigned,
        "taf": "taf" in assigned,
    }
    values: dict[str, dict[str, dict]] = {
        key: {} for key in WORKBOOK_EXCLUSION_FILTER_KEYS
    }
    rows_in_scope = 0
    for excel_row, row in enumerate(rows[header_row:], start=header_row + 1):
        if not _source_row_has_content(row):
            continue
        if allowed_source_ids is not None and source_row_id(
            source_sha256, sheet_name, excel_row
        ) not in allowed_source_ids:
            continue
        rows_in_scope += 1

        def raw(key):
            column = assigned.get(key)
            return row[column] if column is not None and column < len(row) else ""

        for facet, field in WORKBOOK_EXCLUSION_FILTER_KEYS.items():
            if not mapped[facet]:
                continue
            if facet == "cds":
                code, name = _display(raw("cds_codice")), _display(raw("cds_nome"))
                value = _workbook_exclusion_cds_value(code, name)
                label = " · ".join(part for part in (name, code) if part)
            else:
                value = _display(raw(field))
                label = value
            if not value.strip():
                continue
            identity = _canonical(value)
            if facet == "cds":
                identity = _canonical(code) + "\\0" + _canonical(name)
            if identity not in values[facet]:
                values[facet][identity] = {
                    "value": value, "label": label, "count": 0,
                }
            values[facet][identity]["count"] += 1

    choices = {}
    for facet, options in values.items():
        choices[facet] = sorted(
            options.values(),
            key=lambda item: item["label"].casefold(),
        )
    return {"mapped": mapped, "choices": choices, "rows_in_scope": rows_in_scope}


def normalize_workbook_exclusion_filters(
    raw_filters: dict | None, choices: dict, assigned: dict[str, int],
) -> dict[str, list[str]]:
    """Validate user selections against values actually present in this report."""
    if raw_filters is None:
        raw_filters = {}
    if not isinstance(raw_filters, dict):
        raise WorkbookGenerationError("Filtri di esclusione non validi")
    unknown = set(raw_filters) - set(WORKBOOK_EXCLUSION_FILTER_KEYS)
    if unknown:
        raise WorkbookGenerationError("Uno o più filtri di esclusione non sono riconosciuti")
    normalized: dict[str, list[str]] = {}
    any_selected = False
    for facet in WORKBOOK_EXCLUSION_FILTER_KEYS:
        selected = raw_filters.get(facet, [])
        if not isinstance(selected, list) or len(selected) > 1000:
            raise WorkbookGenerationError("Selezione multipla non valida")
        clean = []
        for value in selected:
            if not isinstance(value, str) or not value.strip() or len(value) > 1000:
                raise WorkbookGenerationError("Valore selezionato non valido")
            if value not in clean:
                clean.append(value)
        if clean and not choices["mapped"].get(facet):
            raise WorkbookGenerationError(
                f"Il campo necessario al filtro «{facet}» non è associato nella mappatura"
            )
        available = {item["value"] for item in choices["choices"].get(facet, [])}
        if set(clean) - available:
            raise WorkbookGenerationError(
                f"Il filtro «{facet}» contiene valori non presenti nelle righe incluse del report"
            )
        normalized[facet] = clean
        any_selected = any_selected or bool(clean)
    if any_selected and not normalized["titoli"]:
        raise WorkbookGenerationError(
            "Selezionare almeno un Titolo affidamento: gli altri filtri servono a restringerne l'ambito"
        )
    return normalized


def matches_workbook_exclusion_filters(
    filters: dict[str, list[str]], get,
) -> bool:
    """Match titles as the primary criterion; optional facets narrow it with AND."""
    if not filters or not filters.get("titoli"):
        return False

    def selected_match(facet: str, actual: object) -> bool:
        selected = filters.get(facet) or []
        return not selected or _canonical(actual) in {
            _canonical(value) for value in selected
        }

    if not selected_match("titoli", get("titolo_affidamento")):
        return False
    if not selected_match("tipologie", get("cds_tipologia")):
        return False
    if not selected_match("sedi", get("sede")):
        return False
    if not selected_match("annualita", get("anno_corso")):
        return False
    if not selected_match("taf", get("taf")):
        return False
    if filters.get("cds"):
        actual = _workbook_exclusion_cds_value(
            get("cds_codice"), get("cds_nome")
        )
        if actual not in filters["cds"]:
            return False
    return True


def _normalized_cohort_key(course: object, campus: object, year: object):
    code, location = _canonical(course), _canonical(campus)
    year_str = _display(year)
    if (not code or not location
            or not re.fullmatch(r"(?:[1-9]|1[0-2])", year_str)):
        return None
    return (code, location, int(year_str))


def _normalized_course_site(course: object, campus: object):
    code, location = _canonical(course), _canonical(campus)
    return (code, location) if code and location else None


def _source_row_has_content(row: list) -> bool:
    """Count every populated source line, even if only a Boolean is present."""
    return any(
        value is not None and (not isinstance(value, str) or bool(value.strip()))
        for value in row
    )


def _verify_xlsx_ids(
    xlsx_bytes: bytes, sheet_name: str, first_data_row: int,
    id_column: int, expected_ids: list[str], file_label: str,
) -> None:
    """Read the *real generated Excel*, not the in-memory prepared model.

    Every source-row identifier must appear once and only once, in the
    expected original ordering. Fail closed before the ZIP is offered.
    """
    try:
        with CalamineWorkbook.from_filelike(io.BytesIO(xlsx_bytes)) as workbook:
            sheet = workbook.get_sheet_by_name(sheet_name)
            cells = sheet.to_python(skip_empty_area=False)
    except Exception as exc:
        raise WorkbookGenerationError(
            f"Verifica completezza: impossibile rileggere {file_label}"
        ) from exc
    actual = [
        str(row[id_column]).strip() if len(row) > id_column and row[id_column] is not None
        else ""
        for row in cells[first_data_row:]
    ]
    if actual == expected_ids:
        return
    expected_set, actual_set = set(expected_ids), set(actual)
    missing = [value for value in expected_ids if value not in actual_set]
    extra = [value for value in actual if value not in expected_set]
    duplicates = len(actual) - len(actual_set)
    raise WorkbookGenerationError(
        f"Verifica completezza fallita ({file_label}): "
        f"attese {len(expected_ids)} righe, rilevate {len(actual)}; "
        f"assenti {len(missing)}, estranee {len(extra)}, duplicate {duplicates}. "
        "La generazione è stata bloccata: nessun Excel deve essere distribuito."
    )


def _source_years(value: object) -> set[int] | None:
    """Parse an explicitly enumerated year set, e.g. 1 / 1,2,3 / 1; 2.

    Never infer an academic annuality from unrecognized textual values.
    """
    raw = _display(value).strip()
    if not re.fullmatch(
        r"(?:[1-9]|1[0-2])(?:\s*[,;/]\s*(?:[1-9]|1[0-2]))*", raw
    ):
        return None
    return {int(item) for item in re.split(r"\s*[,;/]\s*", raw)}


def _prepare(source: Path, source_sha256: str, sheet_name: str, header_row: int,
             assigned: dict[str, int], history_year: str,
             excluded: set[tuple[str, str, int]],
             included: set[tuple[str, str, int]] | None = None,
             cohort_names: dict[tuple[str, str, int], str] | None = None,
             workload_rules: list[dict] | None = None,
             strict_workload: bool = True,
             allow_empty: bool = False,
             assignment_exclusions: dict[str, list[str]] | None = None):
    if not re.fullmatch(r"[0-9a-f]{64}", source_sha256):
        raise WorkbookGenerationError("Hash dello storico non valido")
    if not source.is_file():
        raise WorkbookGenerationError("Report storico non disponibile")
    # Protect against stale or substituted snapshots.
    digest = hashlib.sha256()
    with source.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    if digest.hexdigest() != source_sha256:
        raise WorkbookGenerationError("Il report storico non corrisponde al suo hash registrato")
    if not 1 <= header_row <= 40:
        raise WorkbookGenerationError("Riga intestazioni fuori intervallo")
    # TOT ORE EFFETTIVE is an output-only calculated field. The input
    # association is optional and historical values must not be reused.
    required = (
        "cds_codice", "sede", "anno_corso",
    )
    missing = [key for key in required if key not in assigned]
    if missing:
        raise WorkbookGenerationError(
            "Mappatura incompleta per la generazione: " + ", ".join(missing)
        )
    wb = CalamineWorkbook.from_path(source)
    if sheet_name not in wb.sheet_names:
        raise WorkbookGenerationError("Foglio storico non presente nella fonte")
    sheet = wb.get_sheet_by_name(sheet_name)
    if sheet.height <= header_row or sheet.height > MAX_EXPORT_ROWS + header_row + 1:
        raise WorkbookGenerationError("Numero di righe storico non supportato")
    if sheet.width > 250 or any(
        isinstance(v, bool) or not isinstance(v, int) or v < 0 or v >= sheet.width
        for v in assigned.values()
    ):
        raise WorkbookGenerationError("Mappatura non valida")
    rows = sheet.to_python(skip_empty_area=False)
    # Old saved drafts may predate the new safeguard. Check them too.
    conflicts = source_header_conflicts(
        "offerta", assigned, rows[header_row - 1]
    )
    if conflicts:
        raise WorkbookGenerationError(
            "Mappatura salvata da correggere: " + "; ".join(conflicts[:5])
        )
    # Preserve explicitly saved choices. If the TAF field was omitted from
    # an older saved mapping, restore it ONLY from exactly one column whose
    # source header is literally "TAF". Never guess a TAF classification.
    taf_header_positions = [
        i for i, header in enumerate(rows[header_row - 1])
        if normalize_header(header) == "TAF"
    ]
    if "taf" in assigned:
        taf_mapping_mode = "mappatura salvata"
    elif len(taf_header_positions) == 1:
        assigned = {**assigned, "taf": taf_header_positions[0]}
        taf_mapping_mode = "intestazione TAF esatta, recuperata per export"
    elif taf_header_positions:
        taf_mapping_mode = "intestazione TAF ambigua: non associata"
    else:
        taf_mapping_mode = "campo TAF non associato e intestazione esatta assente"

    # Check the source's MUTUAZIONE column independently of prior drafts.
    # It may have been left unmapped by a legacy version. Only an exact,
    # unique header is a safe fallback; never invent a Boolean default.
    mutuazione_positions = [
        i for i, heading in enumerate(rows[header_row - 1])
        if normalize_header(heading) == "MUTUAZIONE"
    ]
    if "mutuazione" in assigned:
        mutuazione_mapping_mode = "mappatura salvata"
    elif len(mutuazione_positions) == 1:
        assigned = {**assigned, "mutuazione": mutuazione_positions[0]}
        mutuazione_mapping_mode = "intestazione MUTUAZIONE esatta, recuperata per export"
    elif mutuazione_positions:
        mutuazione_mapping_mode = "intestazione MUTUAZIONE ambigua: non associata"
    else:
        mutuazione_mapping_mode = "campo MUTUAZIONE non associato e intestazione esatta assente"

    try:
        effective_rules = validate_rules(workload_rules or [])
    except WorkloadRuleError as exc:
        raise WorkbookGenerationError(str(exc)) from exc
    effective_assignment_exclusions = assignment_exclusions or {}
    if effective_assignment_exclusions:
        if not effective_assignment_exclusions.get("titoli"):
            raise WorkbookGenerationError(
                "Esclusione incarichi: selezionare almeno un Titolo affidamento"
            )
        for facet, field in WORKBOOK_EXCLUSION_FILTER_KEYS.items():
            if effective_assignment_exclusions.get(facet) and field not in assigned:
                raise WorkbookGenerationError(
                    f"Esclusione incarichi: associare il campo necessario al filtro «{facet}»"
                )
    if "ore_previste" not in assigned:
        raise WorkbookGenerationError(
            "Calcolo carico: associare TOT ORE PREVISTE prima di generare i file"
        )
    if any(rule["tipologia"] for rule in effective_rules) and "cds_tipologia" not in assigned:
        raise WorkbookGenerationError(
            "Calcolo carico: associare TIPOLOGIA prima di usare regole per tipologia"
        )
    if any(rule["taf"] for rule in effective_rules) and "taf" not in assigned:
        raise WorkbookGenerationError(
            "Calcolo carico: associare TAF prima di usare regole per TAF"
        )

    excluded_keys = {_normalized_cohort_key(*item) for item in excluded}
    excluded_keys.discard(None)
    included_keys = {
        _normalized_cohort_key(*item) for item in (included or set())
    }
    included_keys.discard(None)
    # Name-based matching is ONLY a fallback for a missing/inconsistent
    # course code. Require a unique documented CdS identity in BOTH the
    # saved cohort register and the selected report. Ambiguity => no deletion.
    recorded_sites_by_title = {}
    for registered_key, registered_title in (cohort_names or {}).items():
        k = _normalized_cohort_key(*registered_key)
        title = _canonical(registered_title)
        if k is not None and title:
            recorded_sites_by_title.setdefault((title, k[1]), set()).add(k[:2])
    excluded_title_sites = set()
    included_title_sites = set()
    for register_key, register_name in (cohort_names or {}).items():
        normalized_key = _normalized_cohort_key(*register_key)
        normalized_name = _canonical(register_name)
        if not normalized_key or not normalized_name:
            continue
        title_site = (normalized_name, normalized_key[1])
        if normalized_key in excluded_keys:
            excluded_title_sites.add(title_site)
        if normalized_key in included_keys:
            included_title_sites.add(title_site)
    source_sites_by_title = {}
    if cohort_names and assigned.get("cds_nome") is not None:
        for raw in rows[header_row:]:
            if not _source_row_has_content(raw):
                continue
            def raw_field(name):
                col = assigned.get(name)
                return raw[col] if col is not None and col < len(raw) else ""
            src_title = _canonical(raw_field("cds_nome"))
            src_site = _normalized_course_site(
                raw_field("cds_codice"), raw_field("sede")
            )
            if src_title and src_site:
                source_sites_by_title.setdefault(
                    (src_title, src_site[1]), set()
                ).add(src_site)

    # Independent source coverage baseline, computed BEFORE filtering.
    # Rows whose only content is outside the mapped columns still count.
    source_row_numbers = [
        index for index, raw in enumerate(rows[header_row:], start=header_row + 1)
        if _source_row_has_content(raw)
    ]
    source_ids = {
        source_row_id(source_sha256, sheet_name, index)
        for index in source_row_numbers
    }
    if len(source_ids) != len(source_row_numbers):
        raise WorkbookGenerationError("Verifica completezza: ID sorgente duplicati")

    excluded_sites = {key[:2] for key in excluded_keys}
    retained_sites = {key[:2] for key in included_keys}
    registered_sites = excluded_sites | retained_sites
    fully_excluded_sites = excluded_sites - retained_sites
    matched_exclusion_keys = set()
    fallback_rows = []
    partial_year_rows = []
    residual_excluded_title_count = 0
    residual_excluded_title_examples = []
    prepared = []
    excluded_records = []
    excluded_count = 0
    excluded_by_assignment_count = 0
    excluded_by_assignment_examples = []
    excluded_by_missing_year_count = 0
    workload_matches = 0
    workload_unmatched = 0
    workload_not_available = 0
    workload_total = 0.0
    workload_errors = []
    workload_error_count = 0
    workload_conflicts = {}
    workload_missing_warnings = []
    workload_missing_count = 0
    workload_capped_count = 0
    workload_capped_examples = []
    workload_by_rule = [0] * len(effective_rules)
    unresolved_annuality_rows = 0
    unresolved_annuality_examples = []
    missing_activity_code_rows = 0
    missing_activity_code_examples = []
    taf_rows_with_value = 0
    taf_rows_without_value = 0
    mutuazione_true_count = 0
    mutuazione_false_count = 0
    mutuazione_other_count = 0
    mutuazione_blank_count = 0
    for excel_row, row in enumerate(rows[header_row:], start=header_row + 1):
        if not _source_row_has_content(row):
            continue
        def get(key):
            index = assigned.get(key)
            return row[index] if index is not None and index < len(row) else ""
        data = {
            header: get(OFFER_HEADER_TO_FIELD[header.upper()])
            for header in HISTORIC_HEADERS
            if header.upper() in OFFER_HEADER_TO_FIELD
        }
        # Calamine returns Excel TRUE/FALSE cells as Python bool. A generic
        # display helper intentionally treated booleans as empty, causing
        # MUTUAZIONE to disappear from all five workbooks. Convert only this
        # confirmed yes/no field, keeping the original truth value explicit.
        # Both export and reimport review use this same normalized snapshot.
        raw_mutuazione = data.get("MUTUAZIONE")
        if isinstance(raw_mutuazione, bool):
            data["MUTUAZIONE"] = "VERO" if raw_mutuazione else "FALSO"
        normalized_mutuazione = _display(data.get("MUTUAZIONE"))
        mutuazione_value = normalized_mutuazione.casefold()
        if mutuazione_value in ("vero", "true"):
            mutuazione_true_count += 1
        elif mutuazione_value in ("falso", "false"):
            mutuazione_false_count += 1
        elif not normalized_mutuazione:
            mutuazione_blank_count += 1
        else:
            # Preserve unexpected raw text instead of silently assuming a
            # truth value. The summary flags it for verification.
            mutuazione_other_count += 1
        data.setdefault("Ins. Erogante", get("insegnamento_erogante"))
        # Do not attribute or filter by department. Only previously recorded
        # CdS annuality exclusions may suppress matching rows.
        course = _display(get("cds_codice"))
        campus = _display(get("sede"))
        title = _display(get("cds_nome"))
        year_text = _display(get("anno_corso"))
        site = _normalized_course_site(course, campus)
        years = _source_years(year_text)
        matched_by_name = False

        # A source-row course code sometimes differs from the saved cohort
        # register. Reconcile by FULL course name and campus only when the
        # saved register identifies exactly one course and the source uses
        # exactly one code for that same course name/site. Never guess.
        title_key = (_canonical(title), _canonical(campus))
        if (cohort_names and site not in registered_sites and title_key[0]
                and len(recorded_sites_by_title.get(title_key, set())) == 1
                and len(source_sites_by_title.get(title_key, set())) == 1):
            site = next(iter(recorded_sites_by_title[title_key]))
            matched_by_name = True
            if len(fallback_rows) < 30:
                fallback_rows.append(excel_row)

        if site in fully_excluded_sites:
            # Entire registered CdS + campus is excluded, even if its raw
            # ANNO column says "1,2,3" or is absent. This does NOT exclude
            # any other CdS or a campus with retained annualities.
            excluded_count += 1
            if years is None:
                excluded_by_missing_year_count += 1
            matching = sorted(item[2] for item in excluded_keys if item[:2] == site)
            matched_exclusion_keys.update(
                item for item in excluded_keys if item[:2] == site
            )
            excluded_records.append((
                excel_row, data,
                "Tutte le annualità registrate del CdS e della sede risultano escluse",
                "Denominazione univoca CdS e sede" if matched_by_name else "Codice CdS e sede",
                ", ".join(str(year) for year in matching),
            ))
            continue

        if site is not None and years is not None:
            excluded_in_row = {
                (site[0], site[1], year) for year in years
                if (site[0], site[1], year) in excluded_keys
            }
            matched_exclusion_keys.update(excluded_in_row)
            if excluded_in_row and len(excluded_in_row) == len(years):
                # Every explicitly enumerated year of this row is excluded.
                excluded_count += 1
                excluded_records.append((
                    excel_row, data,
                    "Tutti gli anni di corso presenti nella riga risultano esclusi",
                    "Denominazione univoca CdS e sede" if matched_by_name else "Codice CdS, sede e anno",
                    ", ".join(str(year) for year in sorted(years)),
                ))
                continue
            if excluded_in_row and len(partial_year_rows) < 30:
                # A single historic row covers included AND excluded years:
                # must not delete it or silently rewrite "1,2,3" into "2,3".
                partial_year_rows.append(excel_row)
        elif excluded_keys:
            unresolved_annuality_rows += 1
            if len(unresolved_annuality_examples) < 30:
                unresolved_annuality_examples.append(excel_row)
        # Apply the assignment-title selection only after the existing
        # CdS/annuality rules, so an already excluded row is counted once.
        if matches_workbook_exclusion_filters(
            effective_assignment_exclusions, get
        ):
            excluded_count += 1
            excluded_by_assignment_count += 1
            selected_title = _display(get("titolo_affidamento"))
            selected_facets = [
                ("Tipologia CdS", "tipologie"),
                ("CdS", "cds"),
                ("Sede", "sedi"),
                ("Annualità", "annualita"),
                ("TAF", "taf"),
            ]
            matched_description = "Titolo affidamento: " + selected_title
            for label, facet in selected_facets:
                chosen = effective_assignment_exclusions.get(facet) or []
                if chosen:
                    matched_description += "; " + label + ": " + ", ".join(chosen[:5])
            excluded_records.append((
                excel_row, data,
                "Esclusione per titolo affidamento e filtri aggiuntivi",
                matched_description[:1000],
                _display(get("anno_corso"))[:120],
            ))
            if len(excluded_by_assignment_examples) < 50:
                excluded_by_assignment_examples.append({
                    "excel_row": excel_row,
                    "assignment_title": selected_title[:200],
                    "course": _display(get("cds_nome"))[:200],
                    "course_code": _display(get("cds_codice"))[:80],
                    "campus": _display(get("sede"))[:100],
                })
            continue

        # The year of reference is the imported report's archived year, not
        # a per-row equality check; keep the original A.A. value unchanged,
        # including conventions used by Schools of Specialization.
        # Start every retained line at zero, irrespective of any old mapping
        # or old effective-hour values. The future workload rule engine will
        # populate this field from TOT ORE PREVISTE; the source is unchanged.
        # Excluded rows above retain their source values in the internal audit.
        planned_hours = get("ore_previste")
        cap_applied = workload_cap_applied(
            planned_hours, get("cds_tipologia"), course,
            data.get("TAF", ""), effective_rules,
        )
        effective, matched_index, rule_issue = apply_workload(
            planned_hours, get("cds_tipologia"), course,
            data.get("TAF", ""), effective_rules,
        )
        if cap_applied:
            workload_capped_count += 1
            if len(workload_capped_examples) < 100:
                workload_capped_examples.append({
                    "excel_row": excel_row,
                    "rule_number": matched_index + 1 if matched_index is not None else None,
                    "planned_hours": _display(planned_hours),
                    "effective_hours": _display(effective),
                })
        data["TOT ORE EFFETTIVE"] = effective
        if matched_index is None and rule_issue is None:
            # No matching rule: carry the explicitly mapped planned hours,
            # never the obsolete historic effective-hour value.
            workload_unmatched += 1
            workload_total += effective
        elif rule_issue and is_missing_planned_hours(planned_hours):
            # A documented exception, not an inferred number. Empty planned
            # hours always yield ZERO even when a fixed-hours rule matches.
            workload_missing_count += 1
            if len(workload_missing_warnings) < 100:
                workload_missing_warnings.append({
                    "excel_row": excel_row,
                    "reason": rule_issue,
                    "rule_number": matched_index + 1 if matched_index is not None else None,
                })
        elif rule_issue:
            workload_error_count += 1
            conflicting_rules = (
                matching_rule_indices(
                    get("cds_tipologia"), course, data.get("TAF", ""), effective_rules
                ) if rule_issue.startswith("Conflitto tra regole ") else []
            )
            if len(conflicting_rules) > 1:
                for pair in combinations(conflicting_rules, 2):
                    bucket = workload_conflicts.setdefault(
                        pair, {"rows": 0, "examples": []}
                    )
                    bucket["rows"] += 1
                    if len(bucket["examples"]) < 12:
                        bucket["examples"].append(excel_row)
            if len(workload_errors) < 100:
                workload_errors.append({
                    "excel_row": excel_row,
                    "reason": rule_issue,
                    "rule_number": (matched_index + 1 if matched_index is not None else None),
                    "conflicting_rules": conflicting_rules,
                    "source_value": _display(planned_hours)[:75],
                })
        else:
            workload_matches += 1
            workload_by_rule[matched_index] += 1
            if effective == "N.D.":
                workload_not_available += 1
            else:
                workload_total += effective
        historical_id = source_row_id(source_sha256, sheet_name, excel_row)
        if _display(data.get("TAF")):
            taf_rows_with_value += 1
        else:
            taf_rows_without_value += 1
        if not (_display(data.get("CODICE INS")) or _display(data.get("CODICE UGOV"))):
            missing_activity_code_rows += 1
            if len(missing_activity_code_examples) < 30:
                missing_activity_code_examples.append(excel_row)
        title_site = (_canonical(title), _canonical(campus))
        if (title_site in excluded_title_sites
                and title_site not in included_title_sites):
            # A title still occurs despite all cohorts of that title/site
            # being excluded. Do not infer a match; alert the operator.
            residual_excluded_title_count += 1
            if len(residual_excluded_title_examples) < 20:
                residual_excluded_title_examples.append({
                    "excel_row": excel_row,
                    "course_name": title[:140],
                    "source_code": course[:40],
                    "campus": campus[:80],
                })
        prepared.append((data, historical_id, _activity_id(data, historical_id)))
    if not prepared and not allow_empty:
        raise WorkbookGenerationError("Nessuna riga storica esportabile")

    # Cross-check EACH nonempty source line against the partition retained /
    # excluded. This detects silent omissions caused by future filter changes.
    kept_ids = [record[1] for record in prepared]
    excluded_ids = [
        source_row_id(source_sha256, sheet_name, excel_row)
        for excel_row, *_ in excluded_records
    ]
    kept_set, excluded_set = set(kept_ids), set(excluded_ids)
    missing_ids = source_ids - kept_set - excluded_set
    extraneous_ids = (kept_set | excluded_set) - source_ids
    if (len(kept_set) != len(kept_ids)
            or len(excluded_set) != len(excluded_ids)
            or kept_set & excluded_set or missing_ids or extraneous_ids
            or len(kept_ids) + len(excluded_ids) != len(source_row_numbers)):
        raise WorkbookGenerationError(
            "Verifica completezza fallita: alcune righe del report non sono "
            "riconciliate univocamente tra cinque Excel e registro delle esclusioni. "
            f"Righe sorgente: {len(source_row_numbers)}; "
            f"incluse: {len(kept_ids)}; escluse: {len(excluded_ids)}; "
            f"non riconciliate: {len(missing_ids)}. "
            "Generazione bloccata per prevenire omissioni o duplicazioni."
        )
    reconciliation = {
        "verified": True,
        "source_nonempty_rows": len(source_row_numbers),
        "included_in_each_workbook": len(kept_ids),
        "excluded_in_internal_register": len(excluded_ids),
        "excluded_by_assignment_filters": excluded_by_assignment_count,
        "assignment_exclusion_examples": excluded_by_assignment_examples,
        "missing_from_outputs": 0,
        "duplicate_ids": 0,
    }
    workload_stats = {
        "rules": len(effective_rules),
        "rows_calculated": workload_matches,
        "rows_without_rule": workload_unmatched,
        "rows_using_planned_hours": workload_unmatched,
        "rows_not_available": workload_not_available,
        "total_effective_hours": round(workload_total, 2),
        "per_rule_rows": workload_by_rule,
        "rows_with_missing_planned_hours": workload_missing_count,
        "missing_planned_hours_examples": workload_missing_warnings,
        "rows_capped_to_planned_hours": workload_capped_count,
        "capped_to_planned_hours_examples": workload_capped_examples,
        "error_count": workload_error_count,
        "errors": workload_errors,
        "conflict_pairs": [
            {
                "rules": list(pair),
                "rows": bucket["rows"],
                "examples": bucket["examples"],
            }
            for pair, bucket in sorted(
                workload_conflicts.items(),
                key=lambda item: (-item[1]["rows"], item[0]),
            )
        ],
        "blocked": workload_error_count > 0,
    }
    if strict_workload and workload_error_count:
        first = workload_errors[0]
        raise WorkbookGenerationError(
            f"Calcolo carico non valido: {workload_error_count} errori effettivi "
            f"(riga {first['excel_row']}: {first['reason']}). "
            "Le celle vuote sono segnalate a parte e rimangono a 0; "
            "verificare le righe non numeriche, negative o con regole conflittuali nell'anteprima."
        )
    return (
        prepared, excluded_count, unresolved_annuality_rows,
        unresolved_annuality_examples,
        missing_activity_code_rows, missing_activity_code_examples,
        excluded_by_missing_year_count,
        len(excluded_keys - matched_exclusion_keys),
        [
            {"course_code": course, "campus": campus, "study_year": year}
            for course, campus, year in sorted(excluded_keys - matched_exclusion_keys)[:25]
        ],
        len(fallback_rows), fallback_rows,
        len(partial_year_rows), partial_year_rows,
        residual_excluded_title_count, residual_excluded_title_examples,
        taf_mapping_mode, taf_rows_with_value, taf_rows_without_value,
        mutuazione_mapping_mode, mutuazione_true_count,
        mutuazione_false_count, mutuazione_other_count, mutuazione_blank_count,
        excluded_records, reconciliation, workload_stats,
    )


def build_five_workbooks(
    source: Path, source_sha256: str, sheet_name: str, header_row: int,
    assigned: dict[str, int], history_year: str,
    excluded: set[tuple[str, str, int]] | None = None,
    included: set[tuple[str, str, int]] | None = None,
    cohort_names: dict[tuple[str, str, int], str] | None = None,
    workload_rules: list[dict] | None = None,
    assignment_exclusions: dict[str, list[str]] | None = None,
) -> tuple[bytes, dict]:
    """ZIP with five byte-identical referent XLSX and one internal excluded-row audit."""
    proposal_year = next_academic_year(history_year)
    (prepared, excluded_count, unresolved_count, unresolved_examples,
     missing_code_count, missing_code_examples, excluded_ambiguous_count,
     unmatched_exclusions_count, unmatched_exclusion_examples,
     fallback_count, fallback_examples, partial_count, partial_examples,
     residual_count, residual_examples,
     taf_mapping_mode, taf_rows_with_value, taf_rows_without_value,
     mutuazione_mapping_mode, mutuazione_true_count,
     mutuazione_false_count, mutuazione_other_count, mutuazione_blank_count,
     excluded_records, reconciliation, workload_stats) = _prepare(
        source, source_sha256, sheet_name, header_row, assigned,
        history_year, excluded or set(), included, cohort_names, workload_rules,
        assignment_exclusions=assignment_exclusions,
    )
    output = io.BytesIO()
    workbook = xlsxwriter.Workbook(output, {"in_memory": True})
    workbook.set_properties({"title": "DidaUP - Proposte didattiche",
                             "comments": "Bozza istruttoria - non approvata"})
    sheet = workbook.add_worksheet("Proposte SSD")
    title = workbook.add_format({
        "bold": True, "font_color": "#FFFFFF", "bg_color": "#123F66",
        "font_size": 14, "valign": "vcenter",
    })
    subtitle = workbook.add_format({
        "font_color": "#274561", "bg_color": "#E8F1F8",
        "text_wrap": True, "valign": "vcenter",
    })
    header_fmt = workbook.add_format({
        "bold": True, "font_color": "#FFFFFF", "bg_color": "#275C7D",
        "text_wrap": True, "border": 1, "border_color": "#D2DDE6",
        "valign": "vcenter",
    })
    locked = workbook.add_format({
        "locked": True, "font_color": "#22364D", "bg_color": "#F3F6F8",
    })
    edit = workbook.add_format({
        "locked": False, "font_color": "#222222", "bg_color": "#FFF0BF",
    })
    hidden = workbook.add_format({"locked": True, "font_color": "#555555"})
    sheet.set_tab_color("#275C7D")
    sheet.hide_gridlines(2)
    sheet.set_zoom(85)
    sheet.set_row(0, 27)
    sheet.set_row(1, 33)
    sheet.set_row(2, 28)
    sheet.set_row(3, 27)
    sheet.set_row(4, 22)
    sheet.merge_range(0, 0, 0, 36, f"DidaUP | PROPOSTE DIDATTICHE {proposal_year}", title)
    sheet.merge_range(
        1, 0, 1, 36,
        f"STORICO {history_year} (in sola lettura)   |   "
        f"PROPOSTE {proposal_year} (quattro colonne gialle). "
        "Documento di lavoro, non costituisce approvazione.",
        subtitle,
    )
    sheet.merge_range(
        2, 0, 2, 36,
        "Tutte le attività didattiche; nessun filtro per dipartimento. "
        "Usare le Visualizzazioni foglio di Excel online per filtri personali.",
        subtitle,
    )
    sheet.merge_range(
        3, 0, 3, 36,
        "La colonna Ore è una QUOTA CEDUTA dal docente storico per le aggiunte/"
        "sostituzioni parziali. TOT ORE EFFETTIVE usa TOT ORE PREVISTE "
        "salvo regole esplicite di calcolo o N.D. (non disponibile).",
        subtitle,
    )
    sheet.merge_range(
        4, 0, 4, 36,
        "Per più destinazioni dalla stessa copertura serve «Aggiungi variazione» "
        "da Office Scripts, da associare e collaudare nel tenant d'Ateneo. "
        "Il file esportato NON contiene ancora un pulsante eseguibile.",
        subtitle,
    )
    for j, name in enumerate(ALL_HEADERS):
        sheet.write_string(5, j, name, header_fmt)
    sheet.set_row(5, 52)
    sheet.set_column(0, 0, 17)
    sheet.set_column(1, 2, 21)
    sheet.set_column(3, 8, 16)
    sheet.set_column(9, 14, 20)
    sheet.set_column(15, 28, 19)
    sheet.set_column(29, 32, 23)
    sheet.set_column(33, 36, 20)
    # Hide only the requested historical columns, preserving their source
    # values and their original positions so reimport IDs remain stable.
    for header in HIDDEN_REFERENT_HEADERS:
        col = VISIBLE_HEADERS.index(header)
        sheet.set_column(col, col, 18, locked, {"hidden": True})
    sheet.set_column(37, 40, 18, hidden, {"hidden": True})
    for excel_index, (data, historical_id, activity_id) in enumerate(prepared, start=6):
        sheet.set_row(excel_index, 20)
        for col, header in enumerate(VISIBLE_HEADERS):
            if PROPOSAL_START <= col <= PROPOSAL_END:
                sheet.write_blank(excel_index, col, None, edit)
            else:
                _write_safe(sheet, excel_index, col, data.get(header, ""), locked)
        for col, value in enumerate(
            ("STORICO", historical_id, historical_id, activity_id),
            start=37,
        ):
            sheet.write_string(excel_index, col, value, hidden)
    sheet.autofilter(5, 0, 5 + len(prepared), 36)
    sheet.freeze_panes(6, 3)
    # Data validation does not guess the not-yet-approved enum of change types.
    sheet.data_validation(
        6, 31, 5 + len(prepared), 31,
        {"validate": "decimal", "criteria": ">=", "value": 0,
         "input_title": "Ore cedute", "input_message": "Non superiori alle ore disponibili"},
    )
    sheet.protect("", {
        "autofilter": True, "select_locked_cells": True,
        "select_unlocked_cells": True,
        "insert_rows": False, "delete_rows": False,
        "format_cells": False, "sort": False,
    })
    workbook.close()
    template = output.getvalue()
    # Independently reopen the physical referent XLSX to verify that ALL
    # retained source rows have actually been written, once each.
    _verify_xlsx_ids(
        template, "Proposte SSD", 6, ALL_HEADERS.index("DIDAUP_ID_ORIGINE"),
        [record[1] for record in prepared], "Excel per i referenti",
    )
    if excluded_count != len(excluded_records):
        raise WorkbookGenerationError("Conteggio delle esclusioni incoerente")
    if {
        source_row_id(source_sha256, sheet_name, row_index)
        for row_index, *_ in excluded_records
    } & {row[1] for row in prepared}:
        raise WorkbookGenerationError("Una riga compare tra incluse ed escluse")
    # The sixth file is an internal audit, never part of the five files to
    # share with referents. Historical columns are readable and unchanged;
    # there are no proposal/edit columns.
    excluded_output = io.BytesIO()
    excluded_wb = xlsxwriter.Workbook(excluded_output, {"in_memory": True})
    excluded_wb.set_properties({
        "title": "DidaUP - Righe storiche escluse",
        "comments": "Riepilogo interno non destinato ai referenti",
    })
    excluded_sheet = excluded_wb.add_worksheet("Righe escluse")
    excluded_title = excluded_wb.add_format({
        "bold": True, "font_color": "#FFFFFF", "bg_color": "#733D3D",
        "font_size": 14, "valign": "vcenter",
    })
    excluded_info = excluded_wb.add_format({
        "font_color": "#51322F", "bg_color": "#F8EAE7", "text_wrap": True,
    })
    excluded_header = excluded_wb.add_format({
        "bold": True, "font_color": "#FFFFFF", "bg_color": "#8B5147",
        "text_wrap": True, "valign": "vcenter",
    })
    excluded_cell = excluded_wb.add_format({"locked": True})
    audit_headers = (
        "RIGA NEL REPORT", "CRITERIO DI ESCLUSIONE",
        "TIPO DI CORRISPONDENZA", "ANNUALITÀ ESCLUSE",
        "ID RIGA STORICA",
    )
    headers = HISTORIC_HEADERS + list(audit_headers)
    last_col = len(headers) - 1
    excluded_sheet.merge_range(
        0, 0, 0, last_col,
        f"DidaUP | RIGHE ESCLUSE DALLA GENERAZIONE {proposal_year}",
        excluded_title,
    )
    excluded_sheet.merge_range(
        1, 0, 1, last_col,
        f"Registro interno | Storico {history_year} | "
        f"{excluded_count} righe eliminate dai cinque file per i referenti. "
        "Non distribuire questo file ai referenti.",
        excluded_info,
    )
    excluded_sheet.merge_range(
        2, 0, 2, last_col,
        "Sono riportate soltanto le righe effettivamente escluse; "
        "le righe con annualità dubbia e conservate nei cinque Excel non compaiono qui.",
        excluded_info,
    )
    excluded_sheet.merge_range(
        3, 0, 3, last_col,
        f"CONTROLLO COMPLETEZZA: {reconciliation['source_nonempty_rows']} righe "
        f"del report = {reconciliation['included_in_each_workbook']} presenti in "
        "ciascuno dei cinque Excel + "
        f"{reconciliation['excluded_in_internal_register']} escluse. "
        "Nessuna riga mancante o duplicata.",
        excluded_info,
    )
    for col, header in enumerate(headers):
        excluded_sheet.write_string(4, col, header, excluded_header)
    excluded_sheet.set_row(0, 28)
    excluded_sheet.set_row(1, 36)
    excluded_sheet.set_row(2, 33)
    excluded_sheet.set_row(3, 33)
    excluded_sheet.set_row(4, 44)
    excluded_sheet.set_column(0, len(HISTORIC_HEADERS) - 1, 19)
    excluded_sheet.set_column(len(HISTORIC_HEADERS), len(HISTORIC_HEADERS), 15)
    excluded_sheet.set_column(len(HISTORIC_HEADERS)+1, len(HISTORIC_HEADERS)+1, 58)
    excluded_sheet.set_column(len(HISTORIC_HEADERS)+2, len(HISTORIC_HEADERS)+2, 34)
    excluded_sheet.set_column(len(HISTORIC_HEADERS)+3, len(HISTORIC_HEADERS)+3, 20)
    excluded_sheet.set_column(len(HISTORIC_HEADERS)+4, len(HISTORIC_HEADERS)+4, 43)
    excluded_sheet.hide_gridlines(2)
    excluded_sheet.set_zoom(85)
    excluded_sheet.set_tab_color("#8B5147")
    for row_index, (source_row, data, reason, match_type, years_label) in enumerate(
        excluded_records, start=5
    ):
        for col, header in enumerate(HISTORIC_HEADERS):
            _write_safe(excluded_sheet, row_index, col, data.get(header, ""), excluded_cell)
        audit = (
            source_row, reason, match_type, years_label,
            source_row_id(source_sha256, sheet_name, source_row),
        )
        for col, value in enumerate(audit, start=len(HISTORIC_HEADERS)):
            _write_safe(excluded_sheet, row_index, col, value, excluded_cell)
    excluded_sheet.autofilter(4, 0, 4 + len(excluded_records), last_col)
    excluded_sheet.freeze_panes(5, 3)
    excluded_sheet.protect("", {"autofilter": True, "select_locked_cells": True})
    excluded_wb.close()
    excluded_template = excluded_output.getvalue()
    _verify_xlsx_ids(
        excluded_template, "Righe escluse", 5, len(HISTORIC_HEADERS) + 4,
        [
            source_row_id(source_sha256, sheet_name, excel_row)
            for excel_row, *_ in excluded_records
        ],
        "registro interno delle esclusioni",
    )
    reconciliation["exported_workbooks_checked"] = NUM_COPIES
    reconciliation["internal_register_checked"] = True
    # Every generation gets a visibly different filename. Existing OneDrive
    # copies do not update when DidaUP regenerates the archive: the operator
    # must not mistake an earlier export for the latest one.
    export_revision = (
        datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        + "-" + secrets.token_hex(3)
    )
    # Five byte-identical XLSX contents; only ZIP member names differ.
    packed = io.BytesIO()
    with ZipFile(packed, "w", compression=ZIP_DEFLATED, compresslevel=6) as archive:
        for index in range(1, NUM_COPIES + 1):
            archive.writestr(
                f"DidaUP_Proposte_{proposal_year.replace('/', '-')}_"
                f"rev-{export_revision}_Dipartimento_{index:02d}.xlsx",
                template,
            )
        archive.writestr(
            f"DidaUP_Righe_escluse_{proposal_year.replace('/', '-')}_"
            f"rev-{export_revision}_CONTROLLO_INTERNO.xlsx",
            excluded_template,
        )
    return packed.getvalue(), {
        "export_revision": export_revision,
        "copies": NUM_COPIES, "archive_files": NUM_COPIES + 1,
        "excluded_file_rows": len(excluded_records),
        "workload": workload_stats,
        "reconciliation": reconciliation,
        "excluded_audit_sha256": hashlib.sha256(excluded_template).hexdigest(),
        "historical_rows": len(prepared),
        "excluded_rows": excluded_count,
        "excluded_by_assignment_filters": reconciliation["excluded_by_assignment_filters"],
        "assignment_exclusion_examples": reconciliation["assignment_exclusion_examples"],
        "excluded_rows_with_missing_year": excluded_ambiguous_count,
        "unmatched_exclusion_count": unmatched_exclusions_count,
        "unmatched_exclusion_examples": unmatched_exclusion_examples,
        "cohorts_matched_by_unique_name_rows": fallback_count,
        "cohorts_matched_by_unique_name_examples": fallback_examples,
        "mixed_annuality_rows_retained": partial_count,
        "mixed_annuality_example_rows": partial_examples,
        "excluded_course_titles_still_present": residual_count,
        "excluded_course_title_examples": residual_examples,
        "taf_mapping_mode": taf_mapping_mode,
        "taf_rows_with_value": taf_rows_with_value,
        "taf_rows_without_value": taf_rows_without_value,
        "mutuazione_mapping_mode": mutuazione_mapping_mode,
        "mutuazione_true_rows": mutuazione_true_count,
        "mutuazione_false_rows": mutuazione_false_count,
        "mutuazione_other_rows": mutuazione_other_count,
        "mutuazione_empty_rows": mutuazione_blank_count,
        "unresolved_annuality_rows_included": unresolved_count,
        "unresolved_annuality_example_rows": unresolved_examples,
        "missing_activity_codes_rows_included": missing_code_count,
        "missing_activity_codes_example_rows": missing_code_examples,
        "source_sha256": source_sha256,
        "template_sha256": hashlib.sha256(template).hexdigest(),
        "historical_year": history_year, "proposal_year": proposal_year,
        "department_filter": False,
        "warning": "File per collaudo: nessun pulsante Office Scripts incorporato",
    }
