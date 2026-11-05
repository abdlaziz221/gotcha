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
from app.stores.postgres.release import ReleaseReport, SeedReport, release
from tests.conftest import TEST_CONTENT_DIR

pytestmark = [pytest.mark.anyio, pytest.mark.postgres]

DROP_ALL = (
    "DROP TABLE IF EXISTS schema_migrations, fiches, gotchas, fiche_revisions, glossary_terms,"
    " confirmations, contributions, incidents, ingest_runs, accounts, oauth_clients,"
    " oauth_grants CASCADE"
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
    assert report.seed.retired == ("demo-pay-sn",)

    shutil.rmtree(content / "fiches")
    (content / "fiches").mkdir()
    with pytest.raises(ContentError, match="aucune fiche"):
        await release(empty_database, migrations_dir=ROOT_DIR / "migrations", content_dir=content)
