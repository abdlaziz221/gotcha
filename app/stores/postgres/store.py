"""Stockage PostgreSQL : même comportement que MemoryStore, vérifié par tests/contract/.

Responsable : Abdoul Aziz. Schéma : migrations/001_init.sql. Pilote : asyncpg
(Apache 2.0) ; jamais psycopg (LGPL). Les méthodes marquées TODO sont à écrire
(tâches A3 à A5 de docs/PLAN.md) ; la connexion, le ping et la fermeture marchent déjà.
"""

from __future__ import annotations

from datetime import datetime

import asyncpg

from app.domain.models import (
    Confirmation,
    Contribution,
    ContributionStatus,
    Fiche,
    GlossaryTerm,
    Incident,
    IncidentSource,
    SearchHit,
    SearchQuery,
)


class PostgresStore:
    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    @classmethod
    async def connect(cls, database_url: str) -> PostgresStore:
        pool = await asyncpg.create_pool(database_url, min_size=1, max_size=5)
        return cls(pool)

    async def ping(self) -> bool:
        async with self._pool.acquire() as conn:
            return await conn.fetchval("SELECT 1") == 1

    async def close(self) -> None:
        await self._pool.close()

    # --- FicheStore ----------------------------------------------------------

    async def list_fiches(self, *, include_drafts: bool = False) -> list[Fiche]:
        raise NotImplementedError("TODO(A3) : lire fiches + gotchas, filtrer les brouillons")

    async def get_fiche(self, slug: str, *, include_drafts: bool = False) -> Fiche | None:
        raise NotImplementedError("TODO(A3)")

    async def search(self, query: SearchQuery, *, include_drafts: bool = False) -> list[SearchHit]:
        raise NotImplementedError("TODO(A3) : recherche plein texte (colonnes search, index GIN)")

    async def list_glossary(self) -> list[GlossaryTerm]:
        raise NotImplementedError("TODO(A3)")

    async def upsert_fiche(self, fiche: Fiche) -> None:
        raise NotImplementedError("TODO(A6) : utilisé par scripts/seed.py")

    async def upsert_glossary(self, terms: list[GlossaryTerm]) -> None:
        raise NotImplementedError("TODO(A6)")

    # --- IncidentStore -------------------------------------------------------

    async def list_incidents(
        self,
        *,
        service_slug: str | None = None,
        country: str | None = None,
        active_only: bool = False,
        limit: int = 100,
    ) -> list[Incident]:
        raise NotImplementedError("TODO(A4)")

    async def upsert_incident(self, incident: Incident) -> None:
        raise NotImplementedError("TODO(A4) : INSERT … ON CONFLICT (id) DO UPDATE")

    async def get_last_ingest(self, source: IncidentSource) -> datetime | None:
        raise NotImplementedError("TODO(A4) : table ingest_runs")

    async def set_last_ingest(self, source: IncidentSource, at: datetime) -> None:
        raise NotImplementedError("TODO(A4)")

    # --- ContributionStore ---------------------------------------------------

    async def add_contribution(self, contribution: Contribution) -> None:
        raise NotImplementedError("TODO(A5)")

    async def get_contribution(self, contribution_id: str) -> Contribution | None:
        raise NotImplementedError("TODO(A5)")

    async def list_contributions(
        self, *, status: ContributionStatus | None = None
    ) -> list[Contribution]:
        raise NotImplementedError("TODO(A5)")

    async def update_contribution(self, contribution: Contribution) -> None:
        raise NotImplementedError("TODO(A5)")

    async def add_confirmation(self, confirmation: Confirmation) -> None:
        raise NotImplementedError("TODO(A5) : insérer, puis mettre à jour le compteur de la cible")
