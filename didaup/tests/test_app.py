"""Synthetic-only smoke tests for the DidaUP alpha backend."""
import importlib
import json

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("DIDAUP_DATA_DIR", str(tmp_path))
    config = tmp_path / "options.json"
    config.write_text(json.dumps({
        "bootstrap_username": "admin",
        "bootstrap_password": "SyntheticTestingPass!2026",
        "secure_cookies": False
    }), encoding="utf-8")
    monkeypatch.setenv("DIDAUP_OPTIONS_PATH", str(config))
    import app.main as main
    importlib.reload(main)
    with TestClient(main.app) as service:
        yield service


def signed_in(client, name="admin", password="SyntheticTestingPass!2026"):
    response = client.post("/api/login", json={"username": name, "password": password})
    assert response.status_code == 200, response.text
    session = client.get("/api/session")
    assert session.status_code == 200
    return {"X-CSRF-Token": session.json()["csrf"]}


def test_authentication_required(client):
    assert client.get("/api/years").status_code == 401
    assert client.post("/api/years", json={"code": "2027/28"}).status_code == 401
    wrong = client.post("/api/login", json={
        "username": "admin", "password": "wrong-password"
    })
    assert wrong.status_code == 401


def test_year_selector_and_non_destructive_exclusion(client):
    csrf = signed_in(client)
    listed = client.get("/api/years")
    assert listed.status_code == 200
    assert [y["code"] for y in listed.json()] == ["2026/27"]

    added = client.post("/api/years", json={"code": "2027/28"}, headers=csrf)
    assert added.status_code == 200, added.text
    year_id = added.json()["id"]

    invalid = client.post("/api/years", json={"code": "2027/29"}, headers=csrf)
    assert invalid.status_code == 422

    cohort = client.post(f"/api/years/{year_id}/cohorts", headers=csrf, json={
        "course_code": "SYNTHETIC-01", "course_name": "Corso fittizio",
        "campus": "Sede simulata", "study_year": 2
    })
    assert cohort.status_code == 200, cohort.text
    cohort_id = cohort.json()["id"]

    missing_csrf = client.patch(
        f"/api/cohorts/{cohort_id}",
        json={"included": False, "reason": "Non in gestione", "expected_version": 1}
    )
    assert missing_csrf.status_code == 403

    excluded = client.patch(f"/api/cohorts/{cohort_id}", headers=csrf, json={
        "included": False, "reason": "Esclusione in fase di collaudo",
        "expected_version": 1
    })
    assert excluded.status_code == 200, excluded.text
    rows = client.get(f"/api/years/{year_id}/cohorts").json()
    assert len(rows) == 1
    assert rows[0]["included"] == 0
    assert rows[0]["exclusion_reason"] == "Esclusione in fase di collaudo"

    conflict = client.patch(f"/api/cohorts/{cohort_id}", headers=csrf, json={
        "included": True, "expected_version": 1
    })
    assert conflict.status_code == 409

    reinstated = client.patch(f"/api/cohorts/{cohort_id}", headers=csrf, json={
        "included": True, "expected_version": 2
    })
    assert reinstated.status_code == 200
    assert client.get(f"/api/years/{year_id}/cohorts").json()[0]["included"] == 1


def test_multi_account_roles_and_revocation(client):
    csrf = signed_in(client)
    created = client.post("/api/users", headers=csrf, json={
        "username": "viewer_test", "password": "SyntheticViewerPass!2026",
        "role": "lettura"
    })
    assert created.status_code == 200, created.text
    viewer_id = created.json()["id"]
    client.post("/api/logout", headers=csrf, json={})

    viewer_csrf = signed_in(client, "viewer_test", "SyntheticViewerPass!2026")
    assert client.get("/api/years").status_code == 200
    assert client.get("/api/users").status_code == 403
    assert client.post("/api/years", headers=viewer_csrf,
                       json={"code": "2027/28"}).status_code == 403
    client.post("/api/logout", headers=viewer_csrf, json={})

    admin_csrf = signed_in(client)
    users = client.get("/api/users").json()
    viewer = next(u for u in users if u["id"] == viewer_id)
    disabled = client.patch(f"/api/users/{viewer_id}", headers=admin_csrf, json={
        "role": "lettura", "active": False, "expected_version": viewer["version"]
    })
    assert disabled.status_code == 200

    client.post("/api/logout", headers=admin_csrf, json={})
    blocked = client.post("/api/login", json={
        "username": "viewer_test", "password": "SyntheticViewerPass!2026"
    })
    assert blocked.status_code == 401


