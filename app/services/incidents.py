"""Pannes : état des services, signalements et rafraîchissement des flux. Responsable : Khalifa."""

from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime, timedelta

from app.domain.errors import InvalidInputError
from app.domain.models import (
    Fiche,
    Incident,
    OutageReport,
    Service,
    ServiceKind,
    ServiceStatus,
    Status,
)
from app.domain.ports import Clock, IncidentFeed, IncidentStore
from app.services.fiches import FicheService
from app.services.status import compute_status

log = logging.getLogger(__name__)

# Après un échec, un flux n'est pas relu avant ce délai : sans lui, chaque visite ou appel
# d'agent relisait un flux en panne, avec jusqu'à 5 secondes d'attente à chaque fois.
RETRY_AFTER_FAILURE = timedelta(minutes=2)


class IncidentService:
    def __init__(
        self,
        store: IncidentStore,
        clock: Clock,
        fiches: FicheService,
        *,
        feeds: list[IncidentFeed],
        min_interval: timedelta,
    ) -> None:
        self._store = store
        self._clock = clock
        self._fiches = fiches
        self._feeds = feeds
        self._min_interval = min_interval
        self._lock = asyncio.Lock()
        self._retry_after: dict[int, datetime] = {}  # par flux (id de l'objet)
        # Tâches lancées par refresh_in_background : sans référence, Python peut les arrêter.
        self._background: set[asyncio.Task[int]] = set()

    async def status_for(self, fiche: Fiche) -> ServiceStatus:
        return (await self.statuses_for([fiche]))[fiche.slug]

    async def status_of(self, service: Service, country: str | None) -> ServiceStatus:
        """État d'un service dans un pays précis (utile pour une fiche valable partout)."""
        incidents = await self._store.list_incidents(active_only=True, limit=500)
        return compute_status(
            service.slug,
            country,
            incidents,
            self._clock.now(),
            is_payment=service.kind is ServiceKind.PAYMENT,
        )

    async def statuses_for(self, fiches: list[Fiche]) -> dict[str, ServiceStatus]:
        """État de chaque fiche, indexé par slug, avec une seule lecture des pannes."""
        incidents = await self._store.list_incidents(active_only=True, limit=500)
        now = self._clock.now()
        return {
            f.slug: compute_status(
                f.service.slug,
                f.country,
                incidents,
                now,
                is_payment=f.service.kind is ServiceKind.PAYMENT,
            )
            for f in fiches
        }

    async def recent(
        self,
        *,
        limit: int = 50,
        service_slug: str | None = None,
        country: str | None = None,
        active_only: bool = False,
    ) -> list[Incident]:
        return await self._store.list_incidents(
            service_slug=service_slug, country=country, active_only=active_only, limit=limit
        )

    async def report(self, report: OutageReport) -> Incident:
        """Enregistre un signalement : le service passe en « dégradé » pour quelques heures."""
        services = {s.slug: s for s in await self._fiches.services()}
        service = services.get(report.service_slug)
        if service is None:
            raise InvalidInputError(f"Service inconnu : {report.service_slug}")
        incident = Incident(
            id=f"{report.source.value}:{uuid.uuid4().hex}",
            source=report.source,
            service_slug=service.slug,
            country=report.country,
            status=Status.DEGRADED,
            title=f"Panne signalée : {service.name}",
            description=report.description,
            started_at=self._clock.now(),
            reported_by=report.reported_by,
        )
        await self._store.upsert_incident(incident)
        return incident

    async def refresh_if_stale(self) -> int:
        """Relit les flux lus il y a plus de min_interval ; renvoie le nombre de pannes reçues.

        Ne lève jamais d'exception : un flux ou une base en échec est journalisé et réessayé
        plus tard, et n'empêche pas de lire les autres flux.
        """
        if self._lock.locked():
            # Une lecture est déjà en cours : attendre derrière elle ne servirait à rien.
            return 0
        received = 0
        async with self._lock:
            for feed in self._feeds:
                retry_after = self._retry_after.get(id(feed))
                if retry_after is not None and self._clock.now() < retry_after:
                    continue
                try:
                    received += await self._refresh_feed(feed)
                except Exception:
                    self._retry_after[id(feed)] = self._clock.now() + RETRY_AFTER_FAILURE
                    log.warning("lecture du flux %s impossible", feed.source.value, exc_info=True)
        return received

    def refresh_in_background(self) -> None:
        """Lance refresh_if_stale sans l'attendre : la réponse part avec l'état déjà connu."""
        task = asyncio.create_task(self.refresh_if_stale())
        self._background.add(task)
        task.add_done_callback(self._background.discard)

    async def _refresh_feed(self, feed: IncidentFeed) -> int:
        now = self._clock.now()
        last = await self._store.get_last_ingest(feed.source)
        if last is not None and now - last < self._min_interval:
            return 0
        incidents = await feed.fetch()
        for incident in incidents:
            await self._store.upsert_incident(incident)
        await self._store.set_last_ingest(feed.source, now)
        return len(incidents)
