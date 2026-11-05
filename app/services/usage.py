"""Compteurs d'usage. Responsable : Abdoul Aziz.

Un compte créé ne veut pas dire un utilisateur actif.

On compte des événements par jour et par compte, jamais le texte d'une recherche.
"""

from __future__ import annotations

import logging
from datetime import timedelta

from app.domain.models import UsageEvent, UsageTotal
from app.domain.ports import Clock, UsageStore

log = logging.getLogger(__name__)


class UsageService:
    def __init__(self, store: UsageStore, clock: Clock) -> None:
        self._store = store
        self._clock = clock

    async def record(self, event: UsageEvent, account_id: str | None = None) -> None:
        """Au mieux : une statistique ne fait jamais échouer l'action qu'elle compte.

        Appelé après une écriture réelle (contribution, confirmation) : une erreur ici
        donnerait un 500 alors que l'écriture a eu lieu, et le visiteur la renverrait.
        """
        try:
            await self._store.add_usage(self._clock.today(), event, account_id)
        except Exception:
            log.warning("compteur d'usage non enregistré (%s)", event.value, exc_info=True)

    async def totals(self, *, days: int = 30) -> list[UsageTotal]:
        return await self._store.usage_totals(self._clock.today() - timedelta(days=days))
