"""Regression tests: five complete/identical Excel copies, synthetic data ONLY."""
from __future__ import annotations

import hashlib
import io
import re
from pathlib import Path
from zipfile import ZipFile

import pytest
from python_calamine import CalamineWorkbook
import xlsxwriter

from app.column_mapping import OFFER_HEADER_TO_FIELD
from app.row_identity import source_row_id
from app.department_workbooks import (
    HISTORIC_HEADERS, VISIBLE_HEADERS, TECH_HEADERS, HIDDEN_REFERENT_HEADERS,
    WorkbookGenerationError, build_five_workbooks, _verify_xlsx_ids,
)


def referent_names(archive):
    """The ZIP now includes a sixth internal audit workbook."""
    return [name for name in archive.namelist()
            if "_Dipartimento_" in name and name.endswith(".xlsx")]


def make_source(path: Path, *, malicious=False, wrong_year=False, incomplete_annuality=False, mutuazione_bool=False, with_tipologia=False, blank_planned_rows=(), invalid_planned_rows=None, taf_by_course=None):
    source_headers = list(HISTORIC_HEADERS) + (["TIPOLOGIA"] if with_tipologia else [])
    assert len(source_headers) == (34 if with_tipologia else 33)
    wb = xlsxwriter.Workbook(str(path))
    sh = wb.add_worksheet("Offerta sintetica")
    for column, name in enumerate(source_headers):
        sh.write_string(0, column, name)

    def write_row(row_number, *, course, module, teacher, hours, dept):
        values = {
            "SEDE CORSO": "Sede TEST", "CODICE CORSO": course,
            "CDS": "Corso sintetico", "ANNO ACCADEMICO": (
                "2025/26" if wrong_year else "2026/27"
            ),
            "CODICE INS": module, "INSEGNAMENTO": (
                '=HYPERLINK("https://example.invalid", "test")'
                if malicious else "Insegnamento di prova"
            ),
            "CODICE UGOV": f"UGOV-{module}",
            "MODULO": module, "ANNO": ("" if incomplete_annuality and row_number == 3 else 2),
            "SSD INSEGNAMENTO": "TEST-SSD",
            "TAF": (taf_by_course or {}).get(course, "TAF-SINTETICO"),
            "MUTUAZIONE": (row_number in (1, 4)) if mutuazione_bool else None,
            "NOME DOCENTE": teacher,
            "DIPARTIMENTO AFFERENZA DOCENTE": dept,
            "TOT ORE EFFETTIVE": hours,
            "TOT ORE PREVISTE": (
                None if row_number in blank_planned_rows
                else (invalid_planned_rows or {}).get(
                    row_number, hours if hours is not None else 0
                )
            ),
            "TIPOLOGIA": "Laurea" if course == "SYN-A" else "Magistrale",
        }
        for col, header in enumerate(source_headers):
            val = values.get(header)
            if isinstance(val, bool):
                sh.write_boolean(row_number, col, val)
            elif isinstance(val, (int, float)):
                sh.write_number(row_number, col, val)
            elif val is not None:
                sh.write_string(row_number, col, val)
    write_row(1, course="SYN-A", module="SYN-1", teacher="Docente A", hours=20, dept="D1")
    write_row(2, course="SYN-A", module="SYN-1", teacher="Docente B", hours=10, dept="D2")
    write_row(3, course="SYN-A", module="SYN-2", teacher="", hours=None, dept="")
    write_row(4, course="SYN-B", module="SYN-3", teacher="Docente D", hours=8, dept="D5")
    wb.close()
    assigned = {
        OFFER_HEADER_TO_FIELD[h.upper()]: index
        for index, h in enumerate(source_headers)
        if h.upper() in OFFER_HEADER_TO_FIELD
    }
    return assigned


