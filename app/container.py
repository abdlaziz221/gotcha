"""Assemblage de l'application : choisit le stockage et construit les services.

C'est le seul endroit qui connaît les implémentations concrètes. Le web, le
serveur MCP et l'import des pannes ne reçoivent que des objets Services.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta

from app.config import Settings
from app.domain.ports import Clock, IncidentFeed, Store
from app.ingest.flutterwave import FlutterwaveFeed
from app.security.secrets import scan_text
from app.services.clock import SystemClock
from app.services.contributions import ContributionService
from app.services.fiches import FicheService
from app.services.incidents import IncidentService
from app.stores import create_store


@dataclass
class Services:
    settings: Settings
    store: Store
    clock: Clock
    fiches: FicheService
    incidents: IncidentService
    contributions: ContributionService

    async def close(self) -> None:
        await self.store.close()


async def build_services(
    settings: Settings,
    *,
    clock: Clock | None = None,
    store: Store | None = None,
    feeds: list[IncidentFeed] | None = None,
) -> Services:
    """Construit tous les services.

    Les tests peuvent remplacer l'horloge, le stockage ou les flux de pannes.
    """
    clock = clock or SystemClock()
    store = store or await create_store(settings)
    if feeds is None:
        feeds = [
            FlutterwaveFeed(
                url=settings.flutterwave_feed_url,
                live=settings.ingest_live,
                fixture_path=settings.fixtures_dir / "flutterwave_incidents.json",
            )
        ]
    fiches = FicheService(store, clock, include_drafts=settings.show_drafts)
    incidents = IncidentService(
        store,
        clock,
        fiches,
        feeds=feeds,
        min_interval=timedelta(minutes=settings.ingest_min_interval_minutes),
    )
    contributions = ContributionService(store, fiches, clock, scan=scan_text)
    return Services(settings, store, clock, fiches, incidents, contributions)
