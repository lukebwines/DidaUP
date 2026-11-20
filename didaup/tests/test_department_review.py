"""Five-file review: synthetic proposals, cross-file overlaps, source validation."""
from __future__ import annotations

import hashlib
import io
from pathlib import Path
from zipfile import ZipFile

import pytest
from python_calamine import CalamineWorkbook
import xlsxwriter

from app.department_workbooks import build_five_workbooks
from app.department_review import review_five_workbooks
from test_department_workbooks import make_source

WORKLOAD_RULES = [{"tipologia": "", "cds": "", "taf": "", "mode": "percentuale", "value": "100"}]


def fixture_five(tmp_path, *, mutuazione_bool=False):
    original = tmp_path / "historical.xlsx"
    assigned = make_source(original, mutuazione_bool=mutuazione_bool)
    digest = hashlib.sha256(original.read_bytes()).hexdigest()
    packed, _ = build_five_workbooks(
        original, digest, "Offerta sintetica", 1, assigned, "2026/27",
        workload_rules=WORKLOAD_RULES,
    )
    with ZipFile(io.BytesIO(packed)) as zipfile:
        paths = []
        for index, name in enumerate(
            (name for name in zipfile.namelist() if "_Dipartimento_" in name), 1
        ):
            item = tmp_path / f"dept_{index}.xlsx"
            item.write_bytes(zipfile.read(name))
            paths.append(item)
    return original, assigned, digest, paths


def edit_synthetic_workbook(path, changes, *,
                            additional=None, tamper=None):
    """Rewrite ONLY in tests; preserve sheet values, not workbook styling."""
    src = CalamineWorkbook.from_path(path)
    rows = src.get_sheet_by_name("Proposte SSD").to_python(skip_empty_area=False)
    new = path.with_name("edited-" + path.name)
    wb = xlsxwriter.Workbook(str(new))
    sheet = wb.add_worksheet("Proposte SSD")
    for row_index, values in enumerate(rows):
        values = list(values) + [""] * max(0, 41-len(values))
        if row_index in changes:
            for col, value in changes[row_index].items():
                values[col] = value
        if tamper and row_index == tamper[0]:
            values[tamper[1]] = tamper[2]
        for col, value in enumerate(values):
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                sheet.write_number(row_index, col, value)
            elif value is not None:
                sheet.write_string(row_index, col, str(value))
    if additional:
        for original_index, new_teacher, hours in additional:
            row = list(rows[original_index]) + [""] * max(0, 41-len(rows[original_index]))
            row[29:33] = ["Aggiunta", new_teacher, hours, ""]
            row[37] = "VARIAZIONE"
            row[39] = "DIDAUP-VAR-000001"
            at = len(rows)
            for col, val in enumerate(row):
                if isinstance(val, (int, float)):
                    sheet.write_number(at, col, val)
                elif val is not None:
                    sheet.write_string(at, col, str(val))
    wb.close()
    return new


def inspect(original, assigned, digest, paths):
    return review_five_workbooks(
        original, digest, "Offerta sintetica", 1,
        assigned, "2026/27", paths, workload_rules=WORKLOAD_RULES,
    )


def test_unchanged_five_files_do_not_count_as_five_confirmations(tmp_path):
    original, assigned, digest, paths = fixture_five(tmp_path)
    result = inspect(original, assigned, digest, paths)
    assert result["blocked"] is False
    assert result["overlap_count"] == 0
    assert result["issue_count_at_least"] == 0
    assert all(item["changes_found"] == 0 for item in result["per_file"])


def test_boolean_mutuazione_validates_on_review_and_detects_tampering(tmp_path):
    original, assigned, digest, paths = fixture_five(
        tmp_path, mutuazione_bool=True
    )
    clean = inspect(original, assigned, digest, paths)
    assert clean["blocked"] is False
    assert clean["issue_count_at_least"] == 0
    from app.department_workbooks import VISIBLE_HEADERS
    mutuazione = VISIBLE_HEADERS.index("MUTUAZIONE")
    # Invert a historically locked cell: the review must reject it.
    paths[0] = edit_synthetic_workbook(
        paths[0], {}, tamper=(6, mutuazione, "FALSO")
    )
    result = inspect(original, assigned, digest, paths)
    assert result["blocked"] is True
    assert any("storiche" in x["reason"] for x in result["issues"])


def test_same_activity_edited_in_two_departments_flags_overlap(tmp_path):
    original, assigned, digest, paths = fixture_five(tmp_path)
    paths[0] = edit_synthetic_workbook(
        paths[0], {6: {29: "Aggiunta", 30: "Docente Nuovo 1", 31: 8}}
    )
    # Another historic teacher of the SAME module, in another file.
    paths[1] = edit_synthetic_workbook(
        paths[1], {7: {29: "Aggiunta", 30: "Docente Nuovo 2", 31: 4}}
    )
    result = inspect(original, assigned, digest, paths)
    assert result["blocked"] is True
    assert result["overlap_count"] == 1
    assert result["overlaps"][0]["files"] == [1, 2]
    assert result["overlaps"][0]["identical_proposals"] is False
    assert result["issue_count_at_least"] == 0


def test_duplicate_proposal_across_departments_is_not_auto_accepted(tmp_path):
    original, assigned, digest, paths = fixture_five(tmp_path)
    for i in (0, 1):
        paths[i] = edit_synthetic_workbook(
            paths[i], {6: {29: "Aggiunta", 30: "Docente C", 31: 8}}
        )
    result = inspect(original, assigned, digest, paths)
    assert result["blocked"]
    assert result["overlap_count"] == 1
    assert result["overlaps"][0]["identical_proposals"] is True


def test_modified_historical_hours_or_hidden_origin_is_rejected(tmp_path):
    original, assigned, digest, paths = fixture_five(tmp_path)
    paths[0] = edit_synthetic_workbook(
        paths[0], {6: {29: "Aggiunta", 30: "Docente C", 31: 8}},
        tamper=(6, 28, 999),
    )
    paths[1] = edit_synthetic_workbook(
        paths[1], {6: {38: "SRC-manipolato"}},
    )
    result = inspect(original, assigned, digest, paths)
    assert result["blocked"]
    assert any("storiche" in i["reason"] for i in result["issues"])
    assert any("ID origine" in i["reason"] for i in result["issues"])


def test_two_transfers_from_same_old_teacher_cannot_exceed_hours(tmp_path):
    original, assigned, digest, paths = fixture_five(tmp_path)
    paths[0] = edit_synthetic_workbook(
        paths[0], {6: {29: "Aggiunta", 30: "Docente C", 31: 15}},
        additional=[(6, "Docente D", 8)],
    )
    result = inspect(original, assigned, digest, paths)
    assert result["blocked"]
    assert any("oltre il disponibile" in item["reason"] for item in result["issues"])
    assert result["overlap_count"] == 0  # Single file, no cross-file overlap.


def test_uncovered_activity_cannot_silently_inherit_missing_hours(tmp_path):
    original, assigned, digest, paths = fixture_five(tmp_path)
    paths[0] = edit_synthetic_workbook(
        paths[0], {8: {29: "Sostituzione totale", 30: "Docente Nuovo"}}
    )
    result = inspect(original, assigned, digest, paths)
    assert result["blocked"]
    assert any("Ore storiche assenti" in item["reason"] for item in result["issues"])