def test_five_copies_are_byte_identical_and_unfiltered(tmp_path):
    source = tmp_path / "synthetic.xlsx"
    assigned = make_source(source, malicious=True)
    content, info = build_five_workbooks(
        source, hashlib.sha256(source.read_bytes()).hexdigest(),
        "Offerta sintetica", 1, assigned, "2026/27",
    )
    with ZipFile(io.BytesIO(content)) as archive:
        names = referent_names(archive)
        assert len(names) == 5
        assert all(name.endswith(".xlsx") for name in names)
        revisions = [
            re.search(r"_rev-(\d{8}T\d{6}Z-[0-9a-f]{6})_Dipartimento_\d{2}\.xlsx$", name)
            for name in names
        ]
        assert all(revisions), "Each Excel must carry an export revision"
        assert len({m.group(1) for m in revisions}) == 1, (
            "All five files must come from the SAME export revision"
        )
        copies = [archive.read(name) for name in names]
        assert all(copy == copies[0] for copy in copies)
    assert info["copies"] == 5
    assert re.fullmatch(r"\d{8}T\d{6}Z-[0-9a-f]{6}", info["export_revision"])
    assert info["historical_rows"] == 4  # ALL source activities.
    assert info["excluded_rows"] == 0
    assert info["department_filter"] is False

    first = tmp_path / "generated.xlsx"
    first.write_bytes(copies[0])
    parsed = CalamineWorkbook.from_path(first).get_sheet_by_name("Proposte SSD")
    rows = parsed.to_python(skip_empty_area=False)
    assert rows[5][:37] == VISIBLE_HEADERS
    assert rows[5][37:41] == list(TECH_HEADERS)
    assert rows[6][1] == "SYN-A"
    assert rows[7][1] == "SYN-A"
    assert rows[8][1] == "SYN-A"
    assert rows[9][1] == "SYN-B"
    assert [row[28] for row in rows[6:10]] == [20, 10, 0, 8]
    assert rows[6][29:33] in (["", "", "", ""], [None, None, None, None])
    assert rows[6][37] == "STORICO"
    assert rows[6][38] == rows[6][39]
    assert rows[6][40] == rows[7][40]  # Same activity, different old teachers.
    assert rows[8][40] != rows[6][40]

    with ZipFile(io.BytesIO(copies[0])) as xlsx:
        worksheet_xml = xlsx.read("xl/worksheets/sheet1.xml").decode()
        assert "<sheetProtection " in worksheet_xml
        assert "<autoFilter " in worksheet_xml
        assert "<f>" not in worksheet_xml
        assert "<f " not in worksheet_xml
        assert "<cols>" in worksheet_xml
        assert 'hidden="1"' in worksheet_xml
        # Each requested column is hidden, while retaining data for reimport.
        from xml.etree import ElementTree as ET
        root = ET.fromstring(worksheet_xml)
        namespace = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
        for header in HIDDEN_REFERENT_HEADERS:
            index = VISIBLE_HEADERS.index(header) + 1
            assert any(
                int(col.get("min")) <= index <= int(col.get("max"))
                and col.get("hidden") == "1"
                for col in root.findall("./m:cols/m:col", namespace)
            ), header
        assert len(HIDDEN_REFERENT_HEADERS) == 7
        assert set(HIDDEN_REFERENT_HEADERS).isdisjoint(
            {"Tipo variazione", "Nuovo docente", "Ore", "Note"}
        )
        # A malicious-looking source text is a *literal*, not an executable formula.
        shared = xlsx.read("xl/sharedStrings.xml").decode()
        assert '=HYPERLINK(' in shared
        assert "https://example.invalid" in shared


def test_sixth_excel_contains_only_actually_removed_rows_and_reasons(tmp_path):
    source = tmp_path / "synthetic-exclusion-audit.xlsx"
    mapping = make_source(source)
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    packed, info = build_five_workbooks(
        source, digest, "Offerta sintetica", 1, mapping, "2026/27",
        excluded={("SYN-B", "Sede TEST", 2)},
        included={("SYN-A", "Sede TEST", 2)},
    )
    assert info["copies"] == 5
    assert info["archive_files"] == 6
    assert info["excluded_rows"] == info["excluded_file_rows"] == 1
    assert info["reconciliation"] == {
        "verified": True,
        "source_nonempty_rows": 4,
        "included_in_each_workbook": 3,
        "excluded_in_internal_register": 1,
        "missing_from_outputs": 0,
        "duplicate_ids": 0,
        "exported_workbooks_checked": 5,
        "internal_register_checked": True,
    }
    with ZipFile(io.BytesIO(packed)) as archive:
        names = archive.namelist()
        referents = referent_names(archive)
        audits = [name for name in names if "Righe_escluse_" in name]
        assert len(names) == 6 and len(referents) == 5
        assert len(audits) == 1
        assert "CONTROLLO_INTERNO" in audits[0]
        assert len({archive.read(name) for name in referents}) == 1
        internal = tmp_path / "internal.xlsx"
        internal.write_bytes(archive.read(audits[0]))
        delivered = tmp_path / "referent.xlsx"
        delivered.write_bytes(archive.read(referents[0]))
    historical = CalamineWorkbook.from_path(internal).get_sheet_by_name(
        "Righe escluse"
    ).to_python(skip_empty_area=False)
    assert historical[4][:len(HISTORIC_HEADERS)] == HISTORIC_HEADERS
    assert historical[5][HISTORIC_HEADERS.index("CODICE CORSO")] == "SYN-B"
    assert historical[5][len(HISTORIC_HEADERS)] == 5  # source Excel row
    assert "esclus" in historical[5][len(HISTORIC_HEADERS) + 1].lower()
    assert historical[5][len(HISTORIC_HEADERS) + 4].startswith("SRC-")
    delivered_rows = CalamineWorkbook.from_path(delivered).get_sheet_by_name(
        "Proposte SSD"
    ).to_python(skip_empty_area=False)
    assert "SYN-B" not in [r[1] for r in delivered_rows[6:]]
    with ZipFile(io.BytesIO(packed)) as archive:
        assert hashlib.sha256(archive.read(audits[0])).hexdigest() == (
            info["excluded_audit_sha256"]
        )


