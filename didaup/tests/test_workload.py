"""Workload rules: synthetic data only, no historic effective hours trusted."""
from __future__ import annotations

import hashlib
import io
import json
from pathlib import Path
from zipfile import ZipFile

import pytest
from python_calamine import CalamineWorkbook

from app.workload import (
    validate_rules, apply_workload, WorkloadRuleError, source_choices,
    workload_cap_applied,
)
from app.department_workbooks import build_five_workbooks, _prepare, WorkbookGenerationError
from test_department_workbooks import make_source, referent_names


def rule(*, tipologia="", cds="", taf="", mode="percentuale", value="50"):
    return {"tipologia": tipologia, "cds": cds, "taf": taf, "mode": mode, "value": value}


def test_workload_priority_percentage_fixed_and_rounding():
    rules = validate_rules([
        rule(value="25"),
        rule(cds="SYN-A", value="33.33"),
        rule(cds="SYN-A", taf="C", value="7.5", mode="fissa"),
    ])
    assert apply_workload(30, "tipo", "SYN-B", "C", rules) == (7.5, 0, None)
    assert apply_workload(30, "tipo", "SYN-A", "A", rules) == (10.0, 1, None)
    assert apply_workload(30, "tipo", "SYN-A", "C", rules) == (7.5, 2, None)
    assert apply_workload(20, "tipo", "SYN-A", "C", validate_rules([rule(value="33.33")])) == (
        6.67, 0, None
    )
    assert apply_workload(0, "x", "y", "z", []) == (0, None, None)


def test_workload_rules_reject_duplicate_and_conflict():
    with pytest.raises(WorkloadRuleError, match="duplicata"):
        validate_rules([rule(cds=" SYN-A "), rule(cds="syn-a")])
    with pytest.raises(WorkloadRuleError, match="valore"):
        validate_rules([rule(value="-5")])
    with pytest.raises(WorkloadRuleError, match="valore"):
        validate_rules([rule(value="1+1")])
    rules = validate_rules([rule(cds="SYN-A"), rule(taf="C")])
    conflict = apply_workload(20, "X", "SYN-A", "C", rules)[2]
    assert "Conflitto" in conflict
    assert "regole 1, 2" in conflict


def test_fixed_quota_above_planned_hours_is_automatically_capped():
    rules = validate_rules([rule(mode="fissa", value="12")])
    assert apply_workload(10, "A", "B", "C", rules) == (10.0, 0, None)
    assert workload_cap_applied(10, "A", "B", "C", rules) is True
    assert apply_workload("", "A", "B", "C", rules)[2].startswith(
        "TOT ORE PREVISTE mancante"
    )
    assert workload_cap_applied("", "A", "B", "C", rules) is False
    assert apply_workload("15", "A", "B", "C", rules) == (12.0, 0, None)
    assert workload_cap_applied(15, "A", "B", "C", rules) is False


def test_percentage_above_planned_hours_is_automatically_capped():
    rules = validate_rules([rule(mode="percentuale", value="150")])
    assert apply_workload(10, "A", "B", "C", rules) == (10.0, 0, None)
    assert workload_cap_applied(10, "A", "B", "C", rules) is True
    exactly_one_hundred = validate_rules([rule(mode="percentuale", value="100")])
    assert apply_workload(10, "A", "B", "C", exactly_one_hundred) == (10.0, 0, None)
    assert workload_cap_applied(10, "A", "B", "C", exactly_one_hundred) is False


