"""Workload rules: synthetic data only, no historic effective hours trusted."""
from __future__ import annotations

import hashlib
import io
from pathlib import Path
from zipfile import ZipFile

import pytest
from python_calamine import CalamineWorkbook

from app.workload import validate_rules, apply_workload, WorkloadRuleError, source_choices
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
    assert "Conflitto" in apply_workload(20, "X", "SYN-A", "C", rules)[2]


def test_missing_planned_hours_and_fixed_quota_beyond_plan_are_errors():
    rules = validate_rules([rule(mode="fissa", value="12")])
    assert "superiore" in apply_workload(10, "A", "B", "C", rules)[2]
    assert "mancante" in apply_workload("", "A", "B", "C", rules)[2]
    assert apply_workload("15", "A", "B", "C", rules) == (12.0, 0, None)


def test_workload_applied_only_to_retained_lines_in_all_five(tmp_path):
    src = tmp_path / "history.xlsx"
    assigned = make_source(src)
    assigned.pop("ore_effettive_totali")
    original_hash = hashlib.sha256(src.read_bytes()).hexdigest()
    rules = validate_rules([
        rule(value="25"),
        rule(cds="SYN-A", taf="TAF-SINTETICO", value="75"),
        rule(cds="SYN-B", mode="fissa", value="4"),
    ])
    bundle, info = build_five_workbooks(
        src, original_hash, "Offerta sintetica", 1, assigned,
        "2026/27", workload_rules=rules,
    )
    assert info["workload"]["rows_calculated"] == 4
    assert info["workload"]["total_effective_hours"] == 26.5
    assert info["workload"]["rows_without_rule"] == 0
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
    assert [line[28] for line in values[6:10]] == [15, 7.5, 0, 4]


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
    assert apply_workload(20, "Altro", "SYN-A", "C", rules) == (0, None, None)
    assert apply_workload(20, "Laurea", "SYN-C", "C", rules) == (0, None, None)
    assert apply_workload(20, "Laurea", "SYN-A", "B", rules) == (0, None, None)


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
