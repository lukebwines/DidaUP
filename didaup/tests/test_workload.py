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