def test_workload_applied_only_to_retained_lines_in_all_five(tmp_path):
    src = tmp_path / "history.xlsx"
    assigned = make_source(src)
    assigned.pop("ore_effettive_totali")
    original_hash = hashlib.sha256(src.read_bytes()).hexdigest()
    rules = validate_rules([
        rule(value="25"),
        rule(cds="SYN-A", taf="TAF-SINTETICO", value="150"),
        rule(cds="SYN-B", mode="fissa", value="12"),
    ])
    bundle, info = build_five_workbooks(
        src, original_hash, "Offerta sintetica", 1, assigned,
        "2026/27", workload_rules=rules,
    )
    assert info["workload"]["rows_calculated"] == 4
    assert info["workload"]["total_effective_hours"] == 38
    assert info["workload"]["rows_without_rule"] == 0
    assert info["workload"]["rows_capped_to_planned_hours"] == 3
    assert info["workload"]["capped_to_planned_hours_examples"] == [
        {"excel_row": 2, "rule_number": 2, "planned_hours": "20",
         "effective_hours": "20"},
        {"excel_row": 3, "rule_number": 2, "planned_hours": "10",
         "effective_hours": "10"},
        {"excel_row": 5, "rule_number": 3, "planned_hours": "8",
         "effective_hours": "8"},
    ]
    assert hashlib.sha256(src.read_bytes()).hexdigest() == original_hash
    with ZipFile(io.BytesIO(bundle)) as archive:
        files = referent_names(archive)
        assert len(files) == 5
        assert len(set(archive.read(name) for name in files)) == 1
        output = tmp_path / "output.xlsx"
        output.write_bytes(archive.read(files[0]))
    values = CalamineWorkbook.from_path(output).get_sheet_by_name("Proposte SSD").to_python(
        skip_empty_area=False
    )
    assert [line[28] for line in values[6:10]] == [20, 10, 0, 8]


def test_workload_ambiguous_rules_block_generation_but_preview_reports(tmp_path):
    src = tmp_path / "conflict.xlsx"
    assigned = make_source(src)
    digest = hashlib.sha256(src.read_bytes()).hexdigest()
    rules = validate_rules([rule(cds="SYN-A"), rule(taf="TAF-SINTETICO")])
    with pytest.raises(WorkbookGenerationError, match="Conflitto"):
        build_five_workbooks(
            src, digest, "Offerta sintetica", 1, assigned, "2026/27",
            workload_rules=rules
        )
    snapshot = _prepare(
        src, digest, "Offerta sintetica", 1, assigned, "2026/27",
        set(), None, None, rules, False
    )
    assert snapshot[-1]["blocked"]
    assert snapshot[-1]["errors"][0]["excel_row"] == 2
    assert snapshot[-1]["errors"][0]["reason"] == (
        "Conflitto tra regole 1, 2 con la stessa specificità"
    )
    assert snapshot[-1]["conflict_pairs"] == [{
        "rules": [1, 2], "rows": 3, "examples": [2, 3, 4]
    }]


def test_workload_choices_follow_exact_source_columns(tmp_path):
    src = tmp_path / "values.xlsx"
    mapping = make_source(src)
    result = source_choices(src, "Offerta sintetica", 1, mapping)
    assert {x["code"] for x in result["cds"]} == {"SYN-A", "SYN-B"}
    assert result["taf"] == ["TAF-SINTETICO"]
    assert result["mapped"]["tot_ore_previste"]
    assert result["mapped"]["taf"]



def test_typology_cds_taf_combined_priority_and_choices(tmp_path):
    src = tmp_path / "typed.xlsx"
    assigned = make_source(src, with_tipologia=True)
    assigned.pop("ore_effettive_totali")
    digest = hashlib.sha256(src.read_bytes()).hexdigest()
    lookup = source_choices(src, "Offerta sintetica", 1, assigned)
    assert lookup["mapped"]["tipologia"]
    assert lookup["tipologie"] == ["Laurea", "Magistrale"]
    configured = validate_rules([
        rule(value="10"),
        rule(tipologia="Laurea", value="20"),
        rule(tipologia="Laurea", cds="SYN-A", taf="TAF-SINTETICO", value="80"),
    ])
    payload, summary = build_five_workbooks(
        src, digest, "Offerta sintetica", 1, assigned, "2026/27",
        workload_rules=configured,
    )
    assert summary["workload"]["per_rule_rows"] == [1, 0, 3]
    with ZipFile(io.BytesIO(payload)) as archive:
        result = tmp_path / "typed-export.xlsx"
        result.write_bytes(archive.read(referent_names(archive)[0]))
    lines = CalamineWorkbook.from_path(result).get_sheet_by_name(
        "Proposte SSD"
    ).to_python(skip_empty_area=False)
    assert [row[28] for row in lines[6:10]] == [16, 8, 0, 0.8]



# API journey: one annual profile, mapped input without effective hours,
# preview, generation and byte-identical five-file ZIP.
from test_app import client, signed_in


