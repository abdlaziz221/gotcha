"""Implémentations du stockage (ports de app/domain/ports.py)."""

from __future__ import annotations

from app.config import Settings
from app.domain.ports import Store


async def create_store(settings: Settings) -> Store:
    """Choisit le stockage selon GOTCHA_STORE : memory (fichiers) ou postgres."""
    if settings.store == "postgres":
        from app.stores.postgres.store import PostgresStore

        if not settings.database_url:
            raise ValueError("GOTCHA_STORE=postgres demande DATABASE_URL")
        return await PostgresStore.connect(settings.database_url)

    from app.stores.memory.store import MemoryStore

    return MemoryStore.from_directories(
        settings.content_dir,
        settings.fixtures_dir if settings.load_fixtures else None,
    )
