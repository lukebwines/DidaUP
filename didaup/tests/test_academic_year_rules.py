"""User-confirmed specialization academic year offset. Synthetic fixtures only."""
import hashlib

import pytest
import xlsxwriter

from app.academic_year_rules import (
    classify_source_year, is_school_of_specialization, prior_academic_year
)
from app.cohort_import import extract_cohorts
from app.department_workbooks import build_five_workbooks, WorkbookGenerationError
from app.column_mapping import OFFER_HEADER_TO_FIELD


def test_only_explicit_specialization_school_can_be_one_year_behind():
    assert is_school_of_specialization(
        course_type="Scuola di Specializzazione"
    )
    assert is_school_of_specialization(
        course_name="Scuola di specializzazione in disciplina TEST"
    )
    assert not is_school_of_specialization(
        course_type="Corso di laurea", course_name="Corso sintetico"
    )
    assert prior_academic_year("2026/27") == "2025/26"
    assert classify_source_year(
        "2025/26", "2026/27", course_type="SCUOLA DI SPECIALIZZAZIONE"
    ) == "specialization_convention"
    assert classify_source_year(
        "2025/26", "2026/27", course_type="CORSO DI LAUREA"
    ) == "invalid"
    assert classify_source_year(
        "2024/25", "2026/27", course_type="SCUOLA DI SPECIALIZZAZIONE"
    ) == "invalid"
    assert classify_source_year(
        "2026/27", "2026/27", course_type="CORSO DI LAUREA"
    ) == "equal"
    assert classify_source_year(
        "2025/26", "2026/27", course_type="",
        course_name="Corso di laurea TEST"
    ) == "invalid"


def make_synthetic_school_report(path):
    headers = [
        "TIPOLOGIA", "SEDE CORSO", "CODICE CORSO", "CDS",
        "ANNO ACCADEMICO", "CODICE INS", "INSEGNAMENTO",
        "MODULO", "ANNO", "SSD INSEGNAMENTO", "TOT ORE EFFETTIVE"
    ]
    wb = xlsxwriter.Workbook(str(path))
    ws = wb.add_worksheet("Offerta")
    for col, h in enumerate(headers):
        ws.write_string(0, col, h)
    def row(i, code, title, kind, year):
        vals = [
            kind, "Sede TEST", code, title, year, f"INS-{i}",
            "Insegnamento sintetico", "Modulo sintetico", 1, "SSD-TEST", 12,
        ]
        for col, val in enumerate(vals):
            if isinstance(val, int):
                ws.write_number(i, col, val)
            else:
                ws.write_string(i, col, val)
    row(1, "SPEC-TEST", "Scuola di specializzazione TEST",
        "SCUOLA DI SPECIALIZZAZIONE", "2025/26")
    row(2, "CDS-TEST", "Corso di laurea TEST", "CORSO DI LAUREA", "2026/27")
    wb.close()
    mapping = {
        OFFER_HEADER_TO_FIELD[key.upper()]: col
        for col, key in enumerate(headers) if key.upper() in OFFER_HEADER_TO_FIELD
    }
    return mapping


def test_specialization_year_is_not_a_cohort_anomaly(tmp_path):
    path = tmp_path / "synthetic.xlsx"
    mapping = make_synthetic_school_report(path)
    result = extract_cohorts(path, "Offerta", 1, mapping, "2026/27")
    assert result["valid_rows"] == 2
    assert result["specialization_convention_rows"] == 1
    assert result["anomaly_count"] == 0
    assert result["cohort_count"] == 2


def test_export_preserves_specialization_source_year_unchanged(tmp_path):
    path = tmp_path / "synthetic.xlsx"
    mapping = make_synthetic_school_report(path)
    bundle, details = build_five_workbooks(
        path, hashlib.sha256(path.read_bytes()).hexdigest(),
        "Offerta", 1, mapping, "2026/27"
    )
    assert details["copies"] == 5
    assert details["historical_rows"] == 2
    # No alteration of the historical source year; no conversion to current AA.
    from zipfile import ZipFile
    from io import BytesIO
    from python_calamine import CalamineWorkbook
    with ZipFile(BytesIO(bundle)) as zipfile:
        item = tmp_path / "export.xlsx"
        item.write_bytes(zipfile.read(zipfile.namelist()[0]))
        sheet = CalamineWorkbook.from_path(item).get_sheet_by_name("Proposte SSD")
        rows = sheet.to_python(skip_empty_area=False)
        assert rows[6][3] == "2025/26"
        assert rows[7][3] == "2026/27"


def test_unidentified_previous_year_does_not_gain_exception(tmp_path):
    path = tmp_path / "synthetic.xlsx"
    mapping = make_synthetic_school_report(path)
    # Use an incorrect mapping so the institutionally relevant 'TIPOLOGIA'
    # is missing: a source classified only by unknown codes must NOT bypass
    # the year validation. The course name is explicit here so also remove it.
    wb = xlsxwriter.Workbook(str(tmp_path / "unknown.xlsx"))
    sh = wb.add_worksheet("Offerta")
    headers = [
        "TIPOLOGIA", "SEDE CORSO", "CODICE CORSO", "CDS",
        "ANNO ACCADEMICO", "CODICE INS", "INSEGNAMENTO",
        "MODULO", "ANNO", "SSD INSEGNAMENTO", "TOT ORE EFFETTIVE"
    ]
    for col, name in enumerate(headers):
        sh.write_string(0, col, name)
    values = [
        "CORSO NON CLASSIFICATO", "Sede TEST", "UNKNOWN",
        "Attività generica TEST", "2025/26", "INS-X", "Insegnamento",
        "Modulo", 1, "SSD-X", 9,
    ]
    for col, val in enumerate(values):
        if isinstance(val, int):
            sh.write_number(1, col, val)
        else:
            sh.write_string(1, col, val)
    wb.close()
    unknown = tmp_path / "unknown.xlsx"
    with pytest.raises(WorkbookGenerationError, match="ammesso solo"):
        build_five_workbooks(
            unknown, hashlib.sha256(unknown.read_bytes()).hexdigest(),
            "Offerta", 1, mapping, "2026/27"
        )
