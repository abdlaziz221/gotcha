"""Rafraîchit les flux de pannes une fois : python -m app.ingest

Sur un VPS, à lancer toutes les 10 minutes par une tâche planifiée (cron). Sur le
Serverless, le rafraîchissement se fait à l'ouverture d'une fiche.
"""

from __future__ import annotations

import asyncio

from app.config import Settings
from app.container import build_services


async def main() -> None:
    services = await build_services(Settings.from_env())
    try:
        count = await services.incidents.refresh_if_stale()
        print(f"{count} panne(s) reçue(s)")
    finally:
        await services.close()


if __name__ == "__main__":
    asyncio.run(main())
