"""Mise en service d'une version : schéma à jour, puis contenu de content/ chargé en base.

Lancé à chaque démarrage du conteneur (scripts/release.py, voir le Dockerfile) : la base
suit toujours le contenu livré dans l'image, sans accès à la base depuis nos postes.

- Le contenu est lu et vérifié **avant** de toucher à la base : un fichier invalide
  arrête la mise en service sans migration ni écriture.
- Un verrou PostgreSQL empêche deux instances de le faire en même temps ; l'attente est
  bornée, avec un message clair, au lieu de bloquer le démarrage sans fin.
- Une image plus ancienne que celle déjà en service (date de construction, fichier
  BUILD_TIME écrit par le Dockerfile) ne recharge pas son contenu : une instance qui
  redémarre sur l'ancienne version ne remet pas l'ancien texte en ligne.
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from pathlib import Path

import asyncpg

from app.domain.models import Fiche, GlossaryTerm
from app.domain.ports import Store
from app.stores.content_files import ContentError, load_fiches, load_glossary
from app.stores.postgres.migrate import apply_migrations
from app.stores.postgres.store import PostgresStore

# Identifiant arbitraire du verrou consultatif (pg_advisory_lock), propre à Gotcha.
RELEASE_LOCK_ID = 7_246_810
# Une mise en service prend quelques secondes : au-delà, une session bloquée tient le verrou.
LOCK_WAIT_SECONDS = 120.0


class ReleaseLockTimeoutError(RuntimeError):
    """Une autre session tient le verrou de mise en service depuis trop longtemps."""


@dataclass(frozen=True)
class Content:
    fiches: list[Fiche]
    glossary: list[GlossaryTerm]


@dataclass(frozen=True)
class SeedReport:
    fiches: int
    gotchas: int
    terms: int
    retired: tuple[str, ...] = ()  # fiches absentes de content/, repassées en brouillon


@dataclass(frozen=True)
class ReleaseReport:
    migrations: list[str]
    seed: SeedReport | None  # None : contenu non rechargé (image plus ancienne)
    newer_build: int | None = None  # date de construction de l'image déjà en service


def load_content(content_dir: Path) -> Content:
    """Lit et vérifie tout le contenu ; ne touche à aucune base."""
    fiches = load_fiches(content_dir)
    if not fiches:
        # Sinon retire_fiches dépublierait tout le site.
        raise ContentError(f"{content_dir / 'fiches'} : aucune fiche, chargement annulé")
    glossary = load_glossary(content_dir)
    if not glossary:
        # upsert_glossary remplace tout : une liste vide effacerait le glossaire en ligne.
        raise ContentError(f"{content_dir / 'glossaire.yml'} : aucun terme, chargement annulé")
    return Content(fiches=fiches, glossary=glossary)


async def seed_content(store: Store, content: Content | Path) -> SeedReport:
    """Charge les fiches et le glossaire ; garde les confirmations reçues sur le site.

    Les fiches retirées de content/ repassent en brouillon, et le glossaire est remplacé.
    """
    if isinstance(content, Path):
        content = load_content(content)
    for fiche in content.fiches:
        await store.upsert_fiche(fiche)
    retired = await store.retire_fiches([f.slug for f in content.fiches])
    await store.upsert_glossary(content.glossary)
    return SeedReport(
        fiches=len(content.fiches),
        gotchas=sum(len(f.gotchas) for f in content.fiches),
        terms=len(content.glossary),
        retired=tuple(retired),
    )


async def _take_lock(conn: asyncpg.Connection, wait_seconds: float) -> None:
    """Verrou de session : libéré à la fermeture de la connexion, même en cas d'erreur."""
    deadline = time.monotonic() + wait_seconds
    while not await conn.fetchval("SELECT pg_try_advisory_lock($1)", RELEASE_LOCK_ID):
        if time.monotonic() >= deadline:
            raise ReleaseLockTimeoutError(
                f"Une autre session tient le verrou de mise en service ({RELEASE_LOCK_ID})"
                f" depuis plus de {wait_seconds:.0f} s : démarrage abandonné. Si aucune autre"
                " instance ne démarre, une session PostgreSQL bloquée le garde : la repérer"
                " dans pg_locks (objid = ce numéro) et la fermer avec pg_terminate_backend."
            )
        await asyncio.sleep(min(1.0, wait_seconds))


async def release(
    database_url: str,
    *,
    migrations_dir: Path,
    content_dir: Path,
    built_at: int | None = None,
    lock_wait_seconds: float = LOCK_WAIT_SECONDS,
) -> ReleaseReport:
    """built_at : date de construction de l'image (secondes Unix), None hors image Docker."""
    content = load_content(content_dir)  # un contenu invalide échoue ici, base intacte
    conn = await asyncpg.connect(database_url)
    try:
        await _take_lock(conn, lock_wait_seconds)
        migrations = await apply_migrations(conn, migrations_dir)
        in_service = await conn.fetchval("SELECT built_at FROM content_release WHERE id = 1")
        if built_at is not None and in_service is not None and built_at < in_service:
            return ReleaseReport(migrations=migrations, seed=None, newer_build=in_service)
        store = await PostgresStore.connect(database_url)
        try:
            seed = await seed_content(store, content)
        finally:
            await store.close()
        if built_at is not None:
            await conn.execute(
                "INSERT INTO content_release (id, built_at) VALUES (1, $1)"
                " ON CONFLICT (id) DO UPDATE SET built_at = EXCLUDED.built_at, applied_at = now()",
                built_at,
            )
    finally:
        await conn.close()
    return ReleaseReport(migrations=migrations, seed=seed)