def test_ingress_cookie_scoped_to_addon(client):
    response = client.post("/api/login", headers={
        "X-Ingress-Path": "/api/hassio_ingress/TestToken_1/"
    }, json={"username": "admin", "password": "SyntheticTestingPass!2026"})
    assert response.status_code == 200
    cookie = response.headers["set-cookie"]
    assert "HttpOnly" in cookie
    assert "Path=/api/hassio_ingress/TestToken_1/" in cookie


def test_recovery_preserves_years_and_does_not_repeat_after_password_change(client, tmp_path):
    # Simulate a previous initialized installation that rejects the original password.
    original_csrf = signed_in(client)
    created = client.post("/api/years", headers=original_csrf, json={"code": "2027/28"})
    assert created.status_code == 200
    client.post("/api/logout", headers=original_csrf, json={})

    options_file = tmp_path / "options.json"
    options = json.loads(options_file.read_text(encoding="utf-8"))
    options["admin_recovery_password"] = "SyntheticRecoveryPass!2026"
    options_file.write_text(json.dumps(options), encoding="utf-8")

    import app.main as main
    main.startup()  # Simulates an add-on restart with its unchanged persistent /data.

    old = client.post("/api/login", json={
        "username": "admin", "password": "SyntheticTestingPass!2026"
    })
    assert old.status_code == 401
    recovered = signed_in(client, password="SyntheticRecoveryPass!2026")
    assert any(row["code"] == "2027/28" for row in client.get("/api/years").json())

    # Protect user changes: same recovery option left in place must not reapply.
    update = client.post("/api/account/password", headers=recovered, json={
        "current_password": "SyntheticRecoveryPass!2026",
        "new_password": "SyntheticPermanentPass!2026"
    })
    assert update.status_code == 200, update.text
    client.post("/api/logout", headers=recovered, json={})
    main.startup()
    signed_in(client, password="SyntheticPermanentPass!2026")
    assert any(row["code"] == "2027/28" for row in client.get("/api/years").json())


def synthetic_xlsx():
    """Build tiny fixture entirely from synthetic cell values, no real data."""
    import io
    import zipfile
    xmls = {
        "[Content_Types].xml": """<?xml version="1.0" encoding="utf-8"?>
        <Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
        <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
        <Default Extension="xml" ContentType="application/xml"/>
        <Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>
        <Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
        </Types>""",
        "_rels/.rels": """<?xml version="1.0" encoding="utf-8"?>
        <Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
        <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>
        </Relationships>""",
        "xl/workbook.xml": """<?xml version="1.0" encoding="utf-8"?>
        <workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"
        xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
        <sheets><sheet name="Sintetico" sheetId="1" r:id="rId1"/></sheets></workbook>""",
        "xl/_rels/workbook.xml.rels": """<?xml version="1.0" encoding="utf-8"?>
        <Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
        <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>
        </Relationships>""",
        "xl/worksheets/sheet1.xml": """<?xml version="1.0" encoding="utf-8"?>
        <worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
        <sheetData><row r="1"><c r="A1" t="inlineStr"><is><t>SSD</t></is></c>
        <c r="B1" t="inlineStr"><is><t>Docente fittizio</t></is></c></row>
        <row r="2"><c r="A2" t="inlineStr"><is><t>SSD-X</t></is></c>
        <c r="B2" t="inlineStr"><is><t>Persona TEST</t></is></c></row>
        </sheetData></worksheet>""",
    }
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, contents in xmls.items():
            archive.writestr(name, contents)
    return buffer.getvalue()


