"""Spreadsheet-source column mapping: bounded previews and explicit schema selection.

A mapping is only a draft: data are NOT normalized or validated as teaching
assignments until a later administrative review.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from python_calamine import CalamineWorkbook

MAX_PREVIEW_COLUMNS = 250
MAX_PREVIEW_ROW = 40
MAX_PREVIEW_ROWS = 5

OFFER_FIELDS: list[tuple[str, str]] = [
    ("cds_codice", "CdS · codice"),
    ("cds_nome", "CdS · denominazione"),
    ("cds_tipologia", "CdS · tipologia"),
    ("sede", "Sede didattica"),
    ("anno_corso", "Anno di corso del CdS"),
    ("dipartimento", "Dipartimento"),
    ("codice_insegnamento", "Codice insegnamento"),
    ("insegnamento", "Denominazione insegnamento"),
    ("codice_modulo", "Codice modulo o partizione"),
    ("modulo", "Denominazione modulo"),
    ("ssd_insegnamento_vecchio", "SSD insegnamento · precedente codifica"),
    ("ssd_insegnamento_nuovo", "SSD insegnamento · nuova codifica"),
    ("id_copertura", "Identificativo della copertura storica"),
    ("docente_identificativo", "Identificativo del docente storico"),
    ("docente_nome", "Docente storico · nominativo"),
    ("ssd_docente_vecchio", "SSD docente · precedente codifica"),
    ("ssd_docente_nuovo", "SSD docente · nuova codifica"),
    ("ore_copertura", "Ore assegnate nella copertura storica"),
    ("ore_previste", "Ore previste dall'attività"),
    ("cfu", "CFU"),
    ("stato_copertura", "Stato della copertura"),
]

TEACHER_FIELDS: list[tuple[str, str]] = [
    ("docente_identificativo", "Identificativo docente"),
    ("docente_cognome", "Cognome docente"),
    ("docente_nome", "Nome / nominativo docente"),
    ("ssd_docente_vecchio", "SSD docente · precedente codifica"),
    ("ssd_docente_nuovo", "SSD docente · nuova codifica"),
    ("dipartimento_docente", "Dipartimento di afferenza"),
    ("qualifica", "Qualifica / ruolo"),
    ("ore_carico", "Ore di carico (se presenti)"),
    ("stato_docente", "Stato del rapporto (se presente)"),
]


def fields_for(kind: str) -> list[dict]:
    fields = OFFER_FIELDS if kind == "offerta" else TEACHER_FIELDS if kind == "docenti" else []
    return [{"key": key, "label": label} for key, label in fields]


def preview(path: Path, sheet_name: str, header_row: int) -> dict[str, Any]:
    if not 1 <= header_row <= MAX_PREVIEW_ROW:
        raise ValueError("Riga delle intestazioni non ammessa (1-40)")
    workbook = CalamineWorkbook.from_path(path)
    if sheet_name not in workbook.sheet_names:
        raise ValueError("Foglio non presente nel report")
    sheet = workbook.get_sheet_by_name(sheet_name)
    if sheet.width <= 0 or sheet.width > MAX_PREVIEW_COLUMNS:
        raise ValueError("Numero di colonne non supportato: massimo 250")
    if sheet.height < header_row:
        raise ValueError("La riga delle intestazioni supera la lunghezza del foglio")
    # Only inspect a bounded area. Never expose entire raw data tables in API.
    rows = sheet.to_python(skip_empty_area=False, nrows=header_row + MAX_PREVIEW_ROWS)
    header = rows[header_row - 1] if len(rows) >= header_row else []

    def display(value: Any, max_length: int = 100) -> str:
        if value is None:
            return ""
        # Defang spreadsheet-formula-looking text in previews (DOM uses textContent).
        return str(value).strip()[:max_length]

    columns = [
        {"index": index, "label": display(header[index] if index < len(header) else None)}
        for index in range(sheet.width)
    ]
    sample = []
    for row in rows[header_row : header_row + MAX_PREVIEW_ROWS]:
        sample.append([display(row[i] if i < len(row) else None, 70) for i in range(sheet.width)])
    return {
        "sheet": sheet_name,
        "header_row": header_row,
        "row_count": sheet.height,
        "column_count": sheet.width,
        "columns": columns,
        "sample": sample,
        "notice": "Anteprima riservata: non condividere dati reali in screenshot, issue o repository",
    }


def evaluate_mapping(kind: str, assigned: dict[str, int]) -> list[str]:
    """Provide warnings; do not silently claim a draft mapping is approved."""
    missing: list[str] = []
    if kind == "offerta":
        if not (assigned.get("cds_codice") is not None or assigned.get("cds_nome") is not None):
            missing.append("Identificazione CdS (codice o denominazione)")
        if not (assigned.get("insegnamento") is not None or assigned.get("modulo") is not None):
            missing.append("Denominazione dell'insegnamento o del modulo")
        if not (assigned.get("ssd_insegnamento_vecchio") is not None
                or assigned.get("ssd_insegnamento_nuovo") is not None):
            missing.append("SSD dell'insegnamento (vecchio o nuovo)")
        if "id_copertura" not in assigned:
            missing.append("ID copertura storica: da verificare prima della riconciliazione")
    elif kind == "docenti":
        if not any(key in assigned for key in (
            "docente_identificativo", "docente_cognome", "docente_nome"
        )):
            missing.append("Identificazione del docente")
        if not any(key in assigned for key in ("ssd_docente_vecchio", "ssd_docente_nuovo")):
            missing.append("SSD del docente")
    return missing