def test_sixth_excel_has_zero_records_when_nothing_excluded(tmp_path):
    source = tmp_path / "synthetic-no-exclusions.xlsx"
    mapping = make_source(source)
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    packed, stats = build_five_workbooks(
        source, digest, "Offerta sintetica", 1, mapping, "2026/27"
    )
    assert stats["excluded_rows"] == stats["excluded_file_rows"] == 0
    assert stats["reconciliation"]["source_nonempty_rows"] == 4
    assert stats["reconciliation"]["included_in_each_workbook"] == 4
    assert stats["reconciliation"]["excluded_in_internal_register"] == 0
    with ZipFile(io.BytesIO(packed)) as archive:
        audit = next(name for name in archive.namelist()
                     if name.endswith("CONTROLLO_INTERNO.xlsx"))
        path = tmp_path / "empty-internal.xlsx"
        path.write_bytes(archive.read(audit))
    rows = CalamineWorkbook.from_path(path).get_sheet_by_name(
        "Righe escluse"
    ).to_python(skip_empty_area=False)
    assert rows[4][0] == HISTORIC_HEADERS[0]
    assert len(rows) == 5


def test_taf_is_recovered_from_unique_exact_header_if_old_mapping_omits_it(tmp_path):
    source = tmp_path / "synthetic-taf.xlsx"
    assigned = make_source(source)
    assigned.pop("taf")
    packed, info = build_five_workbooks(
        source, hashlib.sha256(source.read_bytes()).hexdigest(),
        "Offerta sintetica", 1, assigned, "2026/27"
    )
    assert info["taf_mapping_mode"] == "intestazione TAF esatta, recuperata per export"
    assert info["taf_rows_with_value"] == 4
    assert info["taf_rows_without_value"] == 0
    with ZipFile(io.BytesIO(packed)) as bundle:
        first = tmp_path / "first.xlsx"
        first.write_bytes(bundle.read(referent_names(bundle)[0]))
    sheet = CalamineWorkbook.from_path(first).get_sheet_by_name("Proposte SSD")
    rows = sheet.to_python(skip_empty_area=False)
    assert rows[6][VISIBLE_HEADERS.index("TAF")] == "TAF-SINTETICO"


def test_taf_from_saved_mapping_is_preserved_without_guessing(tmp_path):
    source = tmp_path / "synthetic-taf-mapped.xlsx"
    assigned = make_source(source)
    packed, info = build_five_workbooks(
        source, hashlib.sha256(source.read_bytes()).hexdigest(),
        "Offerta sintetica", 1, assigned, "2026/27"
    )
    assert info["taf_mapping_mode"] == "mappatura salvata"
    assert info["taf_rows_with_value"] == 4


def test_boolean_mutuazione_is_visible_as_vero_falso_in_all_five(tmp_path):
    """Native Excel TRUE/FALSE must not turn into blank historical cells."""
    source = tmp_path / "mutuazione-bool.xlsx"
    assigned = make_source(source, mutuazione_bool=True)
    # Confirm source really contains native spreadsheet boolean values.
    original = CalamineWorkbook.from_path(source).get_sheet_by_name(
        "Offerta sintetica"
    ).to_python(skip_empty_area=False)
    column = HISTORIC_HEADERS.index("MUTUAZIONE")
    assert [original[i][column] for i in range(1, 5)] == [
        True, False, False, True
    ]
    packed, info = build_five_workbooks(
        source, hashlib.sha256(source.read_bytes()).hexdigest(),
        "Offerta sintetica", 1, assigned, "2026/27"
    )
    assert info["copies"] == 5
    assert info["mutuazione_mapping_mode"] == "mappatura salvata"
    assert info["mutuazione_true_rows"] == 2
    assert info["mutuazione_false_rows"] == 2
    assert info["mutuazione_other_rows"] == 0
    assert info["mutuazione_empty_rows"] == 0
    with ZipFile(io.BytesIO(packed)) as archive:
        payloads = [archive.read(name) for name in referent_names(archive)]
    assert len(payloads) == 5 and all(blob == payloads[0] for blob in payloads)
    excel = tmp_path / "with-mutuazione.xlsx"
    excel.write_bytes(payloads[0])
    output = CalamineWorkbook.from_path(excel).get_sheet_by_name(
        "Proposte SSD"
    ).to_python(skip_empty_area=False)
    column = VISIBLE_HEADERS.index("MUTUAZIONE")
    assert [output[i][column] for i in range(6, 10)] == [
        "VERO", "FALSO", "FALSO", "VERO"
    ]


