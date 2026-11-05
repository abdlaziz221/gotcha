"""Charge content/ (fiches, pièges, glossaire) dans la base PostgreSQL DATABASE_URL.

Usage : DATABASE_URL=postgresql://… python scripts/seed.py
À lancer après scripts/migrate.py, et à chaque mise à jour du contenu.
Demande PostgresStore.upsert_fiche et upsert_glossary (tâche A6).
"""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.stores.content_files import load_fiches, load_glossary  # noqa: E402
from app.stores.postgres.store import PostgresStore  # noqa: E402


async def main() -> None:
    url = os.environ.get("DATABASE_URL")
    if not url:
        sys.exit("DATABASE_URL n'est pas défini.")
    content_dir = ROOT / "content"
    fiches = load_fiches(content_dir)
    if not fiches:
        # Sinon retire_fiches dépublierait tout le site.
        sys.exit(f"Aucune fiche dans {content_dir / 'fiches'} : chargement annulé.")
    glossary = load_glossary(content_dir)
    store = await PostgresStore.connect(url)
    try:
        for fiche in fiches:
            await store.upsert_fiche(fiche)
        retired = await store.retire_fiches([f.slug for f in fiches])
        await store.upsert_glossary(glossary)
    finally:
        await store.close()
    gotchas = sum(len(f.gotchas) for f in fiches)
    print(f"{len(fiches)} fiche(s), {gotchas} piège(s), {len(glossary)} terme(s) chargés.")
    if retired:
        print("Repassées en brouillon (absentes de content/) : " + ", ".join(retired))


if __name__ == "__main__":
    asyncio.run(main())
