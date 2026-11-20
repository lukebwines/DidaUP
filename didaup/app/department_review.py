"""Conservative read-only review of FIVE returned, complete departmental XLSX.

No approval or import of teaching assignments. Untrusted Excel source values,
technical IDs, and proposals are independently checked against the private
historical source. Any overlapping proposals across files are reported rather
than silently added or resolved.
"""
from __future__ import annotations

from collections import defaultdict
from decimal import Decimal, InvalidOperation
from pathlib import Path

from python_calamine import CalamineWorkbook

from .department_workbooks import (
    _prepare, _display, ALL_HEADERS, HISTORIC_HEADERS, VISIBLE_HEADERS,
    WorkbookGenerationError,
)

MAX_REVIEW_ROWS = 60_000
MAX_ISSUES = 200


class ReviewError(ValueError):
    pass


def _number(value):
    if value is None or isinstance(value, bool):
        return None
    raw = _display(value).replace(",", ".").strip()
    if not raw:
        return None
    try:
        result = Decimal(raw)
    except InvalidOperation:
        return None
    return result if result.is_finite() else None


def review_five_workbooks(
    original: Path, source_sha256: str, sheet_name: str, header_row: int,
    assigned: dict[str, int], history_year: str,
    files: list[Path], excluded: set[tuple[str, str, int]] | None = None,
    included: set[tuple[str, str, int]] | None = None,
    cohort_names: dict[tuple[str, str, int], str] | None = None,
    workload_rules: list[dict] | None = None,
) -> dict:
    if len(files) != 5:
        raise ReviewError("Occorrono esattamente cinque file Excel")
    try:
        (historical, excluded_count, unresolved_count, unresolved_examples,
         missing_code_count, missing_code_examples, excluded_ambiguous_count,
         unmatched_exclusions_count, unmatched_exclusion_examples,
         fallback_count, fallback_examples, partial_count, partial_examples,
         residual_count, residual_examples,
         taf_mapping_mode, taf_rows_with_value, taf_rows_without_value,
         mutuazione_mapping_mode, mutuazione_true_count,
         mutuazione_false_count, mutuazione_other_count, mutuazione_blank_count,
         excluded_records, workload_stats) = _prepare(
            original, source_sha256, sheet_name, header_row, assigned,
            history_year, excluded or set(), included, cohort_names,
            workload_rules,
        )
    except WorkbookGenerationError as exc:
        raise ReviewError(str(exc)) from exc

    expected = {
        hist_id: {"data": data, "activity_id": activity_id}
        for data, hist_id, activity_id in historical
    }
    changes_by_activity: dict[str, dict[int, list[tuple]]] = defaultdict(
        lambda: defaultdict(list)
    )
    results = []
    issues = []

    def issue(file_no: int, row_no: int | None, reason: str):
        if len(issues) < MAX_ISSUES:
            issues.append({
                "file": file_no, "excel_row": row_no, "reason": reason,
            })

    for file_no, path in enumerate(files, start=1):
        if not path.is_file():
            raise ReviewError(f"File {file_no} non disponibile")
        try:
            wb = CalamineWorkbook.from_path(path)
            if wb.sheet_names != ["Proposte SSD"]:
                raise ReviewError(f"File {file_no}: struttura fogli inattesa")
            sheet = wb.get_sheet_by_name("Proposte SSD")
            if sheet.width != len(ALL_HEADERS):
                raise ReviewError(f"File {file_no}: struttura colonne non valida")
            if sheet.height > MAX_REVIEW_ROWS + 6:
                raise ReviewError(f"File {file_no}: numero righe non ammesso")
            rows = sheet.to_python(skip_empty_area=False)
        except ReviewError:
            raise
        except Exception as exc:
            raise ReviewError(f"File {file_no} non leggibile") from exc
        if len(rows) < 7 or list(rows[5])[:len(ALL_HEADERS)] != ALL_HEADERS:
            raise ReviewError(f"File {file_no}: intestazioni DidaUP non valide")

        seen_historical = set()
        seen_proposal_ids = set()
        ceded_by_origin = defaultdict(Decimal)
        changes = []
        for excel_row, raw in enumerate(rows[6:], start=7):
            row = list(raw) + [None] * max(0, len(ALL_HEADERS) - len(raw))
            if not any(_display(v) for v in row):
                issue(file_no, excel_row, "Riga vuota nella struttura delle coperture")
                continue
            row_type, origin, proposal_id, activity = (
                _display(row[i]) for i in range(37, 41)
            )
            if origin not in expected:
                issue(file_no, excel_row, "ID origine assente o non riconosciuto")
                continue
            reference = expected[origin]
            if activity != reference["activity_id"]:
                issue(file_no, excel_row, "Identificativo attività non corrispondente allo storico")
                continue
            if row_type == "STORICO":
                if proposal_id != origin or origin in seen_historical:
                    issue(file_no, excel_row, "Riga storica duplicata o modificata")
                    continue
                seen_historical.add(origin)
            elif row_type == "VARIAZIONE":
                if (not proposal_id.startswith("DIDAUP-VAR-")
                    or proposal_id in seen_proposal_ids):
                    issue(file_no, excel_row, "Identificativo variazione duplicato o non valido")
                    continue
                seen_proposal_ids.add(proposal_id)
            else:
                issue(file_no, excel_row, "Tipologia riga DidaUP non valida")
                continue

            # Re-verify every historical column (not just the hidden IDs).
            is_tampered = any(
                _display(row[col]) != _display(reference["data"].get(header, ""))
                for col, header in enumerate(VISIBLE_HEADERS)
                if not (29 <= col <= 32)
            )
            if is_tampered:
                issue(file_no, excel_row, "Una o più celle storiche sono state modificate")
                continue

            kind, new_teacher, hours, note = (
                _display(row[i]) for i in range(29, 33)
            )
            if not any((kind, new_teacher, hours, note)):
                continue
            if not kind:
                issue(file_no, excel_row, "Tipo variazione mancante")
                continue
            normalized = kind.casefold()
            historical_hours = _number(reference["data"].get("TOT ORE EFFETTIVE"))
            moved = _number(hours)
            if normalized in ("aggiunta", "sostituzione parziale"):
                if not new_teacher:
                    issue(file_no, excel_row, "Docente destinatario mancante")
                    continue
                if moved is None or moved <= 0:
                    issue(file_no, excel_row, "Ore cedute mancanti o non positive")
                    continue
            elif normalized == "sostituzione totale":
                if not new_teacher:
                    issue(file_no, excel_row, "Docente sostitutivo mancante")
                    continue
                if historical_hours is None or historical_hours <= 0:
                    issue(file_no, excel_row, "Ore storiche assenti o pari a zero per sostituzione totale")
                    continue
                if moved is None and not hours:
                    moved = historical_hours
                elif moved != historical_hours:
                    issue(file_no, excel_row, "Sostituzione totale: ore diverse dallo storico")
                    continue
            else:
                issue(
                    file_no, excel_row,
                    "Tipo variazione non ancora definito nelle regole operative",
                )
                continue
            if historical_hours is None:
                issue(file_no, excel_row, "Ore storiche non disponibili per la cessione")
                continue
            if moved > historical_hours:
                issue(file_no, excel_row, "Ore cedute superiori alle ore storiche")
                continue
            ceded_by_origin[origin] += moved
            identity = (origin, kind.casefold(), new_teacher.casefold(), str(moved), note)
            changes.append((activity, identity))
            changes_by_activity[activity][file_no].append(identity)

        for origin, ceded in ceded_by_origin.items():
            available = _number(expected[origin]["data"].get("TOT ORE EFFETTIVE"))
            if available is not None and ceded > available:
                issue(
                    file_no, None,
                    "Somma delle ore cedute oltre il disponibile su una copertura storica"
                )
        if seen_historical != set(expected):
            issue(
                file_no, None,
                "Righe storiche mancanti rispetto alla fonte immutabile"
            )
        results.append({
            "file": file_no,
            "historical_rows_found": len(seen_historical),
            "changes_found": len(changes),
        })

    overlaps = []
    for activity, by_file in sorted(changes_by_activity.items()):
        if len(by_file) <= 1:
            continue
        proposal_sets = [sorted(set(proposals)) for proposals in by_file.values()]
        overlaps.append({
            "activity_id": activity,
            "files": sorted(by_file),
            "identical_proposals": all(x == proposal_sets[0] for x in proposal_sets[1:]),
            "status": "DA_RISOLVERE",
        })

    return {
        "files_received": 5,
        "workload": workload_stats,
        "expected_historical_rows_per_file": len(expected),
        "excluded_rows_per_file": excluded_count,
        "excluded_rows_with_missing_year": excluded_ambiguous_count,
        "unmatched_exclusion_count": unmatched_exclusions_count,
        "unmatched_exclusion_examples": unmatched_exclusion_examples,
        "cohorts_matched_by_unique_name_rows": fallback_count,
        "cohorts_matched_by_unique_name_examples": fallback_examples,
        "mixed_annuality_rows_retained": partial_count,
        "mixed_annuality_example_rows": partial_examples,
        "excluded_course_titles_still_present": residual_count,
        "excluded_course_title_examples": residual_examples,
        "taf_mapping_mode": taf_mapping_mode,
        "taf_rows_with_value": taf_rows_with_value,
        "taf_rows_without_value": taf_rows_without_value,
        "mutuazione_mapping_mode": mutuazione_mapping_mode,
        "mutuazione_true_rows": mutuazione_true_count,
        "mutuazione_false_rows": mutuazione_false_count,
        "mutuazione_other_rows": mutuazione_other_count,
        "mutuazione_empty_rows": mutuazione_blank_count,
        "unresolved_annuality_rows_included": unresolved_count,
        "unresolved_annuality_example_rows": unresolved_examples,
        "missing_activity_codes_rows_included": missing_code_count,
        "missing_activity_codes_example_rows": missing_code_examples,
        "per_file": results,
        "overlaps": overlaps,
        "overlap_count": len(overlaps),
        "issue_count_at_least": len(issues),
        "issues": issues,
        "blocked": bool(issues or overlaps),
        "note": (
            "Anteprima di istruttoria soltanto: non registra, non fonde e "
            "non approva le coperture. Le sovrapposizioni richiedono esame."
        ),
    }
