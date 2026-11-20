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
import re
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from python_calamine import CalamineWorkbook
import xlsxwriter

from .column_mapping import OFFER_HEADER_TO_FIELD, source_header_conflicts
from .row_identity import source_row_id

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


def _activity_id(data: dict[str, object]) -> str:
    # Internal grouping key, NOT an official activity identifier.
    fields = [
        "CODICE CORSO", "SEDE CORSO", "ANNO", "CODICE INS",
        "CODICE UGOV", "DISCRIMINANTE DI OI", "MODULO", "UL",
        "DISCRIMINANTE MODULO", "SSD INSEGNAMENTO",
    ]
    payload = [_display(data.get(key)) for key in fields]
    if not (_display(data.get("CODICE INS")) or _display(data.get("CODICE UGOV"))):
        raise WorkbookGenerationError(
            "Codice insegnamento e codice UGOV entrambi assenti: "
            "impossibile collegare con sicurezza le proposte"
        )
    return "ACT-" + hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode()
    ).hexdigest()[:32]


def _prepare(source: Path, source_sha256: str, sheet_name: str, header_row: int,
             assigned: dict[str, int], history_year: str,
             excluded: set[tuple[str, str, int]]):
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
    required = (
        "cds_codice", "sede", "anno_corso", "codice_insegnamento",
        "ore_effettive_totali",
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
    prepared = []
    excluded_count = 0
    unresolved_annuality_rows = 0
    unresolved_annuality_examples = []
    for excel_row, row in enumerate(rows[header_row:], start=header_row + 1):
        if not any(_display(x) for x in row):
            continue
        def get(key):
            index = assigned.get(key)
            return row[index] if index is not None and index < len(row) else ""
        data = {
            header: get(OFFER_HEADER_TO_FIELD[header.upper()])
            for header in HISTORIC_HEADERS
            if header.upper() in OFFER_HEADER_TO_FIELD
        }
        data.setdefault("Ins. Erogante", get("insegnamento_erogante"))
        # Do not attribute or filter by department. Only previously recorded
        # CdS annuality exclusions may suppress matching rows.
        course = _display(get("cds_codice"))
        campus = _display(get("sede"))
        year_text = _display(get("anno_corso"))
        year_int = int(year_text) if re.fullmatch(r"(?:[1-9]|1[0-2])", year_text) else None
        if excluded and (not course or not campus or year_int is None):
            # An incomplete historical row is NOT evidence that it belongs to
            # an excluded cohort. Keep it in all five files and report it.
            unresolved_annuality_rows += 1
            if len(unresolved_annuality_examples) < 30:
                unresolved_annuality_examples.append(excel_row)
        if course and campus and year_int is not None and (
            course, campus, year_int
        ) in excluded:
            excluded_count += 1
            continue
        # The year of reference is the imported report's archived year, not
        # a per-row equality check. Keep the original A.A. value unchanged,
        # including conventions used by Schools of Specialization.
        effective = get("ore_effettive_totali")
        if _display(effective) and (
            isinstance(effective, bool) or
            not isinstance(effective, (float, int)) or
            not math.isfinite(float(effective)) or effective < 0
        ):
            raise WorkbookGenerationError(
                f"Riga {excel_row}: TOT ORE EFFETTIVE non numerico o negativo"
            )
        historical_id = source_row_id(source_sha256, sheet_name, excel_row)
        prepared.append((data, historical_id, _activity_id(data)))
    if not prepared:
        raise WorkbookGenerationError("Nessuna riga storica esportabile")
    return prepared, excluded_count, unresolved_annuality_rows, unresolved_annuality_examples


def build_five_workbooks(
    source: Path, source_sha256: str, sheet_name: str, header_row: int,
    assigned: dict[str, int], history_year: str,
    excluded: set[tuple[str, str, int]] | None = None,
) -> tuple[bytes, dict]:
    """ZIP of exactly five byte-identical XLSX, no department-specific filters."""
    proposal_year = next_academic_year(history_year)
    prepared, excluded_count, unresolved_count, unresolved_examples = _prepare(
        source, source_sha256, sheet_name, header_row, assigned,
        history_year, excluded or set(),
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
        "sostituzioni parziali; TOT ORE EFFETTIVE è l'unico riferimento.",
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
    # The exact same bytes are included five times. No file-level department
    # metadata is written into the XLSX; provenance is the containing ZIP name.
    packed = io.BytesIO()
    with ZipFile(packed, "w", compression=ZIP_DEFLATED, compresslevel=6) as archive:
        for index in range(1, NUM_COPIES + 1):
            archive.writestr(
                f"DidaUP_Proposte_{proposal_year.replace('/', '-')}_Dipartimento_{index:02d}.xlsx",
                template,
            )
    return packed.getvalue(), {
        "copies": NUM_COPIES, "historical_rows": len(prepared),
        "excluded_rows": excluded_count,
        "unresolved_annuality_rows_included": unresolved_count,
        "unresolved_annuality_example_rows": unresolved_examples,
        "source_sha256": source_sha256,
        "template_sha256": hashlib.sha256(template).hexdigest(),
        "historical_year": history_year, "proposal_year": proposal_year,
        "department_filter": False,
        "warning": "File per collaudo: nessun pulsante Office Scripts incorporato",
    }