def test_unmapped_legacy_mutuazione_is_recovered_only_from_exact_header(tmp_path):
    source = tmp_path / "mutuazione-legacy.xlsx"
    assigned = make_source(source, mutuazione_bool=True)
    assigned.pop("mutuazione")
    packed, info = build_five_workbooks(
        source, hashlib.sha256(source.read_bytes()).hexdigest(),
        "Offerta sintetica", 1, assigned, "2026/27"
    )
    assert info["mutuazione_mapping_mode"] == (
        "intestazione MUTUAZIONE esatta, recuperata per export"
    )
    assert info["mutuazione_true_rows"] == 2
    assert info["mutuazione_false_rows"] == 2
    with ZipFile(io.BytesIO(packed)) as archive:
        file = tmp_path / "mutuazione-result.xlsx"
        file.write_bytes(archive.read(referent_names(archive)[0]))
    output = CalamineWorkbook.from_path(file).get_sheet_by_name(
        "Proposte SSD"
    ).to_python(skip_empty_area=False)
    index = VISIBLE_HEADERS.index("MUTUAZIONE")
    assert [output[i][index] for i in range(6, 10)] == [
        "VERO", "FALSO", "FALSO", "VERO"
    ]


def test_explicit_cohort_exclusions_apply_to_all_five_copies(tmp_path):
    source = tmp_path / "synthetic.xlsx"
    assigned = make_source(source)
    packed, stats = build_five_workbooks(
        source, hashlib.sha256(source.read_bytes()).hexdigest(),
        "Offerta sintetica", 1, assigned, "2026/27",
        excluded={("SYN-B", "Sede TEST", 2)},
    )
    assert stats["excluded_rows"] == 1
    assert stats["historical_rows"] == 3
    with ZipFile(io.BytesIO(packed)) as archive:
        contents = [archive.read(name) for name in referent_names(archive)]
        assert all(x == contents[0] for x in contents)


def test_incomplete_annuality_does_not_block_generation_or_discard_row(tmp_path):
    source = tmp_path / "synthetic-incomplete.xlsx"
    assigned = make_source(source, incomplete_annuality=True)
    packed, summary = build_five_workbooks(
        source, hashlib.sha256(source.read_bytes()).hexdigest(),
        "Offerta sintetica", 1, assigned, "2026/27",
        excluded={("SYN-B", "Sede TEST", 2)},
        included={("SYN-A", "Sede TEST", 1)},
    )
    assert summary["copies"] == 5
    assert summary["excluded_rows"] == 1
    assert summary["unresolved_annuality_rows_included"] == 1
    assert summary["unresolved_annuality_example_rows"] == [4]
    assert summary["historical_rows"] == 3
    with ZipFile(io.BytesIO(packed)) as archive:
        copies = [archive.read(name) for name in referent_names(archive)]
        assert len(copies) == 5
        assert all(data == copies[0] for data in copies)
    exported = tmp_path / "exported.xlsx"
    exported.write_bytes(copies[0])
    values = CalamineWorkbook.from_path(exported).get_sheet_by_name(
        "Proposte SSD"
    ).to_python(skip_empty_area=False)
    # The incomplete source annuality remains in the generated workbook.
    assert values[8][5] == "SYN-2"


def test_missing_both_activity_codes_keeps_all_rows_with_distinct_ids(tmp_path):
    source = tmp_path / "no-teaching-codes.xlsx"
    assigned = make_source(source)
    # The original source can contain empty codes; create an otherwise
    # identical report with truly blank codes for both teachers on one module.
    original = CalamineWorkbook.from_path(source).get_sheet_by_name(
        "Offerta sintetica"
    ).to_python(skip_empty_area=False)
    rewritten = tmp_path / "blank-codes.xlsx"
    writer = xlsxwriter.Workbook(str(rewritten))
    sh = writer.add_worksheet("Offerta sintetica")
    cols = {header: i for i, header in enumerate(original[0])}
    for r, items in enumerate(original):
        for c, value in enumerate(items):
            if r in (1, 2) and c in (
                cols["CODICE INS"], cols["CODICE UGOV"]
            ):
                continue
            if value is None:
                continue
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                sh.write_number(r, c, value)
            else:
                sh.write_string(r, c, str(value))
    writer.close()
    packed, info = build_five_workbooks(
        rewritten, hashlib.sha256(rewritten.read_bytes()).hexdigest(),
        "Offerta sintetica", 1, assigned, "2026/27"
    )
    assert info["copies"] == 5
    assert info["historical_rows"] == 4
    assert info["missing_activity_codes_rows_included"] == 2
    assert info["missing_activity_codes_example_rows"] == [2, 3]
    with ZipFile(io.BytesIO(packed)) as bundle:
        copies = [bundle.read(name) for name in referent_names(bundle)]
        assert len(set(copies)) == 1
    extracted = tmp_path / "out.xlsx"
    extracted.write_bytes(copies[0])
    rows = CalamineWorkbook.from_path(extracted).get_sheet_by_name(
        "Proposte SSD"
    ).to_python(skip_empty_area=False)
    assert rows[6][40] != rows[7][40]
    assert rows[6][40].startswith("ACT-ROW-")
    assert rows[7][40].startswith("ACT-ROW-")



