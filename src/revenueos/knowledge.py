"""Stewarded lexical retrieval with exact, scope-checked, revocable citations."""

from __future__ import annotations

import hashlib
import re
from datetime import UTC, datetime
from typing import Any, Literal
from uuid import NAMESPACE_URL, UUID, uuid5

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator
from sqlalchemy import Connection, text

CHUNKER_VERSION = "paragraph_1600_v1"


class Principal(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    organization_id: UUID
    actor_id: UUID


class DocumentInput(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    slug: str = Field(min_length=1, max_length=100, pattern=r"^[a-z0-9_-]+$")
    version: int = Field(ge=1)
    title: str = Field(min_length=1, max_length=200)
    content: str = Field(min_length=1)
    data_mode: Literal["synthetic", "real"]
    access_scope: str = Field(min_length=1, max_length=64, pattern=r"^[a-z0-9_-]+$")
    claim_key: str = Field(min_length=1, max_length=100)
    claim_value: str = Field(min_length=1, max_length=500)
    outreach_allowed: bool
    approved: bool
    valid_from: AwareDatetime
    valid_until: AwareDatetime | None

    @model_validator(mode="after")
    def validate_content(self) -> DocumentInput:
        if "\x00" in self.content or len(self.content.encode()) > 262144:
            raise ValueError("invalid_document_content")
        if self.valid_until and self.valid_until <= self.valid_from:
            raise ValueError("invalid_document_validity")
        return self


class Citation(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    evidence_id: str
    document_id: UUID
    version_id: UUID
    chunk_id: UUID
    version: int
    title: str
    heading: str
    start_offset: int
    end_offset: int
    text: str
    text_hash: str
    claim_key: str
    claim_value: str
    outreach_allowed: bool


def authorize(connection: Connection, principal: Principal, *, steward: bool = False) -> list[str]:
    row = (
        connection.execute(
            text("""
        SELECT role,scopes FROM knowledge_memberships
        WHERE organization_id=:org AND actor_id=:actor AND active
    """),
            {"org": principal.organization_id, "actor": principal.actor_id},
        )
        .mappings()
        .first()
    )
    if row is None or (steward and row["role"] != "steward"):
        raise PermissionError("knowledge_access_denied")
    return list(row["scopes"])


def chunk_text(content: str) -> list[dict[str, Any]]:
    """Non-overlapping exact paragraph extracts with character offsets, not byte offsets."""
    parts = []
    heading = ""
    for match in re.finditer(r"[^\n]+(?:\n(?!\n)[^\n]+)*", content):
        raw = match.group()
        if raw.startswith("#"):
            first, separator, rest = raw.partition("\n")
            heading = first.lstrip("# ").strip()[:500]
            if not separator or not rest.strip():
                continue
            start = match.start() + len(first) + 1
        else:
            start = match.start()
        end = match.end()
        while start < end and content[start].isspace():
            start += 1
        while end > start and content[end - 1].isspace():
            end -= 1
        # Split unusually long paragraphs at whitespace while preserving exact offsets.
        while start < end:
            stop = min(start + 1600, end)
            if stop < end:
                boundary = content.rfind(" ", start, stop)
                if boundary > start:
                    stop = boundary
            excerpt = content[start:stop]
            if excerpt:
                parts.append({"heading": heading, "start": start, "end": stop, "text": excerpt})
            start = stop
            while start < end and content[start].isspace():
                start += 1
    if not parts:
        raise ValueError("document_has_no_body_text")
    return parts


def ingest_document(
    connection: Connection,
    principal: Principal,
    document: DocumentInput,
    *,
    now: datetime | None = None,
) -> UUID:
    connection.execute(
        text("SELECT id FROM organizations WHERE id=:org FOR UPDATE"),
        {"org": principal.organization_id},
    )
    scopes = authorize(connection, principal, steward=True)
    if document.access_scope not in scopes:
        raise PermissionError("cannot_publish_outside_assigned_scope")
    mode = connection.scalar(
        text("SELECT data_mode FROM organizations WHERE id=:org"),
        {"org": principal.organization_id},
    )
    if mode != document.data_mode:
        raise ValueError("document_mode_mismatch")
    now = now or datetime.now(UTC)
    if now.tzinfo is None:
        raise ValueError("aware_approval_time_required")
    document_id = uuid5(
        NAMESPACE_URL, f"revenueos:document:{principal.organization_id}:{document.slug}"
    )
    version_id = uuid5(document_id, str(document.version))
    content_hash = hashlib.sha256(document.content.encode()).hexdigest()
    existing = (
        connection.execute(
            text("""
        SELECT * FROM document_versions WHERE organization_id=:org AND id=:id
    """),
            {"org": principal.organization_id, "id": version_id},
        )
        .mappings()
        .first()
    )
    if existing:
        same = (
            existing["content_hash"] == content_hash
            and existing["title"] == document.title
            and existing["access_scope"] == document.access_scope
            and existing["claim_key"] == document.claim_key
            and existing["claim_value"] == document.claim_value
            and existing["outreach_allowed"] == document.outreach_allowed
            and existing["valid_from"] == document.valid_from
            and existing["valid_until"] == document.valid_until
            and (existing["approved_at"] is not None) == document.approved
        )
        if not same:
            raise ValueError("immutable_document_version_conflict")
        return version_id
    connection.execute(
        text("""
        INSERT INTO documents(organization_id,id,slug) VALUES(:org,:id,:slug)
        ON CONFLICT(organization_id,id) DO NOTHING
    """),
        {"org": principal.organization_id, "id": document_id, "slug": document.slug},
    )
    connection.execute(
        text("""
        INSERT INTO document_versions(organization_id,id,document_id,version,title,content,
          content_hash,access_scope,data_mode,claim_key,claim_value,outreach_allowed,status,
          approved_by,approved_at,valid_from,valid_until,chunker_version)
        VALUES(:org,:id,:doc,:version,:title,:content,:hash,:scope,:mode,:key,:value,:outreach,
          :status,:actor,:approved_at,:valid_from,:valid_until,:chunker)
    """),
        {
            "org": principal.organization_id,
            "id": version_id,
            "doc": document_id,
            "version": document.version,
            "title": document.title,
            "content": document.content,
            "hash": content_hash,
            "scope": document.access_scope,
            "mode": document.data_mode,
            "key": document.claim_key,
            "value": document.claim_value,
            "outreach": document.outreach_allowed,
            "status": "approved" if document.approved else "draft",
            "actor": principal.actor_id if document.approved else None,
            "approved_at": now if document.approved else None,
            "valid_from": document.valid_from,
            "valid_until": document.valid_until,
            "chunker": CHUNKER_VERSION,
        },
    )
    for ordinal, chunk in enumerate(chunk_text(document.content)):
        connection.execute(
            text("""
            INSERT INTO document_chunks(organization_id,id,document_version_id,ordinal,heading,
              start_offset,end_offset,text,text_hash,search_vector)
            VALUES(:org,:id,:version,:ordinal,:heading,:start,:end,:body,:hash,
              setweight(to_tsvector('english',:title),'A') ||
              setweight(to_tsvector('english',:body),'B'))
        """),
            {
                "org": principal.organization_id,
                "id": uuid5(version_id, str(ordinal)),
                "version": version_id,
                "ordinal": ordinal,
                "heading": chunk["heading"],
                "start": chunk["start"],
                "end": chunk["end"],
                "body": chunk["text"],
                "hash": hashlib.sha256(chunk["text"].encode()).hexdigest(),
                "title": document.title,
            },
        )
    return version_id


def revoke_document(connection: Connection, principal: Principal, version: UUID) -> None:
    connection.execute(
        text("SELECT id FROM organizations WHERE id=:org FOR UPDATE"),
        {"org": principal.organization_id},
    )
    scopes = authorize(connection, principal, steward=True)
    result = connection.execute(
        text("""
        UPDATE document_versions SET status='revoked',revoked_at=now()
        WHERE organization_id=:org AND id=:id AND status='approved' AND access_scope=ANY(:scopes)
    """),
        {"org": principal.organization_id, "id": version, "scopes": scopes},
    )
    if result.rowcount != 1:
        raise PermissionError("document_not_available_for_revocation")


VISIBLE = """
    v.organization_id=:org AND v.access_scope=ANY(:scopes)
    AND v.status='approved' AND v.revoked_at IS NULL AND v.approved_at <= :at
    AND v.valid_from <= :at AND (v.valid_until IS NULL OR v.valid_until > :at)
    AND v.version=(SELECT max(newer.version) FROM document_versions newer
      WHERE newer.organization_id=v.organization_id AND newer.document_id=v.document_id
        AND newer.approved_at <= :at)
"""


def _citation(row: Any) -> Citation:
    return Citation(
        evidence_id=f"doc:{row['id']}",
        document_id=row["document_id"],
        version_id=row["document_version_id"],
        chunk_id=row["id"],
        version=row["version"],
        title=row["title"],
        heading=row["heading"],
        start_offset=row["start_offset"],
        end_offset=row["end_offset"],
        text=row["text"],
        text_hash=row["text_hash"],
        claim_key=row["claim_key"],
        claim_value=row["claim_value"],
        outreach_allowed=row["outreach_allowed"],
    )


def search(
    connection: Connection,
    principal: Principal,
    query: str,
    *,
    method: Literal["lexical", "title_keyword"] = "lexical",
    limit: int = 5,
    at: datetime | None = None,
) -> list[Citation]:
    scopes = authorize(connection, principal)
    if not 1 <= limit <= 20 or not 0 < len(query.strip()) <= 500:
        raise ValueError("invalid_search_bounds")
    at = at or datetime.now(UTC)
    if at.tzinfo is None:
        raise ValueError("aware_search_time_required")
    words = re.findall(r"[a-z0-9]+", query.lower())[:60]
    if not words:
        return []
    # The OR operator here is server-created. Raw input never becomes SQL or tsquery code.
    ts_query = " OR ".join(words)
    vector = "c.search_vector" if method == "lexical" else "to_tsvector('english',v.title)"
    if method not in ("lexical", "title_keyword"):
        raise ValueError("unknown_search_method")
    rows = connection.execute(
        text(f"""
        SELECT c.*,v.document_id,v.version,v.title,v.claim_key,v.claim_value,v.outreach_allowed,
          ts_rank_cd({vector},websearch_to_tsquery('english',:query)) AS rank
        FROM document_chunks c JOIN document_versions v ON
          (v.organization_id,v.id)=(c.organization_id,c.document_version_id)
        WHERE {VISIBLE} AND {vector} @@ websearch_to_tsquery('english',:query)
        ORDER BY rank DESC,c.id LIMIT :limit
    """),
        {
            "org": principal.organization_id,
            "scopes": scopes,
            "at": at,
            "query": ts_query,
            "limit": limit,
        },
    ).mappings()
    return [_citation(row) for row in rows]


def resolve_citation(
    connection: Connection, principal: Principal, chunk_id: UUID, *, at: datetime | None = None
) -> Citation:
    scopes = authorize(connection, principal)
    at = at or datetime.now(UTC)
    if at.tzinfo is None:
        raise ValueError("aware_citation_time_required")
    row = (
        connection.execute(
            text(f"""
        SELECT c.*,v.document_id,v.version,v.title,v.claim_key,v.claim_value,v.outreach_allowed,
          v.content FROM document_chunks c JOIN document_versions v ON
          (v.organization_id,v.id)=(c.organization_id,c.document_version_id)
        WHERE {VISIBLE} AND c.id=:chunk
    """),
            {"org": principal.organization_id, "scopes": scopes, "at": at, "chunk": chunk_id},
        )
        .mappings()
        .first()
    )
    if row is None:
        raise PermissionError("citation_not_current_or_authorized")
    excerpt = row["content"][row["start_offset"] : row["end_offset"]]
    if excerpt != row["text"] or hashlib.sha256(excerpt.encode()).hexdigest() != row["text_hash"]:
        raise ValueError("citation_integrity_failure")
    return _citation(row)


def has_conflict(
    connection: Connection,
    principal: Principal,
    citations: list[Citation],
    *,
    at: datetime | None = None,
) -> bool:
    scopes = authorize(connection, principal)
    keys = list({citation.claim_key for citation in citations})
    if not keys:
        return False
    return bool(
        connection.scalar(
            text(f"""
        SELECT EXISTS(SELECT v.claim_key FROM document_versions v
        WHERE {VISIBLE} AND v.claim_key=ANY(:keys)
        GROUP BY v.claim_key HAVING count(DISTINCT v.claim_value)>1)
    """),
            {
                "org": principal.organization_id,
                "scopes": scopes,
                "at": at or datetime.now(UTC),
                "keys": keys,
            },
        )
    )
