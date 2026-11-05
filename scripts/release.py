"""Prépare la base avant le démarrage du site : migrations, puis chargement de content/.

Usage : python scripts/release.py (lancé par le Dockerfile avant uvicorn).
Avec le stockage mémoire (GOTCHA_STORE=memory), il n'y a rien à préparer.
Sans danger si plusieurs instances démarrent ensemble : un verrou PostgreSQL les met en file.
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.config import Settings  # noqa: E402
from app.stores.postgres.release import release  # noqa: E402


async def main() -> None:
    settings = Settings.from_env()
    if settings.store != "postgres" or not settings.database_url:
        print("Stockage mémoire : aucune base à préparer.")
        return
    report = await release(
        settings.database_url, migrations_dir=ROOT / "migrations", content_dir=settings.content_dir
    )
    migrations = ", ".join(report.migrations) if report.migrations else "aucune, la base est à jour"
    seed = report.seed
    print(f"Migrations appliquées : {migrations}")
    print(f"{seed.fiches} fiche(s), {seed.gotchas} piège(s), {seed.terms} terme(s) chargés.")
    if seed.retired:
        print("Repassées en brouillon (absentes de content/) : " + ", ".join(seed.retired))


if __name__ == "__main__":
    asyncio.run(main())
