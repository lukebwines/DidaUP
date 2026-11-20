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
from app.department_workbooks import (
    HISTORIC_HEADERS, VISIBLE_HEADERS, TECH_HEADERS,
    WorkbookGenerationError, build_five_workbooks,
)


def make_source(path: Path, *, malicious=False, wrong_year=False):
    source_headers = list(HISTORIC_HEADERS)
    assert len(source_headers) == 33
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
            "MODULO": module, "ANNO": 2,
            "SSD INSEGNAMENTO": "TEST-SSD",
            "NOME DOCENTE": teacher,
            "DIPARTIMENTO AFFERENZA DOCENTE": dept,
            "TOT ORE EFFETTIVE": hours,
        }
        for col, header in enumerate(source_headers):
            val = values.get(header)
            if isinstance(val, (int, float)):
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
        names = archive.namelist()
        assert len(names) == 5
        assert all(name.endswith(".xlsx") for name in names)
        copies = [archive.read(name) for name in names]
        assert all(copy == copies[0] for copy in copies)
    assert info["copies"] == 5
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
    assert rows[6][28] == 20
    assert rows[7][28] == 10
    assert rows[8][28] in ("", None)
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
        # A malicious-looking source text is a *literal*, not an executable formula.
        shared = xlsx.read("xl/sharedStrings.xml").decode()
        assert '=HYPERLINK(' in shared
        assert "https://example.invalid" in shared


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
        contents = [archive.read(name) for name in archive.namelist()]
        assert all(x == contents[0] for x in contents)


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
        output.write_bytes(zf.read(zf.namelist()[0]))
        rows = CalamineWorkbook.from_path(output).get_sheet_by_name(
            "Proposte SSD"
        ).to_python(skip_empty_area=False)
        assert rows[6][3] == "2025/26"
    with pytest.raises(WorkbookGenerationError, match="hash"):
        build_five_workbooks(src, "0" * 64, "Offerta sintetica", 1,
                             assigned, "2026/27")


def test_mandatory_mapped_hours_not_substituted_with_planned(tmp_path):
    src = tmp_path / "synthetic.xlsx"
    assigned = make_source(src)
    assigned.pop("ore_effettive_totali")
    with pytest.raises(WorkbookGenerationError, match="ore_effettive_totali"):
        build_five_workbooks(
            src, hashlib.sha256(src.read_bytes()).hexdigest(),
            "Offerta sintetica", 1, assigned, "2026/27"
        )



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
    artifact_id = created.json()["id"]
    download_path = f"/api/years/1/department-workbooks/{artifact_id}/download"
    response = client.get(download_path)
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/zip"
    with ZipFile(io.BytesIO(response.content)) as archive:
        names = archive.namelist()
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
