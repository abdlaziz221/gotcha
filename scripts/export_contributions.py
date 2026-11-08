"""Écrit les contributions approuvées dans content/, en brouillons à relire (tâche A7).

Usage : DATABASE_URL=postgresql://… python scripts/export_contributions.py
Le script lit toujours la base PostgreSQL : sans DATABASE_URL, il s'arrête au lieu de lire
un stockage mémoire vide et d'annoncer « 0 contribution ».
Ensuite : relire les fichiers créés, les compléter, puis ouvrir une PR `content(<fiche>): …`.

- Un piège devient content/fiches/<fiche>/pieges/contribution-<id>.md (brouillon).
- Une étape ou une correction devient une note dans content/a-integrer/, à reporter à la main.
- Chaque export est noté dans content/a-integrer/contributions-exportees.txt (à garder dans
  la PR) : on peut relancer le script sans risque, même après avoir intégré un brouillon.
- L'e-mail du contributeur n'est jamais écrit dans le dépôt.
"""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.domain.models import ContributionStatus  # noqa: E402
from app.stores.content_files import export_contributions  # noqa: E402
from app.stores.postgres.store import PostgresStore  # noqa: E402


async def main() -> None:
    url = os.environ.get("DATABASE_URL")
    if not url:
        sys.exit("DATABASE_URL n'est pas défini : le script lit la base de production.")
    store = await PostgresStore.connect(url)
    try:
        approved = await store.list_contributions(status=ContributionStatus.APPROVED)
    finally:
        await store.close()
    written = export_contributions(approved, ROOT / "content")
    print(f"{len(approved)} contribution(s) approuvée(s), {len(written)} fichier(s) créé(s) :")
    for path in written:
        print(f"  {path.relative_to(ROOT).as_posix()}")


if __name__ == "__main__":
    asyncio.run(main())
