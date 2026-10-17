from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy import Engine, text
from sqlalchemy.exc import DBAPIError

from revenueos.evaluation import STEWARD
from revenueos.knowledge import (
    DocumentInput,
    Principal,
    chunk_text,
    has_conflict,
    ingest_document,
    resolve_citation,
    revoke_document,
    search,
)
from revenueos.synthetic import SYNTHETIC_ORG

AT = datetime(2026, 10, 16, 12, tzinfo=UTC)


def test_chunk_offsets_preserve_exact_unicode_content() -> None:
    content = "# Title\n\nCafé: an exact passage.\n\n" + "long paragraph words " * 100
    chunks = chunk_text(content)
    assert len(chunks) >= 3
    assert all(content[item["start"] : item["end"]] == item["text"] for item in chunks)
    assert max(len(item["text"]) for item in chunks) <= 1600


@pytest.mark.integration
def test_authorized_passage_and_simple_baseline(engine: Engine, intelligence: tuple) -> None:
    _, principal = intelligence
    with engine.connect() as connection:
        hits = search(connection, principal, "configuration checklist", at=AT)
        assert len(hits) == 1
        citation = resolve_citation(connection, principal, hits[0].chunk_id, at=AT)
        assert citation == hits[0]
        assert (
            citation.text == "Onboarding includes a kickoff workshop and a configuration checklist."
        )
        assert (
            search(connection, principal, "configuration checklist", method="title_keyword", at=AT)
            == []
        )


@pytest.mark.integration
@pytest.mark.parametrize(
    "query,slug",
    [
        ("confidential margin", "private"),
        ("legacy discount", "expired"),
        ("telephony roadmap", "draft"),
        ("withdrawn partnership", "revoked"),
    ],
)
def test_restricted_expired_draft_and_revoked_sources_hidden(
    engine: Engine,
    intelligence: tuple,
    query: str,
    slug: str,
) -> None:
    _, principal = intelligence
    with engine.connect() as connection:
        protected_id = connection.scalar(
            text("SELECT id FROM documents WHERE organization_id=:org AND slug=:slug"),
            {"org": principal.organization_id, "slug": slug},
        )
        assert protected_id not in {
            citation.document_id for citation in search(connection, principal, query, at=AT)
        }


@pytest.mark.integration
def test_other_actor_and_organization_cannot_retrieve(engine: Engine, intelligence: tuple) -> None:
    _, principal = intelligence
    with engine.connect() as connection:
        for actor in (
            Principal(organization_id=SYNTHETIC_ORG, actor_id=uuid4()),
            Principal(organization_id=uuid4(), actor_id=principal.actor_id),
        ):
            with pytest.raises(PermissionError):
                search(connection, actor, "onboarding", at=AT)


@pytest.mark.integration
def test_revocation_invalidates_citations(engine: Engine, intelligence: tuple) -> None:
    _, principal = intelligence
    with engine.connect() as connection:
        citation = search(connection, principal, "configuration checklist", at=AT)[0]
    steward = Principal(organization_id=SYNTHETIC_ORG, actor_id=STEWARD)
    with engine.begin() as connection:
        revoke_document(connection, steward, citation.version_id)
    with engine.connect() as connection, pytest.raises(PermissionError):
        resolve_citation(connection, principal, citation.chunk_id, at=AT)


@pytest.mark.integration
def test_structured_conflicts_detected(engine: Engine, intelligence: tuple) -> None:
    _, principal = intelligence
    with engine.connect() as connection:
        hits = search(connection, principal, "raw uploads retention", at=AT)
        assert has_conflict(connection, principal, hits, at=AT)


@pytest.mark.integration
def test_document_versions_immutable_and_reader_cannot_publish(
    engine: Engine,
    intelligence: tuple,
) -> None:
    _, principal = intelligence
    with engine.connect() as connection:
        row = connection.execute(text("SELECT * FROM document_versions LIMIT 1")).mappings().one()
    with pytest.raises(DBAPIError, match="immutable"), engine.begin() as connection:
        connection.execute(
            text("UPDATE document_versions SET content='changed' WHERE id=:id"), {"id": row["id"]}
        )
    document = DocumentInput(
        slug="new",
        version=1,
        title="SYNTHETIC New",
        content="New content.",
        data_mode="synthetic",
        access_scope="team",
        claim_key="new",
        claim_value="new",
        outreach_allowed=True,
        approved=True,
        valid_from=AT,
        valid_until=None,
    )
    with engine.begin() as connection, pytest.raises(PermissionError):
        ingest_document(connection, principal, document, now=AT)


@pytest.mark.integration
def test_unknown_citation_and_query_bounds(engine: Engine, intelligence: tuple) -> None:
    _, principal = intelligence
    with engine.connect() as connection:
        with pytest.raises(PermissionError):
            resolve_citation(connection, principal, uuid4(), at=AT)
        with pytest.raises(ValueError):
            search(connection, principal, "x" * 501, at=AT)
        assert search(connection, principal, "' ; DROP TABLE leads; --", at=AT) == []
