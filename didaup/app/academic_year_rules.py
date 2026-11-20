"""Academic-year convention explicitly confirmed for Schools of Specialization.

For an explicit School-of-Specialization row only, a report year one
academic year behind the selected archival year is valid. Preserve the
original report year without rewriting it. Other course types require
a matching year. Never infer school classification from an unverified code.
"""
from __future__ import annotations

import re
import unicodedata

from .cohort_import import academic_year


def _normalized(value: object) -> str:
    text = unicodedata.normalize("NFKD", str(value or ""))
    return " ".join(
        "".join(c for c in text if not unicodedata.combining(c)).upper().split()
    )


def is_school_of_specialization(*, course_type: object = "", course_name: object = "") -> bool:
    """Match explicit wording; never infer specialty from a numeric course code."""
    descriptions = [_normalized(course_type), _normalized(course_name)]
    return any(
        ("SCUOLA" in text and "SPECIALIZZAZION" in text)
        or "SCUOLE DI SPECIALIZZAZION" in text
        for text in descriptions
    )


def prior_academic_year(value: str) -> str:
    if not re.fullmatch(r"20\d{2}/\d{2}", value):
        raise ValueError("Anno accademico non valido")
    beginning = int(value[:4])
    if int(value[-2:]) != (beginning + 1) % 100:
        raise ValueError("Anno accademico incoerente")
    return f"{beginning - 1}/{beginning % 100:02d}"


def classify_source_year(source_value: object, selected_aa: str,
                         *, course_type: object = "",
                         course_name: object = "") -> str:
    """Return equal / specialization_convention / invalid; no silent rewriting."""
    parsed = academic_year(source_value)
    if parsed == selected_aa:
        return "equal"
    if (parsed is not None
        and is_school_of_specialization(
            course_type=course_type, course_name=course_name
        )
        and parsed == prior_academic_year(selected_aa)):
        return "specialization_convention"
    return "invalid"
