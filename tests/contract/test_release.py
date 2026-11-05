"""Mise en service sur PostgreSQL (scripts/release.py), lancée à chaque démarrage du conteneur.

Demande GOTCHA_TEST_DATABASE_URL (base jetable : ses tables sont supprimées).
"""

from __future__ import annotations

import asyncio
import os
import shutil
from pathlib import Path

import asyncpg
import pytest

from app.config import ROOT_DIR
from app.stores.content_files import ContentError
from app.stores.postgres.release import (
    RELEASE_LOCK_ID,
    ReleaseLockTimeoutError,
    ReleaseReport,
    SeedReport,
    release,
)
from tests.conftest import TEST_CONTENT_DIR

pytestmark = [pytest.mark.anyio, pytest.mark.postgres]

DROP_ALL = (
    "DROP TABLE IF EXISTS schema_migrations, fiches, gotchas, fiche_revisions, glossary_terms,"
    " confirmations, contributions, incidents, ingest_runs, accounts, oauth_clients,"
    " oauth_grants, content_release CASCADE"
)


@pytest.fixture
async def empty_database() -> str:
    url = os.environ.get("GOTCHA_TEST_DATABASE_URL")
    if not url:
        pytest.skip("GOTCHA_TEST_DATABASE_URL non défini")
    conn = await asyncpg.connect(url)
    try:
        await conn.execute(DROP_ALL)
    finally:
        await conn.close()
    return url


async def _release(url: str) -> ReleaseReport:
    return await release(url, migrations_dir=ROOT_DIR / "migrations", content_dir=TEST_CONTENT_DIR)


async def test_first_release_creates_schema_and_loads_content(empty_database: str) -> None:
    report = await _release(empty_database)
    assert report.migrations == ["001_init", "002_comptes_oauth"]
    assert report.seed == SeedReport(fiches=2, gotchas=2, terms=2)

    again = await _release(empty_database)
    assert again.migrations == []
    assert again.seed == report.seed


async def test_instances_starting_together_do_not_collide(empty_database: str) -> None:
    reports = await asyncio.gather(*(_release(empty_database) for _ in range(3)))
    assert sorted(len(r.migrations) for r in reports) == [0, 0, 2]
    conn = await asyncpg.connect(empty_database)
    try:
        assert await conn.fetchval("SELECT count(*) FROM fiches") == 2
        # Un seul historique par fiche : les chargements suivants n'ont rien changé.
        assert await conn.fetchval("SELECT count(*) FROM fiche_revisions") == 2
    finally:
        await conn.close()


async def test_release_retires_fiches_deleted_from_content(
    empty_database: str, tmp_path: Path
) -> None:
    await _release(empty_database)
    content = tmp_path / "content"
    shutil.copytree(TEST_CONTENT_DIR, content)
    shutil.rmtree(content / "fiches" / "demo-pay-sn")
    report = await release(
        empty_database, migrations_dir=ROOT_DIR / "migrations", content_dir=content
    )
    assert report.seed is not None
    assert report.seed.retired == ("demo-pay-sn",)

    shutil.rmtree(content / "fiches")
    (content / "fiches").mkdir()
    with pytest.raises(ContentError, match="aucune fiche"):
        await release(empty_database, migrations_dir=ROOT_DIR / "migrations", content_dir=content)


async def test_invalid_content_stops_before_touching_the_database(
    empty_database: str, tmp_path: Path
) -> None:
    content = tmp_path / "content"
    shutil.copytree(TEST_CONTENT_DIR, content)
    (content / "glossaire.yml").unlink()
    with pytest.raises(ContentError, match="aucun terme"):
        await release(empty_database, migrations_dir=ROOT_DIR / "migrations", content_dir=content)
    conn = await asyncpg.connect(empty_database)
    try:
        assert await conn.fetchval("SELECT to_regclass('schema_migrations')") is None
    finally:
        await conn.close()


async def test_a_stuck_lock_stops_the_release_with_a_clear_message(empty_database: str) -> None:
    holder = await asyncpg.connect(empty_database)
    try:
        await holder.execute("SELECT pg_advisory_lock($1)", RELEASE_LOCK_ID)
        with pytest.raises(ReleaseLockTimeoutError, match="pg_terminate_backend"):
            await release(
                empty_database,
                migrations_dir=ROOT_DIR / "migrations",
                content_dir=TEST_CONTENT_DIR,
                lock_wait_seconds=0.3,
            )
    finally:
        await holder.close()


async def test_an_older_image_does_not_reload_its_content(
    empty_database: str, tmp_path: Path
) -> None:
    async def start(content_dir: Path, built_at: int) -> ReleaseReport:
        return await release(
            empty_database,
            migrations_dir=ROOT_DIR / "migrations",
            content_dir=content_dir,
            built_at=built_at,
        )

    old = tmp_path / "ancien"
    shutil.copytree(TEST_CONTENT_DIR, old)
    shutil.rmtree(old / "fiches" / "demo-pay-sn")
    assert (await start(TEST_CONTENT_DIR, built_at=200)).seed is not None

    # L'ancienne image redémarre : sans garde-fou, elle retirerait demo-pay-sn.
    stale = await start(old, built_at=100)
    assert stale.seed is None
    assert stale.newer_build == 200
    conn = await asyncpg.connect(empty_database)
    try:
        query = "SELECT publication FROM fiches WHERE slug = 'demo-pay-sn'"
        assert await conn.fetchval(query) == "published"
        # Une nouvelle image (même un retour en arrière volontaire, reconstruit) s'applique.
        assert (await start(old, built_at=300)).seed is not None
        assert await conn.fetchval(query) == "draft"
    finally:
        await conn.close()
