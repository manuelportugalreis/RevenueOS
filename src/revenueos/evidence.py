"""Deterministic relevance/answerability checks independent of evaluation labels."""

import re
from datetime import datetime
from typing import Any, Literal

from sqlalchemy import Connection, text

from revenueos.knowledge import Citation, Principal, search

VERSION = "focused_evidence_v2"


def select_evidence(
    connection: Connection,
    principal: Principal,
    query: str,
    at: datetime,
    method: Literal["lexical", "title_keyword"] = "lexical",
) -> tuple[list[Citation], dict[str, Any]]:
    candidates = search(connection, principal, query, at=at, limit=20, method=method)
    texts = [
        query,
        *[c.text for c in candidates],
        *[f"{c.title} {c.heading} {c.claim_key}" for c in candidates],
    ]
    terms = [
        set(row)
        for row in connection.scalars(
            text("""SELECT
        tsvector_to_array(to_tsvector('english',value))
        FROM unnest(CAST(:texts AS text[])) WITH ORDINALITY AS t(value,n) ORDER BY n"""),
            {"texts": texts},
        )
    ]
    query_terms = terms[0]
    summary: dict[str, Any] = {
        "version": VERSION,
        "candidate_count": len(candidates),
        "selected_count": 0,
        "reason": "insufficient_evidence",
    }
    if not candidates or not query_terms:
        return [], summary
    n = len(candidates)
    scores = [
        (
            len(query_terms & terms[i + 1]) / len(query_terms),
            len(query_terms & terms[n + i + 1]) / len(query_terms),
        )
        for i in range(n)
    ]
    best = max(scores)
    chosen = [c for c, score in zip(candidates, scores, strict=True) if score == best]
    if best[0] < 0.5 or len({c.claim_key for c in chosen}) != 1:
        return [], summary
    qualifiers = set(
        re.findall(
            r"\b(?:legacy|expired|revoked|unpublished|confidential|private)\b", query.lower()
        )
    )
    chosen = [
        c
        for c in chosen
        if all(re.search(r"\b" + word + r"\b", c.text, re.I) for word in qualifiers)
    ]
    if re.search(r"\b(exact|amount|dollars?|percentage)\b|how\s+much|[$€£]", query, re.I):
        chosen = [c for c in chosen if re.search(r"\d", c.text)]
    chosen = chosen[:5]
    summary.update(
        selected_count=len(chosen),
        coverage=best[0],
        reason=None if chosen else "insufficient_evidence",
    )
    return chosen, summary
