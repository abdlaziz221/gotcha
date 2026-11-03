"""Mise en service d'une version : schéma à jour, puis contenu de content/ chargé en base.

Lancé à chaque démarrage du conteneur (scripts/release.py, voir le Dockerfile) : la base
suit toujours le contenu livré dans l'image, sans accès à la base depuis nos postes.
Un verrou PostgreSQL empêche deux instances de le faire en même temps.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import asyncpg

from app.domain.ports import Store
from app.stores.content_files import load_fiches, load_glossary
from app.stores.postgres.migrate import apply_migrations
from app.stores.postgres.store import PostgresStore

# Identifiant arbitraire du verrou consultatif (pg_advisory_lock), propre à Gotcha.
RELEASE_LOCK_ID = 7_246_810


@dataclass(frozen=True)
class SeedReport:
    fiches: int
    gotchas: int
    terms: int


@dataclass(frozen=True)
class ReleaseReport:
    migrations: list[str]
    seed: SeedReport


async def seed_content(store: Store, content_dir: Path) -> SeedReport:
    """Charge les fiches et le glossaire ; garde les confirmations reçues sur le site."""
    fiches = load_fiches(content_dir)
    glossary = load_glossary(content_dir)
    for fiche in fiches:
        await store.upsert_fiche(fiche)
    await store.upsert_glossary(glossary)
    return SeedReport(
        fiches=len(fiches), gotchas=sum(len(f.gotchas) for f in fiches), terms=len(glossary)
    )


async def release(database_url: str, *, migrations_dir: Path, content_dir: Path) -> ReleaseReport:
    conn = await asyncpg.connect(database_url)
    try:
        # Verrou de session : libéré à la fermeture de la connexion, même en cas d'erreur.
        await conn.execute("SELECT pg_advisory_lock($1)", RELEASE_LOCK_ID)
        migrations = await apply_migrations(conn, migrations_dir)
        store = await PostgresStore.connect(database_url)
        try:
            seed = await seed_content(store, content_dir)
        finally:
            await store.close()
    finally:
        await conn.close()
    return ReleaseReport(migrations=migrations, seed=seed)
