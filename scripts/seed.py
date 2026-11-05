"""Charge content/ (fiches, pièges, glossaire) dans la base PostgreSQL DATABASE_URL.

Usage : DATABASE_URL=postgresql://… python scripts/seed.py
À lancer après scripts/migrate.py. En production, inutile : scripts/release.py le fait
à chaque démarrage du conteneur.
"""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.stores.postgres.release import seed_content  # noqa: E402
from app.stores.postgres.store import PostgresStore  # noqa: E402


async def main() -> None:
    url = os.environ.get("DATABASE_URL")
    if not url:
        sys.exit("DATABASE_URL n'est pas défini.")
    store = await PostgresStore.connect(url)
    try:
        report = await seed_content(store, ROOT / "content")
    finally:
        await store.close()
    print(f"{report.fiches} fiche(s), {report.gotchas} piège(s), {report.terms} terme(s) chargés.")
    if report.retired:
        print("Repassées en brouillon (absentes de content/) : " + ", ".join(report.retired))


if __name__ == "__main__":
    asyncio.run(main())