def test_import_retains_file_privately_and_rejects_duplicate(client, tmp_path):
    csrf = signed_in(client)
    fixture = synthetic_xlsx()
    report = client.post(
        "/api/years/1/imports",
        headers=csrf,
        data={"kind": "offerta", "test_data_only": "true"},
        files={"source": ("test-synthetic.xlsx", fixture, "application/octet-stream")},
    )
    assert report.status_code == 200, report.text
    assert report.json()["status"] == "acquisito_da_mappare"
    assert any(sheet["name"] == "Sintetico" for sheet in report.json()["sheets"])
    listed = client.get("/api/years/1/imports")
    assert listed.status_code == 200
    assert len(listed.json()) == 1
    private_files = list((tmp_path / "sources").glob("source_*.xlsx"))
    assert len(private_files) == 1

    duplicate = client.post(
        "/api/years/1/imports", headers=csrf, data={"kind": "offerta", "test_data_only": "true"},
        files={"source": ("test-synthetic.xlsx", fixture, "application/octet-stream")},
    )
    assert duplicate.status_code == 409
    assert len(list((tmp_path / "sources").glob("source_*.xlsx"))) == 1

    invalid = client.post(
        "/api/years/1/imports", headers=csrf, data={"kind": "docenti", "test_data_only": "true"},
        files={"source": ("fake.xls", b"not-really-an-excel-file", "application/octet-stream")},
    )
    assert invalid.status_code == 422


def test_archive_reset_requires_admin_password_and_text(client, tmp_path):
    csrf = signed_in(client)
    fixture = synthetic_xlsx()
    added = client.post(
        "/api/years/1/imports", headers=csrf, data={"kind": "docenti", "test_data_only": "true"},
        files={"source": ("fake-staff.xlsx", fixture, "application/octet-stream")},
    )
    assert added.status_code == 200, added.text

    wrong = client.post("/api/admin/archive/reset", headers=csrf, json={
        "scope": "year", "year_id": 1,
        "confirmation": "AZZERA 2026/27", "password": "wrong"
    })
    assert wrong.status_code == 403
    wrong_phrase = client.post("/api/admin/archive/reset", headers=csrf, json={
        "scope": "year", "year_id": 1,
        "confirmation": "AZZERA", "password": "SyntheticTestingPass!2026"
    })
    assert wrong_phrase.status_code == 422

    cleared = client.post("/api/admin/archive/reset", headers=csrf, json={
        "scope": "year", "year_id": 1,
        "confirmation": "AZZERA 2026/27", "password": "SyntheticTestingPass!2026"
    })
    assert cleared.status_code == 200, cleared.text
    assert client.get("/api/years/1/imports").json() == []
    assert list((tmp_path / "sources").iterdir()) == []
    # Users and the selected academic year survive the reset.
    assert any(x["code"] == "2026/27" for x in client.get("/api/years").json())
    assert any(x["username"] == "admin" for x in client.get("/api/users").json())


def test_reset_all_keeps_accounts_and_initial_year(client):
    csrf = signed_in(client)
    client.post("/api/years", headers=csrf, json={"code": "2027/28"})
    cleared = client.post("/api/admin/archive/reset", headers=csrf, json={
        "scope": "all", "confirmation": "AZZERA ARCHIVIO",
        "password": "SyntheticTestingPass!2026"
    })
    assert cleared.status_code == 200, cleared.text
    assert [x["code"] for x in client.get("/api/years").json()] == ["2026/27"]
    assert len(client.get("/api/users").json()) == 1


def test_theme_and_import_controls_exist(client):
    html = client.get("/").text
    css = client.get("/static/site.css").text
    js = client.get("/static/site.js").text
    assert 'id="import-form"' in html
    assert 'id="archive-reset-form"' in html
    assert 'data-theme-toggle' in html
    assert ':root[data-theme="dark"]' in css
    assert 'localStorage.setItem("didaup-theme"' in js