def test_exclusions_ignore_case_and_surrounding_spaces(tmp_path):
    source = tmp_path / "excluded-normalized.xlsx"
    assigned = make_source(source)
    packed, info = build_five_workbooks(
        source, hashlib.sha256(source.read_bytes()).hexdigest(),
        "Offerta sintetica", 1, assigned, "2026/27",
        excluded={(" syn-b ", " sede test  ", 2)},
        included={("SYN-A", "Sede TEST", 2)},
    )
    assert info["excluded_rows"] == 1
    assert info["unmatched_exclusion_count"] == 0
    assert info["historical_rows"] == 3
    with ZipFile(io.BytesIO(packed)) as archive:
        item = tmp_path / "normalized.xlsx"
        item.write_bytes(archive.read(referent_names(archive)[0]))
    rows = CalamineWorkbook.from_path(item).get_sheet_by_name(
        "Proposte SSD"
    ).to_python(skip_empty_area=False)
    assert all(row[1] != "SYN-B" for row in rows[6:])


def test_missing_year_removed_only_when_all_registered_annualities_excluded(tmp_path):
    source = tmp_path / "missing-year.xlsx"
    assigned = make_source(source, incomplete_annuality=True)
    packed, info = build_five_workbooks(
        source, hashlib.sha256(source.read_bytes()).hexdigest(),
        "Offerta sintetica", 1, assigned, "2026/27",
        excluded={("SYN-A", "Sede TEST", 2)},
        included=set(),
    )
    assert info["excluded_rows"] == 3
    assert info["excluded_rows_with_missing_year"] == 1
    assert info["unmatched_exclusion_count"] == 0
    assert info["historical_rows"] == 1
    with ZipFile(io.BytesIO(packed)) as archive:
        item = tmp_path / "all-excluded.xlsx"
        item.write_bytes(archive.read(referent_names(archive)[0]))
    rows = CalamineWorkbook.from_path(item).get_sheet_by_name(
        "Proposte SSD"
    ).to_python(skip_empty_area=False)
    assert rows[6][1] == "SYN-B"


def test_unmatched_exclusions_are_reported_not_silently_ignored(tmp_path):
    source = tmp_path / "unmatched.xlsx"
    assigned = make_source(source)
    _, info = build_five_workbooks(
        source, hashlib.sha256(source.read_bytes()).hexdigest(),
        "Offerta sintetica", 1, assigned, "2026/27",
        excluded={("NOT-IN-REPORT", "Verona", 1)},
    )
    assert info["excluded_rows"] == 0
    assert info["unmatched_exclusion_count"] == 1
    assert info["unmatched_exclusion_examples"][0]["course_code"] == "not-in-report"



def _write_named_course_report(path, *, course_year="1,2,3", source_code="CF-REPORT",
                                name="Corso di formazione continua sintetico"):
    wb = xlsxwriter.Workbook(str(path))
    sheet = wb.add_worksheet("Offerta sintetica")
    for index, header in enumerate(HISTORIC_HEADERS):
        sheet.write_string(0, index, header)
    examples = [
        {
            "CODICE CORSO": source_code, "CDS": name,
            "SEDE CORSO": "VERONA", "ANNO": course_year,
            "CODICE INS": "MOD-TEST", "CODICE UGOV": "UGOV-TEST",
            "INSEGNAMENTO": "Materia simulata", "MODULO": "Modulo prova",
            "SSD INSEGNAMENTO": "TEST-SSD", "TOT ORE EFFETTIVE": 10,
        },
        {
            "CODICE CORSO": "ALTRO-CDS", "CDS": "CdS da mantenere",
            "SEDE CORSO": "VERONA", "ANNO": "1",
            "CODICE INS": "ALT-TEST", "CODICE UGOV": "UGOV-ALT",
            "INSEGNAMENTO": "Materia diversa", "MODULO": "Modulo diverso",
            "SSD INSEGNAMENTO": "TEST-SSD", "TOT ORE EFFETTIVE": 6,
        },
    ]
    for i, data in enumerate(examples, 1):
        for j, header in enumerate(HISTORIC_HEADERS):
            value = data.get(header)
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                sheet.write_number(i, j, value)
            elif value is not None:
                sheet.write_string(i, j, str(value))
    wb.close()
    return {
        OFFER_HEADER_TO_FIELD[h.upper()]: i
        for i, h in enumerate(HISTORIC_HEADERS)
        if h.upper() in OFFER_HEADER_TO_FIELD
    }


