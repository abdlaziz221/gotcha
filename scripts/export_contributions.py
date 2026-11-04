"""Écrit les contributions approuvées dans content/, en brouillons à relire (tâche A7).

Usage (production) :
  GOTCHA_ENV=prod GOTCHA_MCP_AUTH=false GOTCHA_SITE_AUTH=false DATABASE_URL=… \n  python scripts/export_contributions.py
Ensuite : relire les fichiers créés, les compléter, puis ouvrir une PR `content(<fiche>): …`.

- Un piège devient content/fiches/<fiche>/pieges/contribution-<id>.md (brouillon).
- Une étape ou une correction devient une note dans content/a-integrer/, à reporter à la main.
- Un fichier déjà présent n'est jamais écrasé : on peut relancer le script sans risque.
- L'e-mail du contributeur n'est jamais écrit dans le dépôt.
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.config import Settings  # noqa: E402
from app.domain.models import ContributionStatus  # noqa: E402
from app.stores import create_store  # noqa: E402
from app.stores.content_files import export_contributions  # noqa: E402


async def main() -> None:
    store = await create_store(Settings.from_env())
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
