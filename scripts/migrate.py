"""Applique les migrations SQL de migrations/ à la base DATABASE_URL.

Usage : DATABASE_URL=postgresql://… python scripts/migrate.py
"""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

import asyncpg

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.stores.postgres.migrate import apply_migrations  # noqa: E402


async def main() -> None:
    url = os.environ.get("DATABASE_URL")
    if not url:
        sys.exit("DATABASE_URL n'est pas défini.")
    conn = await asyncpg.connect(url)
    try:
        done = await apply_migrations(conn, ROOT / "migrations")
    finally:
        await conn.close()
    print("Migrations appliquées : " + (", ".join(done) if done else "aucune, la base est à jour"))


if __name__ == "__main__":
    asyncio.run(main())