def _export_named_case(source, mapping, *, excluded, included=(), cohort_names=None):
    return build_five_workbooks(
        source, hashlib.sha256(source.read_bytes()).hexdigest(),
        "Offerta sintetica", 1, mapping, "2026/27",
        excluded=set(excluded), included=set(included),
        cohort_names=cohort_names,
    )


def test_entire_excluded_cds_is_removed_even_with_source_year_1_2_3(tmp_path):
    source = tmp_path / "multiyear.xlsx"
    mapping = _write_named_course_report(source)
    packed, info = _export_named_case(
        source, mapping, excluded={("CF-REPORT", "VERONA", 1)}
    )
    assert info["excluded_rows"] == 1
    assert info["unmatched_exclusion_count"] == 0
    assert info["mixed_annuality_rows_retained"] == 0
    assert info["historical_rows"] == 1
    with ZipFile(io.BytesIO(packed)) as package:
        payloads = [package.read(name) for name in referent_names(package)]
        assert len(payloads) == 5 and all(x == payloads[0] for x in payloads)
    file = tmp_path / "retained.xlsx"
    file.write_bytes(payloads[0])
    rows = CalamineWorkbook.from_path(file).get_sheet_by_name(
        "Proposte SSD"
    ).to_python(skip_empty_area=False)
    assert rows[6][2] == "CdS da mantenere"
    assert not any(
        "formazione continua sintetico" in str(row[2])
        for row in rows[6:]
    )


def test_name_fallback_must_be_unique_and_reported(tmp_path):
    source = tmp_path / "different-code.xlsx"
    title = "Corso di formazione continua sintetico"
    mapping = _write_named_course_report(source, source_code="SOURCE-CODE")
    key = ("REGISTRY-CODE", "VERONA", 1)
    _, info = _export_named_case(
        source, mapping, excluded={key},
        cohort_names={key: title},
    )
    assert info["excluded_rows"] == 1
    assert info["historical_rows"] == 1
    assert info["unmatched_exclusion_count"] == 0
    assert info["cohorts_matched_by_unique_name_rows"] == 1
    assert info["cohorts_matched_by_unique_name_examples"] == [2]


def test_nonunique_name_fallback_does_not_delete_rows(tmp_path):
    source = tmp_path / "ambiguous-name.xlsx"
    title = "Corso di formazione continua sintetico"
    mapping = _write_named_course_report(source, source_code="SOURCE-CODE")
    key_a = ("REGISTRY-A", "VERONA", 1)
    key_b = ("REGISTRY-B", "VERONA", 1)
    _, info = _export_named_case(
        source, mapping, excluded={key_a, key_b},
        cohort_names={key_a: title, key_b: title},
    )
    assert info["excluded_rows"] == 0
    assert info["unmatched_exclusion_count"] == 2
    assert info["cohorts_matched_by_unique_name_rows"] == 0
    assert info["historical_rows"] == 2


def test_mixed_years_are_retained_and_reported_for_review(tmp_path):
    source = tmp_path / "mixed-year.xlsx"
    mapping = _write_named_course_report(source)
    _, info = _export_named_case(
        source, mapping,
        excluded={("CF-REPORT", "VERONA", 1)},
        included={("CF-REPORT", "VERONA", 2)},
    )
    assert info["excluded_rows"] == 0
    assert info["mixed_annuality_rows_retained"] == 1
    assert info["mixed_annuality_example_rows"] == [2]
    assert info["unmatched_exclusion_count"] == 0
    assert info["historical_rows"] == 2


def test_per_row_academic_year_is_preserved_and_source_integrity_checked(tmp_path):
    src = tmp_path / "synthetic.xlsx"
    assigned = make_source(src, wrong_year=True)
    digest = hashlib.sha256(src.read_bytes()).hexdigest()
    archive, details = build_five_workbooks(
        src, digest, "Offerta sintetica", 1, assigned, "2026/27"
    )
    assert details["historical_rows"] == 4
    with ZipFile(io.BytesIO(archive)) as zf:
        output = tmp_path / "output.xlsx"
        output.write_bytes(zf.read(referent_names(zf)[0]))
        rows = CalamineWorkbook.from_path(output).get_sheet_by_name(
            "Proposte SSD"
        ).to_python(skip_empty_area=False)
        assert rows[6][3] == "2025/26"
    with pytest.raises(WorkbookGenerationError, match="hash"):
        build_five_workbooks(src, "0" * 64, "Offerta sintetica", 1,
                             assigned, "2026/27")