def test_source_mapping_preview_draft_and_concurrency(client):
    csrf = signed_in(client)
    fake = synthetic_xlsx()
    imported = client.post(
        "/api/years/1/imports", headers=csrf, data={
            "kind": "offerta", "test_data_only": "true"
        },
        files={"source": ("synthetic.xlsx", fake, "application/octet-stream")},
    )
    assert imported.status_code == 200, imported.text
    source_id = imported.json()["id"]
    metadata = client.get(f"/api/imports/{source_id}/mapping")
    assert metadata.status_code == 200, metadata.text
    assert metadata.json()["mapping"] is None
    assert any(field["key"] == "ssd_insegnamento_nuovo"
               for field in metadata.json()["available_fields"])

    preview = client.get(f"/api/imports/{source_id}/preview", params={
        "sheet_name": "Sintetico", "header_row": 1
    })
    assert preview.status_code == 200, preview.text
    assert preview.json()["columns"][0]["label"] == "SSD"
    assert preview.json()["columns"][1]["label"] == "Docente fittizio"

    saved = client.put(f"/api/imports/{source_id}/mapping", headers=csrf, json={
        "sheet_name": "Sintetico", "header_row": 1,
        "assigned": {"ssd_insegnamento_nuovo": 0, "docente_nome": 1},
        "expected_version": 0
    })
    assert saved.status_code == 200, saved.text
    assert saved.json()["status"] == "bozza_da_verificare"
    assert saved.json()["version"] == 1
    assert any("CdS" in message for message in saved.json()["warnings"])

    stale = client.put(f"/api/imports/{source_id}/mapping", headers=csrf, json={
        "sheet_name": "Sintetico", "header_row": 1,
        "assigned": {"ssd_insegnamento_nuovo": 0},
        "expected_version": 0
    })
    assert stale.status_code == 409

    duplicate_index = client.put(f"/api/imports/{source_id}/mapping", headers=csrf, json={
        "sheet_name": "Sintetico", "header_row": 1,
        "assigned": {"ssd_insegnamento_nuovo": 0, "docente_nome": 0},
        "expected_version": 1
    })
    assert duplicate_index.status_code == 422

    invalid_column = client.put(f"/api/imports/{source_id}/mapping", headers=csrf, json={
        "sheet_name": "Sintetico", "header_row": 1,
        "assigned": {"ssd_insegnamento_nuovo": 13},
        "expected_version": 1
    })
    assert invalid_column.status_code == 422
    assert client.get("/api/years/1/imports").json()[0]["mapping_status"] == "bozza_da_verificare"


def test_mapping_deleted_with_archive_but_account_retained(client):
    csrf = signed_in(client)
    imported = client.post(
        "/api/years/1/imports", headers=csrf,
        data={"kind": "offerta", "test_data_only": "true"},
        files={"source": ("synthetic.xlsx", synthetic_xlsx(), "application/octet-stream")}
    )
    assert imported.status_code == 200
    import_id = imported.json()["id"]
    assert client.put(f"/api/imports/{import_id}/mapping", headers=csrf, json={
        "sheet_name": "Sintetico", "header_row": 1,
        "assigned": {"ssd_insegnamento_nuovo": 0},
        "expected_version": 0
    }).status_code == 200
    assert client.post("/api/admin/archive/reset", headers=csrf, json={
        "scope": "year", "year_id": 1,
        "confirmation": "AZZERA 2026/27", "password": "SyntheticTestingPass!2026"
    }).status_code == 200
    assert client.get(f"/api/imports/{import_id}/mapping").status_code == 404
    assert len(client.get("/api/users").json()) == 1



