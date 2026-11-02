"""Application des migrations SQL de migrations/, dans l'ordre, une seule fois chacune."""

from __future__ import annotations

from pathlib import Path

import asyncpg


async def apply_migrations(conn: asyncpg.Connection, directory: Path) -> list[str]:
    """Applique les fichiers NNN_nom.sql pas encore appliqués ; renvoie leurs noms."""
    await conn.execute(
        "CREATE TABLE IF NOT EXISTS schema_migrations ("
        " version text PRIMARY KEY,"
        " applied_at timestamptz NOT NULL DEFAULT now())"
    )
    applied = {row["version"] for row in await conn.fetch("SELECT version FROM schema_migrations")}
    done = []
    # Quelques petits fichiers lus au démarrage : la lecture bloquante est acceptable ici.
    scripts = [(p.stem, p.read_text(encoding="utf-8")) for p in sorted(directory.glob("*.sql"))]  # noqa: ASYNC240
    for version, sql in scripts:
        if version in applied:
            continue
        async with conn.transaction():
            await conn.execute(sql)
            await conn.execute("INSERT INTO schema_migrations (version) VALUES ($1)", version)
        done.append(version)
    return done