def test_workload_api_profile_preview_and_export(client, tmp_path):
    source = tmp_path / "synthetic-workload.xlsx"
    mapping = make_source(source)
    mapping.pop("ore_effettive_totali")
    csrf = signed_in(client)
    uploaded = client.post(
        "/api/years/1/imports", headers=csrf,
        data={"kind": "offerta", "test_data_only": "true"},
        files={"source": ("synthetic-workload.xlsx", source.read_bytes(),
                          "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
    )
    assert uploaded.status_code == 200, uploaded.text
    source_id = uploaded.json()["id"]
    saved = client.put(
        f"/api/imports/{source_id}/mapping", headers=csrf,
        json={"sheet_name": "Offerta sintetica", "header_row": 1,
              "assigned": mapping, "expected_version": 0},
    )
    assert saved.status_code == 200, saved.text
    empty = client.get("/api/years/1/workload")
    assert empty.status_code == 200
    assert empty.json()["version"] == 0
    profile_rules = [rule(value="50")]
    changed = client.put(
        "/api/years/1/workload", headers=csrf,
        json={"expected_version": 0, "rules": profile_rules},
    )
    assert changed.status_code == 200, changed.text
    assert changed.json()["version"] == 1
    assert client.put(
        "/api/years/1/workload", headers=csrf,
        json={"expected_version": 0, "rules": []},
    ).status_code == 409
    source_values = client.get(
        "/api/years/1/workload/choices", params={"import_id": source_id}
    )
    assert source_values.status_code == 200, source_values.text
    assert source_values.json()["mapped"]["tot_ore_previste"]
    preview = client.get(
        "/api/years/1/workload/preview", params={"import_id": source_id}
    )
    assert preview.status_code == 200, preview.text
    assert preview.json()["rows_calculated"] == 4
    assert preview.json()["total_effective_hours"] == 19
    assert preview.json()["blocked"] is False
    output = client.post(
        "/api/years/1/department-workbooks", headers=csrf,
        json={"import_id": source_id},
    )
    assert output.status_code == 200, output.text
    assert output.json()["workload"]["total_effective_hours"] == 19
    archive = client.get("/" + output.json()["download_url"])
    assert archive.status_code == 200
    with ZipFile(io.BytesIO(archive.content)) as z:
        files = referent_names(z)
        assert len(files) == 5 and len(z.namelist()) == 6
        assert len(set(z.read(name) for name in files)) == 1
        path = tmp_path / "calculated.xlsx"
        path.write_bytes(z.read(files[0]))
    rows = CalamineWorkbook.from_path(path).get_sheet_by_name("Proposte SSD").to_python(
        skip_empty_area=False
    )
    assert [line[28] for line in rows[6:10]] == [10, 5, 0, 4]



def test_multiselection_or_inside_each_filter_and_and_between_filters():
    rules = validate_rules([
        rule(tipologia=["Laurea", "Magistrale"], cds=["SYN-A", "SYN-B"],
             taf=["A", "C"], mode="percentuale", value="40"),
    ])
    assert rules[0]["tipologia"] == ["Laurea", "Magistrale"]
    assert rules[0]["cds"] == ["SYN-A", "SYN-B"]
    assert rules[0]["taf"] == ["A", "C"]
    assert apply_workload(20, "Laurea", "SYN-B", "C", rules) == (8.0, 0, None)
    assert apply_workload(20, "Magistrale", "SYN-A", "A", rules) == (8.0, 0, None)
    assert apply_workload(20, "Altro", "SYN-A", "C", rules) == (20.0, None, None)
    assert apply_workload(20, "Laurea", "SYN-C", "C", rules) == (20.0, None, None)
    assert apply_workload(20, "Laurea", "SYN-A", "B", rules) == (20.0, None, None)


def test_multiselection_duplicate_sets_and_values_are_rejected():
    with pytest.raises(WorkloadRuleError, match="duplicata"):
        validate_rules([
            rule(cds=["A", "B"], taf=["C", "D"]),
            rule(cds=[" b ", " a "], taf=["d", "c"]),
        ])
    with pytest.raises(WorkloadRuleError, match="duplicato"):
        validate_rules([rule(cds=["A", " a "])])
    with pytest.raises(WorkloadRuleError, match="vuota"):
        validate_rules([rule(taf=[""])])
    with pytest.raises(WorkloadRuleError, match="non valido"):
        validate_rules([rule(cds=[10])])
    with pytest.raises(WorkloadRuleError, match="non valido"):
        validate_rules([rule(taf={"not": "a list"})])


def test_multiselect_specificity_and_overlap_never_silently_sum():
    rules = validate_rules([
        rule(value="10"),
        rule(cds=["SYN-A", "SYN-B"], value="50"),
        rule(cds=["SYN-A", "SYN-B"], taf=["A", "B"], mode="fissa", value="5"),
    ])
    assert apply_workload(20, "X", "SYN-B", "B", rules) == (5.0, 2, None)
    assert apply_workload(20, "X", "SYN-A", "C", rules) == (10.0, 1, None)
    assert apply_workload(20, "X", "SYN-C", "A", rules) == (2.0, 0, None)

    conflicting = validate_rules([
        rule(cds=["SYN-A", "SYN-B"], value="50"),
        rule(taf=["A", "B"], value="20"),
    ])
    assert "Conflitto" in apply_workload(20, "X", "SYN-B", "B", conflicting)[2]


def test_previous_scalar_rules_migrate_to_multiselect_lists_without_changing_result():
    legacy = rule(cds="SYN-A", taf="C", value="80")
    converted = validate_rules([legacy])
    assert converted[0]["cds"] == ["SYN-A"]
    assert converted[0]["taf"] == ["C"]
    assert converted[0]["tipologia"] == []
    assert apply_workload(10, "X", "SYN-A", "C", converted) == (8.0, 0, None)


def test_multi_cds_rule_applied_in_all_five_excel_exports(tmp_path):
    source = tmp_path / "multi-cds.xlsx"
    mapping = make_source(source)
    mapping.pop("ore_effettive_totali")
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    rules = validate_rules([
        rule(cds=["SYN-A", "SYN-B"], taf=["TAF-SINTETICO"], value="50")
    ])
    packed, summary = build_five_workbooks(
        source, digest, "Offerta sintetica", 1, mapping, "2026/27",
        workload_rules=rules,
    )
    assert summary["workload"]["per_rule_rows"] == [4]
    assert summary["workload"]["total_effective_hours"] == 19
    with ZipFile(io.BytesIO(packed)) as archive:
        names = referent_names(archive)
        assert len(names) == 5
        assert len({archive.read(name) for name in names}) == 1
        output = tmp_path / "multi-output.xlsx"
        output.write_bytes(archive.read(names[0]))
    rows = CalamineWorkbook.from_path(output).get_sheet_by_name(
        "Proposte SSD"
    ).to_python(skip_empty_area=False)
    assert [row[28] for row in rows[6:10]] == [10, 5, 0, 4]


def test_workload_multiselect_controls_are_visible_in_section(client):
    page = client.get("/").text
    js = client.get("/static/workload.js").text
    for key in ("typologia", "cds", "taf"):
        for part in ("toggle", "panel", "search", "options", "all", "clear", "count"):
            assert f'id="workload-{key}-{part}"' in page
    assert "Seleziona visibili" in page
    assert "Deseleziona tutte" in page
    assert "filteredOptions" in js and "groups.typologia.selected" in js


def test_workload_api_persists_multiselections_and_reloads_them(client):
    csrf = signed_in(client)
    saved = client.put(
        "/api/years/1/workload", headers=csrf,
        json={"expected_version": 0, "rules": [
            rule(tipologia=["Magistrale", "Laurea"], cds=["SYN-B", "SYN-A"],
                 taf=["B", "A"], mode="percentuale", value="35")
        ]},
    )
    assert saved.status_code == 200, saved.text
    expected = saved.json()["rules"][0]
    assert expected["tipologia"] == ["Laurea", "Magistrale"]
    assert expected["cds"] == ["SYN-A", "SYN-B"]
    assert expected["taf"] == ["A", "B"]
    current = client.get("/api/years/1/workload")
    assert current.status_code == 200
    assert current.json()["rules"] == [expected]
    assert current.json()["version"] == 1


def test_nd_mode_is_explicit_text_and_never_zero_hours():
    checked = validate_rules([
        rule(cds=["SYN-A", "SYN-B"], taf=["TAF-X"], mode="non_disponibile", value="")
    ])
    assert checked[0]["value"] == "N.D."
    assert apply_workload(20, "Qualsiasi", "SYN-A", "TAF-X", checked) == (
        "N.D.", 0, None
    )
    # N.D. is deliberate even when planned hours are blank or malformed.
    assert apply_workload("", "Qualsiasi", "SYN-A", "TAF-X", checked) == (
        "N.D.", 0, None
    )
    assert apply_workload("valore errato", "Qualsiasi", "SYN-A", "TAF-X", checked) == (
        "N.D.", 0, None
    )
    # Unmatched activities retain their planned hours rather than becoming N.D.
    assert apply_workload(23, "Qualsiasi", "SYN-C", "TAF-X", checked) == (
        23.0, None, None
    )
    with pytest.raises(WorkloadRuleError, match="N.D."):
        validate_rules([rule(mode="non_disponibile", value="10")])
    with pytest.raises(WorkloadRuleError):
        validate_rules([rule(mode="non_disponibile", value="Non applicabile")])


def test_nd_is_written_as_excel_text_in_all_five_files_not_counted(tmp_path):
    source = tmp_path / "nd-synthetic.xlsx"
    assigned = make_source(source)
    assigned.pop("ore_effettive_totali")
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    rules = validate_rules([
        rule(cds=["SYN-A"], mode="non_disponibile", value="N.D."),
    ])
    package, info = build_five_workbooks(
        source, digest, "Offerta sintetica", 1, assigned, "2026/27",
        workload_rules=rules,
    )
    assert info["workload"]["rows_not_available"] == 3
    assert info["workload"]["rows_calculated"] == 3
    assert info["workload"]["rows_using_planned_hours"] == 1
    assert info["workload"]["total_effective_hours"] == 8
    assert info["workload"]["error_count"] == 0
    with ZipFile(io.BytesIO(package)) as archive:
        names = referent_names(archive)
        assert len(names) == 5
        assert len(set(archive.read(name) for name in names)) == 1
        output = tmp_path / "nd-output.xlsx"
        output.write_bytes(archive.read(names[0]))
    rows = CalamineWorkbook.from_path(output).get_sheet_by_name(
        "Proposte SSD"
    ).to_python(skip_empty_area=False)
    assert [row[28] for row in rows[6:10]] == ["N.D.", "N.D.", "N.D.", 8]
    # Source still untouched.
    assert hashlib.sha256(source.read_bytes()).hexdigest() == digest


def test_nd_mode_is_visible_in_user_interface(client):
    html = client.get("/").text
    js = client.get("/static/workload.js").text
    assert '<option value="non_disponibile">' in html
    assert 'id="workload-count-nd"' in html
    assert 'id="workload-value-wrapper"' in html
    assert 'workload-count-nd' in js
    assert 'input.required = !unavailable' in js


def _upload_mapped_synthetic_report(client, csrf, path, mapping):
    uploaded = client.post(
        "/api/years/1/imports", headers=csrf,
        data={"kind": "offerta", "test_data_only": "true"},
        files={"source": (
            "offer-only-synthetic.xlsx", path.read_bytes(),
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )},
    )
    assert uploaded.status_code == 200, uploaded.text
    import_id = uploaded.json()["id"]
    mapped = client.put(
        f"/api/imports/{import_id}/mapping", headers=csrf,
        json={"sheet_name": "Offerta sintetica", "header_row": 1,
              "assigned": mapping, "expected_version": 0},
    )
    assert mapped.status_code == 200, mapped.text
    return import_id


def _cohort_set_inclusion(client, csrf, code, year, included):
    created = client.post("/api/years/1/cohorts", headers=csrf, json={
        "course_code": code,
        "course_name": "Corso sintetico",
        "campus": "Sede TEST",
        "study_year": year,
    })
    assert created.status_code == 200, created.text
    if included:
        return created.json()["id"]
    changed = client.patch(
        f"/api/cohorts/{created.json()['id']}", headers=csrf,
        json={"included": False, "reason": "Esclusione sintetica",
              "expected_version": 1},
    )
    assert changed.status_code == 200, changed.text
    return created.json()["id"]


def test_workload_selectors_include_only_rows_retained_in_five_xlsx(client, tmp_path):
    source = tmp_path / "offer-synthetic.xlsx"
    mapping = make_source(
        source, with_tipologia=True,
        taf_by_course={"SYN-A": "TAF-A", "SYN-B": "TAF-B"},
    )
    csrf = signed_in(client)
    import_id = _upload_mapped_synthetic_report(client, csrf, source, mapping)
    url = f"/api/years/1/workload/choices?import_id={import_id}"

    before = client.get(url)
    assert before.status_code == 200, before.text
    assert {x["code"] for x in before.json()["cds"]} == {"SYN-A", "SYN-B"}
    assert before.json()["taf"] == ["TAF-A", "TAF-B"]
    assert before.json()["tipologie"] == ["Laurea", "Magistrale"]
    _cohort_set_inclusion(client, csrf, "SYN-B", 2, False)

    after = client.get(url)
    assert after.status_code == 200, after.text
    data = after.json()
    assert [x["code"] for x in data["cds"]] == ["SYN-A"]
    assert data["taf"] == ["TAF-A"]
    assert data["tipologie"] == ["Laurea"]
    assert data["rows_in_scope"] == 3
    assert data["excluded_rows"] == 1
    # Verify against what was ACTUALLY generated, not just the source filter.
    generated = client.post(
        "/api/years/1/department-workbooks", headers=csrf,
        json={"import_id": import_id},
    )
    assert generated.status_code == 200, generated.text
    assert generated.json()["reconciliation"]["included_in_each_workbook"] == 3
    assert generated.json()["reconciliation"]["excluded_in_internal_register"] == 1
    download = client.get("/" + generated.json()["download_url"])
    assert download.status_code == 200, download.text
    with ZipFile(io.BytesIO(download.content)) as archive:
        copies = referent_names(archive)
        assert len(copies) == 5
        assert len({archive.read(name) for name in copies}) == 1
        out = tmp_path / "actual.xlsx"
        out.write_bytes(archive.read(copies[0]))
    rows = CalamineWorkbook.from_path(out).get_sheet_by_name(
        "Proposte SSD"
    ).to_python(skip_empty_area=False)[6:]
    assert len(rows) == 3
    assert {row[1] for row in rows} == {"SYN-A"}
    assert {row[16] for row in rows} == {"TAF-A"}

    # Once an annuality is explicitly re-included, it returns to the selector.
    excluded_cohort = next(
        x for x in client.get("/api/years/1/cohorts").json()
        if x["course_code"] == "SYN-B"
    )
    restored = client.patch(
        f"/api/cohorts/{excluded_cohort['id']}", headers=csrf,
        json={"included": True, "expected_version": excluded_cohort["version"]},
    )
    assert restored.status_code == 200, restored.text
    again = client.get(url)
    assert again.status_code == 200
    assert {x["code"] for x in again.json()["cds"]} == {"SYN-A", "SYN-B"}
    assert again.json()["rows_in_scope"] == 4


def test_workload_selectors_empty_when_all_cohorts_excluded(client, tmp_path):
    source = tmp_path / "all-excluded.xlsx"
    mapping = make_source(source, with_tipologia=True)
    csrf = signed_in(client)
    import_id = _upload_mapped_synthetic_report(client, csrf, source, mapping)
    _cohort_set_inclusion(client, csrf, "SYN-A", 2, False)
    _cohort_set_inclusion(client, csrf, "SYN-B", 2, False)
    choices = client.get(f"/api/years/1/workload/choices?import_id={import_id}")
    assert choices.status_code == 200, choices.text
    assert choices.json()["rows_in_scope"] == 0
    assert choices.json()["excluded_rows"] == 4
    assert choices.json()["cds"] == []
    assert choices.json()["tipologie"] == []
    assert choices.json()["taf"] == []


def test_workload_choices_keep_mixed_annuality_rows_that_export_keeps(client, tmp_path):
    source = tmp_path / "mixed-annuality.xlsx"
    mapping = make_source(
        source, with_tipologia=True, annualities_by_row={1: "1,2,3"},
        taf_by_course={"SYN-A": "TAF-A", "SYN-B": "TAF-B"},
    )
    csrf = signed_in(client)
    import_id = _upload_mapped_synthetic_report(client, csrf, source, mapping)
    _cohort_set_inclusion(client, csrf, "SYN-A", 1, False)
    _cohort_set_inclusion(client, csrf, "SYN-A", 2, True)
    _cohort_set_inclusion(client, csrf, "SYN-B", 2, False)

    choices = client.get(f"/api/years/1/workload/choices?import_id={import_id}")
    assert choices.status_code == 200, choices.text
    assert choices.json()["rows_in_scope"] == 3
    assert choices.json()["excluded_rows"] == 1
    assert choices.json()["mixed_annuality_rows_retained"] == 1
    assert [x["code"] for x in choices.json()["cds"]] == ["SYN-A"]
    assert choices.json()["taf"] == ["TAF-A"]

    generated = client.post(
        "/api/years/1/department-workbooks", headers=csrf,
        json={"import_id": import_id},
    )
    assert generated.status_code == 200, generated.text
    assert generated.json()["mixed_annuality_rows_retained"] == 1
    assert generated.json()["reconciliation"]["included_in_each_workbook"] == 3


def test_ui_keeps_excluded_historical_rule_values_outside_choices(client):
    script = client.get("/static/workload.js").text
    page = client.get("/").text
    assert "Valori della regola non presenti nelle righe incluse" in script
    assert "group.options.push({value" not in script
    assert "Selettori limitati alle " in script
    assert 'id="workload-conflict-pairs"' in page
    assert "conflict.rules" in script
    assert "Regola " in script


def test_workload_release_assets_are_versioned_to_avoid_old_cached_selectors(client):
    """Home Assistant must recognize an add-on version bump to install new code."""
    html = client.get("/").text
    from pathlib import Path
    manifest = (Path(__file__).resolve().parents[1] / "config.yaml").read_text(
        encoding="utf-8"
    )
    release = "0.1.10-alpha20"
    assert f'version: "{release}"' in manifest
    assert f'ALPHA · {release}' in html
    for asset in ("site.css", "site.js", "mapping.js", "cohort_review.js", "workload.js", "workbook_exclusions.js"):
        assert f'static/{asset}?v={release}' in html


def test_saved_rule_for_excluded_course_is_flagged_but_kept_for_admin_review(client, tmp_path):
    src = tmp_path / "saved-rule-then-excluded.xlsx"
    mapping = make_source(src, with_tipologia=True)
    csrf = signed_in(client)
    import_id = _upload_mapped_synthetic_report(client, csrf, src, mapping)
    configured = client.put(
        "/api/years/1/workload", headers=csrf,
        json={"expected_version": 0, "rules": [
            rule(cds=["SYN-B"], value="50")
        ]},
    )
    assert configured.status_code == 200, configured.text
    _cohort_set_inclusion(client, csrf, "SYN-B", 2, False)
    choices = client.get(
        f"/api/years/1/workload/choices?import_id={import_id}"
    )
    assert choices.status_code == 200, choices.text
    assert {item["code"] for item in choices.json()["cds"]} == {"SYN-A"}
    assert choices.json()["excluded_rows"] == 1
    # Rules must not be deleted just because the inclusion perimeter changed.
    stored = client.get("/api/years/1/workload")
    assert stored.status_code == 200
    assert stored.json()["rules"][0]["cds"] == ["SYN-B"]
    frontend = client.get("/static/workload.js").text
    assert "Fuori dalle righe incluse:" in frontend
    assert "unmatched_exclusion_count" in frontend
    assert "mixed_annuality_rows_retained" in frontend
    assert "group.options.push({value" not in frontend


def test_workbook_assignment_exclusions_are_saved_previewed_and_applied(client, tmp_path):
    source = tmp_path / "offer-with-assignment-titles.xlsx"
    mapping = make_source(
        source, with_tipologia=True,
        assignment_titles_by_row={
            1: "Titolo A", 2: "Titolo B", 3: "Titolo A", 4: "Titolo A",
        },
    )
    csrf = signed_in(client)
    import_id = _upload_mapped_synthetic_report(client, csrf, source, mapping)
    base = f"/api/years/1/department-workbooks/exclusions"
    loaded = client.get(base, params={"import_id": import_id})
    assert loaded.status_code == 200, loaded.text
    data = loaded.json()
    assert data["mapped"]["titoli"] is True
    assert data["rows_in_scope"] == 4
    assert data["version"] == 0
    cds_a = next(
        item["value"] for item in data["choices"]["cds"]
        if item["label"].endswith("SYN-A")
    )
    filters = {
        "titoli": ["Titolo A"],
        "tipologie": ["Laurea"],
        "cds": [cds_a],
        "sedi": ["Sede TEST"],
        "annualita": ["2"],
        "taf": ["TAF-SINTETICO"],
    }
    payload = {
        "import_id": import_id,
        "expected_version": data["version"],
        "source_sha256": data["source_sha256"],
        "mapping_version": data["mapping_version"],
        "cohort_revision": data["cohort_revision"],
        "filters": filters,
    }
    preview = client.post(base + "/preview", headers=csrf, json=payload)
    assert preview.status_code == 200, preview.text
    assert preview.json()["matched_rows"] == 2
    assert [item["excel_row"] for item in preview.json()["examples"]] == [2, 4]

    saved = client.put(base, headers=csrf, json=payload)
    assert saved.status_code == 200, saved.text
    assert saved.json()["version"] == 1
    assert saved.json()["matched_rows"] == 2

    refreshed = client.get(base, params={"import_id": import_id})
    assert refreshed.status_code == 200, refreshed.text
    assert refreshed.json()["filters"] == filters
    assert refreshed.json()["stale"] is False

    generated = client.post(
        "/api/years/1/department-workbooks", headers=csrf,
        json={"import_id": import_id},
    )
    assert generated.status_code == 200, generated.text
    assert generated.json()["excluded_by_assignment_filters"] == 2
    assert generated.json()["excluded_rows"] == 2
    assert generated.json()["reconciliation"]["included_in_each_workbook"] == 2
    assert generated.json()["reconciliation"]["excluded_in_internal_register"] == 2
    download = client.get("/" + generated.json()["download_url"])
    assert download.status_code == 200, download.text
    with ZipFile(io.BytesIO(download.content)) as archive:
        copies = referent_names(archive)
        assert len(copies) == 5
        assert len({archive.read(name) for name in copies}) == 1
        audit_names = [name for name in archive.namelist()
                       if "CONTROLLO_INTERNO" in name]
        assert len(audit_names) == 1
        audit_path = tmp_path / "assignment-exclusions-audit.xlsx"
        audit_path.write_bytes(archive.read(audit_names[0]))
    audit = CalamineWorkbook.from_path(audit_path)
    audit_rows = audit.get_sheet_by_name("Righe escluse").to_python(
        skip_empty_area=False
    )[5:]
    assert [row[32] for row in audit_rows] == [
        "Titolo A", "Titolo A"
    ]


def test_workbook_assignment_exclusions_become_stale_after_annuality_changes(client, tmp_path):
    source = tmp_path / "offer-stale-assignment-exclusions.xlsx"
    mapping = make_source(
        source, with_tipologia=True,
        assignment_titles_by_row={
            1: "Titolo A", 2: "Titolo B", 3: "Titolo A", 4: "Titolo A",
        },
    )
    csrf = signed_in(client)
    import_id = _upload_mapped_synthetic_report(client, csrf, source, mapping)
    base = "/api/years/1/department-workbooks/exclusions"
    loaded = client.get(base, params={"import_id": import_id})
    assert loaded.status_code == 200, loaded.text
    data = loaded.json()
    payload = {
        "import_id": import_id, "expected_version": 0,
        "source_sha256": data["source_sha256"],
        "mapping_version": data["mapping_version"],
        "cohort_revision": data["cohort_revision"],
        "filters": {"titoli": ["Titolo A"]},
    }
    saved = client.put(base, headers=csrf, json=payload)
    assert saved.status_code == 200, saved.text
    _cohort_set_inclusion(client, csrf, "SYN-B", 2, False)
    stale = client.get(base, params={"import_id": import_id})
    assert stale.status_code == 200, stale.text
    assert stale.json()["stale"] is True
    assert stale.json()["filters"] == {}
    generated = client.post(
        "/api/years/1/department-workbooks", headers=csrf,
        json={"import_id": import_id},
    )
    assert generated.status_code == 409
    assert "annualità precedente" in generated.json()["detail"]


def test_workbook_assignment_exclusion_ui_has_all_multiselect_facets(client):
    html = client.get("/").text
    script = client.get("/static/workbook_exclusions.js").text
    for element in (
        "workbook-exclusion-title-filter",
        "workbook-exclusion-type-filter",
        "workbook-exclusion-cds-filter",
        "workbook-exclusion-campus-filter",
        "workbook-exclusion-year-filter",
        "workbook-exclusion-taf-filter",
    ):
        assert f'id="{element}"' in html
    assert "Seleziona risultati" in html
    assert "hasUnsavedChanges" in script
    assert "filtri diversi sono combinati (AND)" in html
