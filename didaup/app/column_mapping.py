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
    ("ssd_insegnamento_originale", "SSD insegnamento · come indicato nel report"),
    ("docente_cognome", "Cognome docente storico"),
    ("ore_prevlez", "Ore previste di lezione (OREPREVLEZ)"),
    ("ore_effettive_totali", "Totale ore effettive"),
    ("codice_ugov", "Codice UGOV"),
    ("discriminante_oi", "Discriminante OI"),
    ("discriminante_modulo", "Discriminante modulo"),
    ("ul", "Unità logistica UL"),
    ("anno_accademico_report", "Anno accademico come da report"),
    ("cfu_totali_ins", "CFU totali insegnamento"),
    ("tipo_erogazione", "Tipo erogazione"),
    ("mutuazione", "Mutuazione"),
    ("insegnamento_erogante", "Insegnamento erogante"),
    ("taf", "TAF"),
    ("fuori_piano", "Fuori piano"),
    ("moodle", "Moodle"),
    ("crediti_tirocinio", "Crediti tirocinio"),
    ("periodo_inizio", "Periodo inizio"),
    ("periodo_fine", "Periodo fine"),
    ("titolo_affidamento", "Titolo affidamento storico"),
    ("proposta_docente", "VARIAZIONE · Nuovo docente"),
    ("proposta_ore", "VARIAZIONE · Ore"),
    ("proposta_note", "VARIAZIONE · Note"),

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
                or assigned.get("ssd_insegnamento_nuovo") is not None
                or assigned.get("ssd_insegnamento_originale") is not None):
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


# Exact, user-supplied 2026/27 header labels. They define a technical
# workbook *layout*, not a specific teacher, assignment or legal rule.
# "SSD INSEGNAMENTO" has no old/new qualifier; never infer either version.
OFFER_HEADER_TO_FIELD = {
    "SEDE CORSO": "sede",
    "CODICE CORSO": "cds_codice",
    "CDS": "cds_nome",
    "ANNO ACCADEMICO": "anno_accademico_report",
    "CFU TOTALI INS": "cfu_totali_ins",
    "CODICE INS": "codice_insegnamento",
    "TIPOEROGAZIONE": "tipo_erogazione",
    "INSEGNAMENTO": "insegnamento",
    "CODICE UGOV": "codice_ugov",
    "DISCRIMINANTE DI OI": "discriminante_oi",
    "MODULO": "modulo",
    "UL": "ul",
    "DISCRIMINANTE MODULO": "discriminante_modulo",
    "ANNO": "anno_corso",
    "MUTUAZIONE": "mutuazione",
    "INS. EROGANTE": "insegnamento_erogante",
    "TAF": "taf",
    "FUORI PIANO": "fuori_piano",
    "SSD INSEGNAMENTO": "ssd_insegnamento_originale",
    "CFU": "cfu",
    "MOODLE": "moodle",
    "MATRICOLA DOCENTE": "docente_identificativo",
    "NOME DOCENTE": "docente_nome",
    "COGNOME DOCENTE": "docente_cognome",
    "OREPREVLEZ": "ore_prevlez",
    "CREDITITIR": "crediti_tirocinio",
    "CODICE SSD DOCENTE NUOVO": "ssd_docente_nuovo",
    "TOT ORE PREVISTE": "ore_previste",
    "TOT ORE EFFETTIVE": "ore_effettive_totali",
    "NUOVO DOCENTE": "proposta_docente",
    "ORE": "proposta_ore",
    "NOTE": "proposta_note",
    "PERIODO INIZIO": "periodo_inizio",
    "PERIODO FINE": "periodo_fine",
    "DIPARTIMENTO AFFERENZA DOCENTE": "dipartimento",
    "TITOLO AFFIDAMENTO": "titolo_affidamento",
}
PROPOSAL_FIELDS = ("proposta_docente", "proposta_ore", "proposta_note")


def normalize_header(value: Any) -> str:
    # Ignore capitalization, accents on common Italian words and whitespace.
    import re
    import unicodedata

    value = unicodedata.normalize("NFKD", str(value or ""))
    value = "".join(character for character in value if not unicodedata.combining(character))
    value = re.sub(r"\s+", " ", value.upper().strip())
    return value


def suggest_fields(headers: list[Any], kind: str) -> dict[str, Any]:
    # Never guess a field from partial matches, and never assign one
    # source column to multiple semantic fields.
    mapping_table = OFFER_HEADER_TO_FIELD if kind == "offerta" else {}
    locations: dict[str, list[int]] = {}
    for index, text in enumerate(headers):
        normalized = normalize_header(text)
        if normalized and normalized in mapping_table:
            locations.setdefault(mapping_table[normalized], []).append(index)
    assigned = {field: positions[0] for field, positions in locations.items() if len(positions) == 1}
    ambiguous = {
        field: positions for field, positions in locations.items()
        if len(positions) > 1
    }
    editable = {field: assigned[field] for field in PROPOSAL_FIELDS if field in assigned}
    missing_proposal = [field for field in PROPOSAL_FIELDS if field not in assigned]
    return {
        "assigned": assigned, "matched": len(assigned),
        "ambiguous": ambiguous, "proposal_columns": editable,
        "missing_proposal_fields": missing_proposal,
        "unmatched_source_columns": [
            index for index, label in enumerate(headers)
            if str(label or "").strip() and index not in assigned.values()
        ],
        "confidence": "exact_header" if assigned else "unrecognized",
    }


def autodetect_workbook(path: Path, kind: str) -> dict[str, Any]:
    """Look for the supplied Excel-for-referents layout in the first 40 rows.

    The result is a *suggestion*; never persists or validates assignments.
    """
    workbook = CalamineWorkbook.from_path(path)
    best: dict[str, Any] | None = None
    for name in workbook.sheet_names[:100]:
        sheet = workbook.get_sheet_by_name(name)
        if sheet.width > MAX_PREVIEW_COLUMNS or sheet.height < 1:
            continue
        first = sheet.to_python(skip_empty_area=False, nrows=min(MAX_PREVIEW_ROW, sheet.height))
        for index, row in enumerate(first):
            result = suggest_fields(list(row), kind)
            if best is None or result["matched"] > best["matched"]:
                best = {
                    **result, "sheet_name": name, "header_row": index + 1,
                    "column_count": sheet.width,
                }
    if best is None or best["matched"] < (8 if kind == "offerta" else 3):
        return {
            "recognized": False, "message": "Tracciato non riconosciuto con sufficiente certezza; verificare le intestazioni manualmente",
        }
    return {
        **best, "recognized": True,
        "message": "Corrispondenze proposte automaticamente dalle intestazioni esatte. Richiedono verifica.",
    }
