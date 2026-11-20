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
