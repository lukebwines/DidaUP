"""Explicit, year-scoped workload rules; no inference from historic effective hours."""
from __future__ import annotations

import re
import unicodedata
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from python_calamine import CalamineWorkbook

from .column_mapping import normalize_header

MAX_RULES = 500
MAX_CHOICES = 1500
MONEY_PRECISION = Decimal("0.01")
_NUMBER = re.compile(r"\d{1,6}(?:[.,]\d{1,2})?\Z")


class WorkloadRuleError(ValueError):
    pass


def canonical(value):
    return " ".join(unicodedata.normalize("NFKC", str(value or "")).split()).casefold()


def decimal_hours(value):
    if value is None or isinstance(value, bool):
        return None
    try:
        raw = str(value).strip().replace(",", ".")
        if not raw:
            return None
        result = Decimal(raw)
    except (InvalidOperation, ValueError):
        return None
    return result if result.is_finite() and result >= 0 else None


def validate_rules(rules):
    if not isinstance(rules, list) or len(rules) > MAX_RULES:
        raise WorkloadRuleError("Numero di regole non valido (massimo 500)")
    accepted = []
    criteria = set()
    for index, item in enumerate(rules, 1):
        if not isinstance(item, dict):
            raise WorkloadRuleError(f"Regola {index}: struttura non valida")
        rule = {}
        for field, limit in (("tipologia", 120), ("cds", 80), ("taf", 80)):
            value = item.get(field, "")
            if not isinstance(value, str) or len(value) > limit:
                raise WorkloadRuleError(f"Regola {index}: campo {field} non valido")
            rule[field] = " ".join(value.strip().split())
        key = tuple(canonical(rule[field]) for field in ("tipologia", "cds", "taf"))
        if key in criteria:
            raise WorkloadRuleError(f"Regola {index}: combinazione tipologia/CdS/TAF duplicata")
        criteria.add(key)
        mode = item.get("mode")
        value = item.get("value")
        if mode not in ("percentuale", "fissa"):
            raise WorkloadRuleError(f"Regola {index}: scegliere percentuale o quota fissa")
        if not isinstance(value, (str, int, float)) or isinstance(value, bool):
            raise WorkloadRuleError(f"Regola {index}: valore non valido")
        text = str(value).strip()
        if not _NUMBER.fullmatch(text):
            raise WorkloadRuleError(f"Regola {index}: valore numerico con massimo due decimali")
        amount = decimal_hours(text)
        if amount is None or amount > (Decimal("1000") if mode == "percentuale"
                                      else Decimal("999999")):
            raise WorkloadRuleError(f"Regola {index}: valore fuori intervallo")
        rule["mode"] = mode
        rule["value"] = format(amount, "f")
        accepted.append(rule)
    return accepted


def apply_workload(planned, typology, course, taf, rules):
    """Return (hours, matching_rule_index, issue). No matched rule => zero."""
    matches = []
    for i, rule in enumerate(rules):
        if (rule["tipologia"] and canonical(rule["tipologia"]) != canonical(typology)):
            continue
        if rule["cds"] and canonical(rule["cds"]) != canonical(course):
            continue
        if rule["taf"] and canonical(rule["taf"]) != canonical(taf):
            continue
        specificity = sum(bool(rule[key]) for key in ("tipologia", "cds", "taf"))
        matches.append((specificity, i, rule))
    if not matches:
        return 0, None, None
    highest = max(match[0] for match in matches)
    selected = [m for m in matches if m[0] == highest]
    if len(selected) > 1:
        return 0, None, "Conflitto tra regole con la stessa specificità"
    _, index, rule = selected[0]
    hours = decimal_hours(planned)
    if hours is None:
        return 0, index, "TOT ORE PREVISTE mancante, negativo o non numerico"
    rate = Decimal(rule["value"])
    result = (hours * rate / 100 if rule["mode"] == "percentuale"
              else rate).quantize(MONEY_PRECISION, rounding=ROUND_HALF_UP)
    if rule["mode"] == "fissa" and rate > hours:
        return 0, index, "Quota fissa superiore a TOT ORE PREVISTE"
    if result > 99999999:
        return 0, index, "Risultato superiore al limite delle ore ammesse"
    return float(result), index, None


def source_choices(path, sheet_name, header_row, assigned):
    """Distinct exact values from the selected official source, not guesses."""
    wb = CalamineWorkbook.from_path(path)
    if sheet_name not in wb.sheet_names:
        raise WorkloadRuleError("Foglio sorgente non disponibile")
    sheet = wb.get_sheet_by_name(sheet_name)
    if sheet.height > 60041 or sheet.width > 250 or header_row < 1 or header_row > 40:
        raise WorkloadRuleError("Dimensioni del report non supportate")
    rows = sheet.to_python(skip_empty_area=False)
    headings = rows[header_row-1]
    positions = [i for i, name in enumerate(headings) if normalize_header(name) == "TAF"]
    taf_index = assigned.get("taf")
    if taf_index is None and len(positions) == 1:
        taf_index = positions[0]

    def pick(row, index):
        if index is None or not isinstance(index, int) or index < 0 or index >= len(row):
            return ""
        return str(row[index] or "").strip()

    typologies = set()
    courses = {}
    tafs = set()
    for row in rows[header_row:]:
        if not any(value is not None and str(value).strip() for value in row):
            continue
        typ = pick(row, assigned.get("cds_tipologia"))
        cds = pick(row, assigned.get("cds_codice"))
        name = pick(row, assigned.get("cds_nome"))
        taf = pick(row, taf_index)
        if typ:
            typologies.add(typ)
        if taf:
            tafs.add(taf)
        if cds and cds not in courses:
            courses[cds] = name
        if max(len(typologies), len(tafs), len(courses)) > MAX_CHOICES:
            raise WorkloadRuleError("Troppi valori per i selettori delle regole")
    return {
        "tipologie": sorted(typologies, key=canonical),
        "cds": [{"code": code, "name": name} for code, name
                in sorted(courses.items(), key=lambda x: canonical(x[1] or x[0]))],
        "taf": sorted(tafs, key=canonical),
        "mapped": {
            "tot_ore_previste": "ore_previste" in assigned,
            "tipologia": "cds_tipologia" in assigned,
            "cds": "cds_codice" in assigned,
            "taf": taf_index is not None,
        },
    }