def test_source_headers_recognized_without_output_variation_fields():
    from app.column_mapping import (
        OFFER_HEADER_TO_FIELD, OUTPUT_PROPOSAL_HEADERS,
        suggest_fields, evaluate_mapping,
    )

    # Source report layout from labels only: no teacher or assignment data.
    headers = list(OFFER_HEADER_TO_FIELD.keys())
    assert len(headers) == 36
    result = suggest_fields(headers, "offerta")
    assert result["matched"] == 36
    assert not result["ambiguous"]
    assert result["output_proposal_headers"] == ["Nuovo docente", "Ore", "Note"]
    assert not any(key.startswith("proposta_") for key in result["assigned"])
    assert not any(label in OFFER_HEADER_TO_FIELD for label in
                   ("NUOVO DOCENTE", "ORE", "NOTE"))
    assert result["assigned"]["ore_previste"] == headers.index("TOT ORE PREVISTE")
    assert result["assigned"]["ore_prevlez"] == headers.index("OREPREVLEZ")
    assert result["assigned"]["ore_effettive_totali"] == headers.index("TOT ORE EFFETTIVE")
    assert result["assigned"]["ssd_insegnamento_originale"] == headers.index("SSD INSEGNAMENTO")
    assert result["assigned"]["scuola"] == headers.index("SCUOLA")
    assert result["assigned"]["dipartimento"] == headers.index("DIPARTIMENTO DI RIFERIMENTO")
    assert "ssd_insegnamento_vecchio" not in result["assigned"]
    assert "ssd_insegnamento_nuovo" not in result["assigned"]
    assert not any("SSD dell'insegnamento" in x
                   for x in evaluate_mapping("offerta", result["assigned"]))


def test_duplicate_source_headers_require_manual_decision():
    from app.column_mapping import suggest_fields
    result = suggest_fields(["CODICE CORSO", "CDS", " codice  corso "], "offerta")
    assert result["matched"] == 1
    assert result["ambiguous"]["cds_codice"] == [0, 2]
    assert "cds_codice" not in result["assigned"]
    assert result["assigned"]["cds_nome"] == 1
    assert result["output_proposal_headers"] == ["Nuovo docente", "Ore", "Note"]


def make_synthetic_header_workbook():
    """Extend an existing tiny synthetic workbook with user-supplied header names."""
    import io
    import zipfile
    from xml.sax.saxutils import escape
    from app.column_mapping import OFFER_HEADER_TO_FIELD

    source = synthetic_xlsx()
    original = io.BytesIO(source)
    output = io.BytesIO()
    headers = list(OFFER_HEADER_TO_FIELD.keys())
    cells = []
    for i, label in enumerate(headers):
        # Only synthetic headers and source-level metadata; no real student or teacher data.
        col = ""
        x = i + 1
        while x:
            x, rem = divmod(x - 1, 26)
            col = chr(65 + rem) + col
        cells.append(
            '<c r="' + col + '1" t="inlineStr"><is><t>' +
            escape(label) + '</t></is></c>'
        )
    worksheet_xml = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        '<sheetData><row r="1">' + "".join(cells) +
        '</row><row r="2"><c r="A2" t="inlineStr"><is><t>TEST-SEDE</t></is></c></row></sheetData>'
        '</worksheet>'
    )
    with zipfile.ZipFile(original, "r") as infile, zipfile.ZipFile(output, "w") as outfile:
        for item in infile.infolist():
            data = (worksheet_xml.encode("utf-8") if item.filename == "xl/worksheets/sheet1.xml"
                    else infile.read(item.filename))
            outfile.writestr(item.filename, data)
    return output.getvalue()


def test_auto_mapping_reads_synthetic_template_without_saving_automatically(client):
    csrf = signed_in(client)
    fixture = make_synthetic_header_workbook()
    imported = client.post(
        "/api/years/1/imports", headers=csrf,
        data={"kind": "offerta", "test_data_only": "true"},
        files={"source": ("synthetic-layout.xlsx", fixture, "application/octet-stream")},
    )
    assert imported.status_code == 200, imported.text
    import_id = imported.json()["id"]
    guessed = client.get(f"/api/imports/{import_id}/autodetect")
    assert guessed.status_code == 200, guessed.text
    result = guessed.json()
    assert result["recognized"] is True
    assert result["matched"] == 36
    assert result["output_proposal_headers"] == ["Nuovo docente", "Ore", "Note"]
    assert "proposta_docente" not in result["assigned"]
    assert result["header_row"] == 1
    # Recognition is just a suggestion: original data and saved mapping untouched.
    record = client.get(f"/api/imports/{import_id}/mapping").json()
    assert record["mapping"] is None
    assert record["available_fields"]