def test_effective_hours_unmapped_take_planned_hours_by_default(tmp_path):
    src = tmp_path / "synthetic.xlsx"
    assigned = make_source(src)
    assigned.pop("ore_effettive_totali")
    original_hash = hashlib.sha256(src.read_bytes()).hexdigest()
    bundle, stats = build_five_workbooks(
        src, original_hash, "Offerta sintetica", 1, assigned, "2026/27"
    )
    assert stats["workload"]["rows_without_rule"] == 4
    assert hashlib.sha256(src.read_bytes()).hexdigest() == original_hash
    with ZipFile(io.BytesIO(bundle)) as archive:
        path = tmp_path / "unmapped.xlsx"
        path.write_bytes(archive.read(referent_names(archive)[0]))
    rows = CalamineWorkbook.from_path(path).get_sheet_by_name(
        "Proposte SSD"
    ).to_python(skip_empty_area=False)
    assert [r[28] for r in rows[6:10]] == [20, 10, 0, 8]




def test_source_partition_includes_every_nonexcluded_row_even_without_mapped_fields(tmp_path):
    """A row with only an unmapped column must not silently disappear."""
    original = tmp_path / "synthetic.xlsx"
    assigned = make_source(original)
    base = CalamineWorkbook.from_path(original).get_sheet_by_name(
        "Offerta sintetica"
    ).to_python(skip_empty_area=False)
    enriched = tmp_path / "extra-unmapped-column.xlsx"
    workbook = xlsxwriter.Workbook(str(enriched))
    sh = workbook.add_worksheet("Offerta sintetica")
    for row_no, cells in enumerate(base):
        for col, value in enumerate(cells):
            if value is None:
                continue
            if isinstance(value, bool):
                sh.write_boolean(row_no, col, value)
            elif isinstance(value, (int, float)):
                sh.write_number(row_no, col, value)
            else:
                sh.write_string(row_no, col, str(value))
    sh.write_string(0, len(HISTORIC_HEADERS), "INFORMAZIONE EXTRA NON MAPPATA")
    sh.write_string(10, len(HISTORIC_HEADERS), "Attività senza corrispondenze")
    workbook.close()
    digest = hashlib.sha256(enriched.read_bytes()).hexdigest()
    package, result = build_five_workbooks(
        enriched, digest, "Offerta sintetica", 1, assigned, "2026/27",
        excluded={("SYN-B", "Sede TEST", 2)},
    )
    assert result["reconciliation"]["source_nonempty_rows"] == 5
    assert result["reconciliation"]["included_in_each_workbook"] == 4
    assert result["reconciliation"]["excluded_in_internal_register"] == 1
    with ZipFile(io.BytesIO(package)) as archive:
        names = referent_names(archive)
        assert len(names) == 5
        assert len({archive.read(name) for name in names}) == 1
        path = tmp_path / "included.xlsx"
        path.write_bytes(archive.read(names[0]))
    data = CalamineWorkbook.from_path(path).get_sheet_by_name(
        "Proposte SSD"
    ).to_python(skip_empty_area=False)
    assert len(data[6:]) == 4
    assert [row[38] for row in data[6:]] == [
        source_row_id(digest, "Offerta sintetica", row)
        for row in (2, 3, 4, 11)
    ]


def test_reconciliation_blocks_missing_or_duplicated_exported_ids(tmp_path):
    source = tmp_path / "synthetic.xlsx"
    assigned = make_source(source)
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    package, info = build_five_workbooks(
        source, digest, "Offerta sintetica", 1, assigned, "2026/27"
    )
    with ZipFile(io.BytesIO(package)) as archive:
        payload = archive.read(referent_names(archive)[0])
    expected = [
        source_row_id(digest, "Offerta sintetica", row)
        for row in (2, 3, 4, 5)
    ]
    _verify_xlsx_ids(payload, "Proposte SSD", 6, 38, expected, "collaudo")
    with pytest.raises(WorkbookGenerationError, match="completezza fallita"):
        _verify_xlsx_ids(
            payload, "Proposte SSD", 6, 38, expected + ["SRC-synthetic-missing"], "collaudo"
        )

    output = io.BytesIO()
    workbook = xlsxwriter.Workbook(output, {"in_memory": True})
    sh = workbook.add_worksheet("Proposte SSD")
    sh.write_string(6, 38, expected[0])
    sh.write_string(7, 38, expected[0])
    workbook.close()
    with pytest.raises(WorkbookGenerationError, match="duplicate 1"):
        _verify_xlsx_ids(
            output.getvalue(), "Proposte SSD", 6, 38, expected[:2], "collaudo"
        )


