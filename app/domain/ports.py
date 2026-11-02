"""Ports : ce que le reste du code attend du stockage, de l'horloge et des flux de pannes.

CONTRAT PARTAGÉ. Le stockage a deux implémentations : app/stores/memory (fichiers,
pour développer sans base) et app/stores/postgres (production). Les tests de
tests/contract/ vérifient que les deux se comportent exactement pareil.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Protocol

from app.domain.models import (
    Confirmation,
    Contribution,
    ContributionStatus,
    Fiche,
    GlossaryTerm,
    Incident,
    IncidentSource,
    SearchHit,
    SearchQuery,
)


class Clock(Protocol):
    def now(self) -> datetime:
        """Heure actuelle, avec fuseau, en UTC (c'est aussi l'heure de Dakar)."""
        ...

    def today(self) -> date: ...


class FicheStore(Protocol):
    """Fiches, pièges et glossaire.

    include_drafts=False : seules les fiches publiées sont renvoyées, et elles ne
    contiennent que leurs pièges publiés. C'est le mode de la production.
    """

    async def list_fiches(self, *, include_drafts: bool = False) -> list[Fiche]:
        """Toutes les fiches, triées par titre."""
        ...

    async def get_fiche(self, slug: str, *, include_drafts: bool = False) -> Fiche | None: ...

    async def search(self, query: SearchQuery, *, include_drafts: bool = False) -> list[SearchHit]:
        """Recherche dans les titres, résumés, pièges et codes d'erreur.

        Résultats triés par score décroissant, au plus query.limit. Insensible à la
        casse et aux accents. Filtre sur query.service et query.country s'ils sont
        donnés.
        """
        ...

    async def list_glossary(self) -> list[GlossaryTerm]:
        """Tous les termes, triés par terme."""
        ...

    async def upsert_fiche(self, fiche: Fiche) -> None:
        """Crée ou remplace une fiche et ses pièges (utilisé par scripts/seed.py).

        Les pièges absents de la nouvelle version sont supprimés, l'ordre des pièges
        est conservé. Les compteurs de confirmation déjà enregistrés sont gardés
        (les fichiers de content/ ne les connaissent pas), et last_confirmed_on garde
        la date la plus récente.
        """
        ...

    async def upsert_glossary(self, terms: list[GlossaryTerm]) -> None: ...


class IncidentStore(Protocol):
    async def list_incidents(
        self,
        *,
        service_slug: str | None = None,
        country: str | None = None,
        active_only: bool = False,
        limit: int = 100,
    ) -> list[Incident]:
        """Pannes triées de la plus récente à la plus ancienne (started_at décroissant)."""
        ...

    async def upsert_incident(self, incident: Incident) -> None:
        """Crée ou remplace une panne. Idempotent sur incident.id."""
        ...

    async def get_last_ingest(self, source: IncidentSource) -> datetime | None:
        """Date de la dernière lecture réussie d'un flux de pannes."""
        ...

    async def set_last_ingest(self, source: IncidentSource, at: datetime) -> None: ...


class ContributionStore(Protocol):
    async def add_contribution(self, contribution: Contribution) -> None: ...

    async def get_contribution(self, contribution_id: str) -> Contribution | None: ...

    async def list_contributions(
        self, *, status: ContributionStatus | None = None
    ) -> list[Contribution]:
        """Contributions triées de la plus ancienne à la plus récente (file de relecture)."""
        ...

    async def update_contribution(self, contribution: Contribution) -> None: ...

    async def add_confirmation(self, confirmation: Confirmation) -> None:
        """Enregistre une confirmation.

        Si still_works est vrai, la cible (fiche ou piège) voit ensuite son compteur
        confirmations augmenter de 1 et last_confirmed_on passer à la date de la
        confirmation.
        """
        ...


class Store(FicheStore, IncidentStore, ContributionStore, Protocol):
    """Le stockage complet. Choisi au démarrage selon GOTCHA_STORE (memory ou postgres)."""

    async def close(self) -> None: ...


class IncidentFeed(Protocol):
    """Un flux de pannes externe (aujourd'hui : Flutterwave)."""

    source: IncidentSource

    async def fetch(self) -> list[Incident]:
        """Lit le flux et le traduit en pannes Gotcha. Lève une exception en cas d'échec."""
        ...
