"""Stockage PostgreSQL : même comportement que MemoryStore, vérifié par tests/contract/.

Responsable : Abdoul Aziz. Schéma : migrations/001_init.sql. Pilote : asyncpg
(Apache 2.0) ; jamais psycopg (LGPL). Fiches et pièges sont stockés en JSONB (D6) ;
la visibilité des brouillons, le tri et la recherche réutilisent app/stores/search.py
pour donner exactement les mêmes résultats que le stockage mémoire (D17).
"""

from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime
from typing import Any

import asyncpg

from app.domain.models import (
    Account,
    Confirmation,
    Contribution,
    ContributionStatus,
    Fiche,
    GlossaryTerm,
    Gotcha,
    Incident,
    IncidentSource,
    OAuthGrantKind,
    SearchHit,
    SearchQuery,
    TargetKind,
)
from app.stores.search import keep_confirmations, search_fiches, sort_fiches, sort_glossary

_COUNTERS = ("confirmations", "last_confirmed_on")


async def _init_connection(conn: asyncpg.Connection) -> None:
    """Les colonnes JSONB se lisent et s'écrivent directement en objets Python."""
    await conn.set_type_codec("jsonb", encoder=json.dumps, decoder=json.loads, schema="pg_catalog")


def _content_snapshot(fiche: Fiche) -> dict[str, Any]:
    """La fiche sans ses compteurs : sert à n'historiser que les vrais changements de contenu."""
    data = fiche.model_dump(mode="json", exclude=set(_COUNTERS))
    for gotcha in data["gotchas"]:
        for key in _COUNTERS:
            gotcha.pop(key, None)
    return data


