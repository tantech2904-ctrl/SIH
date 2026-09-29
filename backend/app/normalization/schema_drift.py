"""Schema drift detection.

When a known vendor/parser emits a field that is not part of the expected
mapping set, but that semantically corresponds to an existing canonical field,
we surface a drift record for analyst approval.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from app.normalization.vocabulary import lookup_alias, normalize_alias_key


@dataclass
class DriftCandidate:
    expected_field: str
    observed_field: str
    suggested_canonical: str
    confidence: float
    reason: str


def detect_drift(
    *,
    vendor: str,
    parser_id: str,
    parser_version: str,
    known_fields: Iterable[str],
    observed_fields: Iterable[str],
) -> list[DriftCandidate]:
    known_norm = {normalize_alias_key(f): f for f in known_fields}
    known_canonicals = set()
    for f in known_fields:
        canon = lookup_alias(f)
        if canon:
            known_canonicals.add(canon)

    candidates: list[DriftCandidate] = []
    for observed in observed_fields:
        key = normalize_alias_key(observed)
        if key in known_norm:
            continue
        # Does it alias to a canonical we already know about?
        canon = lookup_alias(observed)
        if not canon:
            continue
        # If we already have a mapping for this canonical via another field, that's drift.
        if canon in known_canonicals:
            # find the *expected* field name for this canonical
            expected = None
            for f in known_fields:
                if lookup_alias(f) == canon:
                    expected = f
                    break
            candidates.append(DriftCandidate(
                expected_field=expected or canon,
                observed_field=observed,
                suggested_canonical=canon,
                confidence=0.75,
                reason=(
                    f"Observed field '{observed}' aliases to canonical '{canon}', "
                    f"but parser already maps '{expected}' to the same canonical."
                ),
            ))
    return candidates