def test_partial_annuality_rows_remain_present_and_reconciled(tmp_path):
    source = tmp_path / "partial.xlsx"
    assigned = _write_named_course_report(source, course_year="1,2,3")
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    # Year 1 is excluded but years 2 and 3 on that SAME row are included.
    # Never drop the whole source line or silently change ANNO to "2,3".
    archive_bytes, stats = build_five_workbooks(
        source, digest, "Offerta sintetica", 1, assigned, "2026/27",
        excluded={("CF-REPORT", "VERONA", 1)},
        included={("CF-REPORT", "VERONA", 2),
                  ("CF-REPORT", "VERONA", 3)},
    )
    assert stats["reconciliation"]["verified"] is True
    assert stats["reconciliation"]["source_nonempty_rows"] == 2
    assert stats["reconciliation"]["included_in_each_workbook"] == 2
    assert stats["reconciliation"]["excluded_in_internal_register"] == 0
    assert stats["mixed_annuality_rows_retained"] == 1
    assert stats["mixed_annuality_example_rows"] == [2]
    with ZipFile(io.BytesIO(archive_bytes)) as archive:
        item = tmp_path / "partial-out.xlsx"
        item.write_bytes(archive.read(referent_names(archive)[0]))
    rows = CalamineWorkbook.from_path(item).get_sheet_by_name(
        "Proposte SSD"
    ).to_python(skip_empty_area=False)
    assert rows[6][13] == "1,2,3"
    assert [row[38] for row in rows[6:]] == [
        source_row_id(digest, "Offerta sintetica", index) for index in (2, 3)
    ]



# Complete HTTP flow (upload -> mapping -> five identical downloads -> review).
from test_app import client, signed_in


def test_api_generates_private_five_file_zip_and_reviews_unchanged(client, tmp_path):
    synthetic = tmp_path / "source.xlsx"
    assigned = make_source(synthetic)
    csrf = signed_in(client)
    denied = client.post(
        "/api/years/1/department-workbooks", json={"import_id": 1}
    )
    assert denied.status_code == 403  # CSRF required even after login.

    uploaded = client.post(
        "/api/years/1/imports",
        headers=csrf,
        data={"kind": "offerta", "test_data_only": "true"},
        files={"source": ("only-synthetic.xlsx", synthetic.read_bytes(),
                           "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
    )
    assert uploaded.status_code == 200, uploaded.text
    source_id = uploaded.json()["id"]
    saved = client.put(
        f"/api/imports/{source_id}/mapping",
        headers=csrf,
        json={
            "sheet_name": "Offerta sintetica", "header_row": 1,
            "assigned": assigned, "expected_version": 0,
        },
    )
    assert saved.status_code == 200, saved.text
    created = client.post(
        "/api/years/1/department-workbooks",
        headers=csrf, json={"import_id": source_id},
    )
    assert created.status_code == 200, created.text
    assert created.json()["copies"] == 5
    assert created.json()["historical_rows"] == 4
    assert created.json()["department_filter"] is False
    assert created.json()["reconciliation"]["verified"] is True
    assert created.json()["reconciliation"]["source_nonempty_rows"] == 4
    assert created.json()["reconciliation"]["included_in_each_workbook"] == 4
    assert created.json()["reconciliation"]["excluded_in_internal_register"] == 0
    artifact_id = created.json()["id"]
    download_path = f"/api/years/1/department-workbooks/{artifact_id}/download"
    response = client.get(download_path)
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/zip"
    with ZipFile(io.BytesIO(response.content)) as archive:
        names = referent_names(archive)
        assert len(names) == 5
        sheets = [archive.read(name) for name in names]
        assert all(item == sheets[0] for item in sheets)

    review = client.post(
        "/api/years/1/department-workbooks/review", headers=csrf,
        data={"import_id": str(source_id), "test_data_only": "true"},
        files=[
            ("files", (name, content, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"))
            for name, content in zip(names, sheets)
        ],
    )
    assert review.status_code == 200, review.text
    assert review.json()["files_received"] == 5
    assert review.json()["blocked"] is False
    assert review.json()["overlap_count"] == 0

    # Archive reset deletes ONLY the generated ZIP; source and mapping remain.
    reset = client.post(
        "/api/admin/archive/reset", headers=csrf,
        json={"scope": "year", "year_id": 1,
              "confirmation": "AZZERA LAVORAZIONE 2026/27",
              "password": "SyntheticTestingPass!2026"},
    )
    assert reset.status_code == 200
    assert client.get(download_path).status_code == 404
    assert client.get(f"/api/imports/{source_id}/mapping").status_code == 200
    assert len(client.get("/api/years/1/imports").json()) == 1
