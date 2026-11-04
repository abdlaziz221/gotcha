"""Compteurs d'usage. Responsable : Abdoul Aziz.

Un compte créé ne veut pas dire un utilisateur actif.

On compte des événements par jour et par compte, jamais le texte d'une recherche.
"""

from __future__ import annotations

from datetime import timedelta

from app.domain.models import UsageEvent, UsageTotal
from app.domain.ports import Clock, UsageStore


class UsageService:
    def __init__(self, store: UsageStore, clock: Clock) -> None:
        self._store = store
        self._clock = clock

    async def record(self, event: UsageEvent, account_id: str | None = None) -> None:
        await self._store.add_usage(self._clock.today(), event, account_id)

    async def totals(self, *, days: int = 30) -> list[UsageTotal]:
        return await self._store.usage_totals(self._clock.today() - timedelta(days=days))