class PostgresStore:
    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    @classmethod
    async def connect(cls, database_url: str) -> PostgresStore:
        pool = await asyncpg.create_pool(
            database_url, min_size=1, max_size=5, init=_init_connection
        )
        return cls(pool)

    async def ping(self) -> bool:
        async with self._pool.acquire() as conn:
            return await conn.fetchval("SELECT 1") == 1

    async def close(self) -> None:
        await self._pool.close()

    # --- FicheStore ----------------------------------------------------------

    async def list_fiches(self, *, include_drafts: bool = False) -> list[Fiche]:
        async with self._pool.acquire() as conn:
            return sort_fiches(await self._load_fiches(conn, include_drafts=include_drafts))

    async def get_fiche(self, slug: str, *, include_drafts: bool = False) -> Fiche | None:
        async with self._pool.acquire() as conn:
            fiches = await self._load_fiches(conn, include_drafts=include_drafts, slug=slug)
        return fiches[0] if fiches else None

    async def search(self, query: SearchQuery, *, include_drafts: bool = False) -> list[SearchHit]:
        return search_fiches(await self.list_fiches(include_drafts=include_drafts), query)

    async def list_glossary(self) -> list[GlossaryTerm]:
        rows = await self._pool.fetch("SELECT slug, term, definition FROM glossary_terms")
        return sort_glossary(GlossaryTerm(**dict(row)) for row in rows)

    async def upsert_fiche(self, fiche: Fiche) -> None:
        async with self._pool.acquire() as conn, conn.transaction():
            existing = await self._load_fiches(conn, include_drafts=True, slug=fiche.slug)
            merged = keep_confirmations(fiche, existing[0] if existing else None)
            await conn.execute(
                "INSERT INTO fiches (slug, service_slug, country, publication, title, data,"
                " last_confirmed_on, confirmations)"
                " VALUES ($1, $2, $3, $4, $5, $6, $7, $8)"
                " ON CONFLICT (slug) DO UPDATE SET service_slug = EXCLUDED.service_slug,"
                " country = EXCLUDED.country, publication = EXCLUDED.publication,"
                " title = EXCLUDED.title, data = EXCLUDED.data,"
                " last_confirmed_on = EXCLUDED.last_confirmed_on,"
                " confirmations = EXCLUDED.confirmations, updated_at = now()",
                merged.slug,
                merged.service.slug,
                merged.country,
                merged.publication.value,
                merged.title,
                merged.model_dump(mode="json", exclude={"gotchas"}),
                merged.last_confirmed_on,
                merged.confirmations,
            )
            await conn.execute(
                "DELETE FROM gotchas WHERE fiche_slug = $1 AND NOT (id = ANY($2::text[]))",
                merged.slug,
                [g.id for g in merged.gotchas],
            )
            await conn.executemany(
                "INSERT INTO gotchas (id, fiche_slug, position, publication, data,"
                " last_confirmed_on, confirmations)"
                " VALUES ($1, $2, $3, $4, $5, $6, $7)"
                " ON CONFLICT (id) DO UPDATE SET position = EXCLUDED.position,"
                " publication = EXCLUDED.publication, data = EXCLUDED.data,"
                " last_confirmed_on = EXCLUDED.last_confirmed_on,"
                " confirmations = EXCLUDED.confirmations, updated_at = now()",
                [
                    (
                        g.id,
                        merged.slug,
                        position,
                        g.publication.value,
                        g.model_dump(mode="json"),
                        g.last_confirmed_on,
                        g.confirmations,
                    )
                    for position, g in enumerate(merged.gotchas)
                ],
            )
            snapshot = _content_snapshot(merged)
            last = await conn.fetchval(
                "SELECT data FROM fiche_revisions WHERE fiche_slug = $1 ORDER BY id DESC LIMIT 1",
                merged.slug,
            )
            if last != snapshot:
                await conn.execute(
                    "INSERT INTO fiche_revisions (fiche_slug, data) VALUES ($1, $2)",
                    merged.slug,
                    snapshot,
                )

    async def upsert_glossary(self, terms: list[GlossaryTerm]) -> None:
        await self._pool.executemany(
            "INSERT INTO glossary_terms (slug, term, definition) VALUES ($1, $2, $3)"
            " ON CONFLICT (slug) DO UPDATE SET term = EXCLUDED.term,"
            " definition = EXCLUDED.definition",
            [(t.slug, t.term, t.definition) for t in terms],
        )

    @staticmethod
    async def _load_fiches(
        conn: asyncpg.Connection | asyncpg.pool.PoolConnectionProxy,
        *,
        include_drafts: bool,
        slug: str | None = None,
    ) -> list[Fiche]:
        fiche_rows = await conn.fetch(
            "SELECT slug, data, last_confirmed_on, confirmations FROM fiches"
            " WHERE ($1::text IS NULL OR slug = $1) AND ($2 OR publication = 'published')",
            slug,
            include_drafts,
        )
        if not fiche_rows:
            return []
        gotcha_rows = await conn.fetch(
            "SELECT fiche_slug, data, last_confirmed_on, confirmations FROM gotchas"
            " WHERE fiche_slug = ANY($1::text[]) AND ($2 OR publication = 'published')"
            " ORDER BY fiche_slug, position",
            [row["slug"] for row in fiche_rows],
            include_drafts,
        )
        gotchas: dict[str, list[Gotcha]] = defaultdict(list)
        for row in gotcha_rows:
            gotchas[row["fiche_slug"]].append(
                Gotcha.model_validate(
                    {
                        **row["data"],
                        "last_confirmed_on": row["last_confirmed_on"],
                        "confirmations": row["confirmations"],
                    }
                )
            )
        return [
            Fiche.model_validate(
                {
                    **row["data"],
                    "gotchas": gotchas[row["slug"]],
                    "last_confirmed_on": row["last_confirmed_on"],
                    "confirmations": row["confirmations"],
                }
            )
            for row in fiche_rows
        ]

    # --- IncidentStore -------------------------------------------------------

    async def list_incidents(
        self,
        *,
        service_slug: str | None = None,
        country: str | None = None,
        active_only: bool = False,
        limit: int = 100,
    ) -> list[Incident]:
        rows = await self._pool.fetch(
            "SELECT id, source, external_id, service_slug, country, status, title, description,"
            " url, started_at, resolved_at, reported_by FROM incidents"
            " WHERE ($1::text IS NULL OR service_slug = $1)"
            " AND ($2::text IS NULL OR country = $2)"
            " AND (NOT $3 OR resolved_at IS NULL)"
            " ORDER BY started_at DESC, id LIMIT $4",
            service_slug,
            country,
            active_only,
            limit,
        )
        return [Incident.model_validate(dict(row)) for row in rows]

    async def upsert_incident(self, incident: Incident) -> None:
        await self._pool.execute(
            "INSERT INTO incidents (id, source, external_id, service_slug, country, status, title,"
            " description, url, started_at, resolved_at, reported_by)"
            " VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)"
            " ON CONFLICT (id) DO UPDATE SET source = EXCLUDED.source,"
            " external_id = EXCLUDED.external_id, service_slug = EXCLUDED.service_slug,"
            " country = EXCLUDED.country, status = EXCLUDED.status, title = EXCLUDED.title,"
            " description = EXCLUDED.description, url = EXCLUDED.url,"
            " started_at = EXCLUDED.started_at, resolved_at = EXCLUDED.resolved_at,"
            " reported_by = EXCLUDED.reported_by, updated_at = now()",
            incident.id,
            incident.source.value,
            incident.external_id,
            incident.service_slug,
            incident.country,
            incident.status.value,
            incident.title,
            incident.description,
            str(incident.url) if incident.url else None,
            incident.started_at,
            incident.resolved_at,
            incident.reported_by,
        )

    async def get_last_ingest(self, source: IncidentSource) -> datetime | None:
        return await self._pool.fetchval(
            "SELECT last_success_at FROM ingest_runs WHERE source = $1", source.value
        )

    async def set_last_ingest(self, source: IncidentSource, at: datetime) -> None:
        await self._pool.execute(
            "INSERT INTO ingest_runs (source, last_success_at) VALUES ($1, $2)"
            " ON CONFLICT (source) DO UPDATE SET last_success_at = EXCLUDED.last_success_at",
            source.value,
            at,
        )

    # --- ContributionStore ---------------------------------------------------

    async def add_contribution(self, contribution: Contribution) -> None:
        c = contribution
        await self._pool.execute(
            "INSERT INTO contributions (id, kind, fiche_slug, title, body_md, source_url,"
            " api_version, pseudo, email, status, created_at, reviewed_at, reviewer, review_note)"
            " VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14)",
            c.id,
            c.kind.value,
            c.fiche_slug,
            c.title,
            c.body_md,
            str(c.source_url) if c.source_url else None,
            c.api_version,
            c.pseudo,
            c.email,
            c.status.value,
            c.created_at,
            c.reviewed_at,
            c.reviewer,
            c.review_note,
        )

    async def get_contribution(self, contribution_id: str) -> Contribution | None:
        row = await self._pool.fetchrow(
            "SELECT id, kind, fiche_slug, title, body_md, source_url, api_version, pseudo, email,"
            " status, created_at, reviewed_at, reviewer, review_note"
            " FROM contributions WHERE id = $1",
            contribution_id,
        )
        return Contribution.model_validate(dict(row)) if row else None

    async def list_contributions(
        self, *, status: ContributionStatus | None = None
    ) -> list[Contribution]:
        rows = await self._pool.fetch(
            "SELECT id, kind, fiche_slug, title, body_md, source_url, api_version, pseudo, email,"
            " status, created_at, reviewed_at, reviewer, review_note FROM contributions"
            " WHERE ($1::text IS NULL OR status = $1) ORDER BY created_at, id",
            status.value if status else None,
        )
        return [Contribution.model_validate(dict(row)) for row in rows]

    async def update_contribution(self, contribution: Contribution) -> None:
        c = contribution
        await self._pool.execute(
            "UPDATE contributions SET kind = $2, fiche_slug = $3, title = $4, body_md = $5,"
            " source_url = $6, api_version = $7, pseudo = $8, email = $9, status = $10,"
            " reviewed_at = $11, reviewer = $12, review_note = $13 WHERE id = $1",
            c.id,
            c.kind.value,
            c.fiche_slug,
            c.title,
            c.body_md,
            str(c.source_url) if c.source_url else None,
            c.api_version,
            c.pseudo,
            c.email,
            c.status.value,
            c.reviewed_at,
            c.reviewer,
            c.review_note,
        )

    async def add_confirmation(self, confirmation: Confirmation) -> None:
        c = confirmation
        async with self._pool.acquire() as conn, conn.transaction():
            await conn.execute(
                "INSERT INTO confirmations (target_kind, target_id, still_works, api_version,"
                " pseudo, created_at) VALUES ($1, $2, $3, $4, $5, $6)",
                c.target_kind.value,
                c.target_id,
                c.still_works,
                c.api_version,
                c.pseudo,
                c.created_at,
            )
            if not c.still_works:
                return
            table_update = (
                "UPDATE fiches SET confirmations = confirmations + 1,"
                " last_confirmed_on = GREATEST(last_confirmed_on, $2) WHERE slug = $1"
                if c.target_kind is TargetKind.FICHE
                else "UPDATE gotchas SET confirmations = confirmations + 1,"
                " last_confirmed_on = GREATEST(last_confirmed_on, $2) WHERE id = $1"
            )
            await conn.execute(table_update, c.target_id, c.created_at.date())

    # --- AccountStore ---------------------------------------------------------

    async def save_account(self, account: Account) -> None:
        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO accounts (id, pseudo, created_at, last_login_at, blocked)
                VALUES ($1, $2, $3, $4, $5)
                ON CONFLICT (id) DO UPDATE SET
                    pseudo = EXCLUDED.pseudo,
                    last_login_at = EXCLUDED.last_login_at,
                    blocked = accounts.blocked OR EXCLUDED.blocked
                """,
                account.id,
                account.pseudo,
                account.created_at,
                account.last_login_at,
                account.blocked,
            )

    async def get_account(self, account_id: str) -> Account | None:
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT id, pseudo, created_at, last_login_at, blocked FROM accounts WHERE id = $1",
                account_id,
            )
        return Account(**dict(row)) if row else None

    async def save_oauth_client(self, client_id: str, data: dict[str, Any]) -> None:
        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO oauth_clients (client_id, data) VALUES ($1, $2)
                ON CONFLICT (client_id) DO UPDATE SET data = EXCLUDED.data
                """,
                client_id,
                data,
            )

    async def get_oauth_client(self, client_id: str) -> dict[str, Any] | None:
        async with self._pool.acquire() as conn:
            return await conn.fetchval(
                "SELECT data FROM oauth_clients WHERE client_id = $1", client_id
            )

    async def add_oauth_grant(
        self, kind: OAuthGrantKind, key_hash: str, data: dict[str, Any], expires_at: datetime
    ) -> None:
        async with self._pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO oauth_grants (kind, key_hash, data, expires_at)"
                " VALUES ($1, $2, $3, $4)",
                kind.value,
                key_hash,
                data,
                expires_at,
            )

    async def get_oauth_grant(
        self, kind: OAuthGrantKind, key_hash: str, now: datetime
    ) -> dict[str, Any] | None:
        async with self._pool.acquire() as conn:
            return await conn.fetchval(
                "SELECT data FROM oauth_grants"
                " WHERE kind = $1 AND key_hash = $2 AND expires_at > $3",
                kind.value,
                key_hash,
                now,
            )

    async def take_oauth_grant(
        self, kind: OAuthGrantKind, key_hash: str, now: datetime
    ) -> dict[str, Any] | None:
        async with self._pool.acquire() as conn:
            return await conn.fetchval(
                "DELETE FROM oauth_grants WHERE kind = $1 AND key_hash = $2 AND expires_at > $3"
                " RETURNING data",
                kind.value,
                key_hash,
                now,
            )

    async def delete_expired_oauth_grants(self, now: datetime) -> None:
        async with self._pool.acquire() as conn:
            await conn.execute("DELETE FROM oauth_grants WHERE expires_at <= $1", now)
