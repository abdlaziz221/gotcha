"""Stockage en mémoire : la référence de comportement pour PostgresStore.

Les fiches viennent de content/, les pannes et contributions fictives de fixtures/.
Tout ce qui est écrit pendant l'exécution est perdu au redémarrage.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

from app.domain.models import (
    Confirmation,
    Contribution,
    ContributionStatus,
    Fiche,
    GlossaryTerm,
    Gotcha,
    Incident,
    IncidentSource,
    SearchHit,
    SearchQuery,
    TargetKind,
)
from app.stores.content_files import load_fiches, load_glossary
from app.stores.search import (
    keep_confirmations,
    search_fiches,
    sort_fiches,
    sort_glossary,
    visible,
)


def _fixture_incident(item: dict[str, object], now: datetime) -> Incident:
    """Panne fictive ; « minutes_ago » remplace started_at pour rester toujours récente."""
    data = dict(item)
    minutes_ago = data.pop("minutes_ago", None)
    if minutes_ago is not None:
        data["started_at"] = now - timedelta(minutes=int(str(minutes_ago)))
    return Incident.model_validate(data)


class MemoryStore:
    def __init__(
        self,
        fiches: list[Fiche],
        glossary: list[GlossaryTerm],
        incidents: list[Incident] | None = None,
        contributions: list[Contribution] | None = None,
    ) -> None:
        self._fiches = {f.slug: f for f in fiches}
        self._glossary = {t.slug: t for t in glossary}
        self._incidents = {i.id: i for i in incidents or []}
        self._contributions = {c.id: c for c in contributions or []}
        self._confirmations: list[Confirmation] = []
        self._last_ingest: dict[IncidentSource, datetime] = {}

    @classmethod
    def from_directories(
        cls, content_dir: Path, fixtures_dir: Path | None = None, *, now: datetime | None = None
    ) -> MemoryStore:
        incidents: list[Incident] = []
        contributions: list[Contribution] = []
        if fixtures_dir is not None:
            now = now or datetime.now(UTC)
            incidents_file = fixtures_dir / "incidents_communaute.json"
            if incidents_file.exists():
                data = json.loads(incidents_file.read_text(encoding="utf-8"))
                incidents = [_fixture_incident(item, now) for item in data["incidents"]]
            contributions_file = fixtures_dir / "contributions.json"
            if contributions_file.exists():
                data = json.loads(contributions_file.read_text(encoding="utf-8"))
                contributions = [Contribution(**item) for item in data["contributions"]]
        return cls(load_fiches(content_dir), load_glossary(content_dir), incidents, contributions)

    # --- FicheStore ----------------------------------------------------------

    async def list_fiches(self, *, include_drafts: bool = False) -> list[Fiche]:
        shown = [visible(f, include_drafts=include_drafts) for f in self._fiches.values()]
        return sort_fiches(f for f in shown if f)

    async def get_fiche(self, slug: str, *, include_drafts: bool = False) -> Fiche | None:
        fiche = self._fiches.get(slug)
        return visible(fiche, include_drafts=include_drafts) if fiche else None

    async def search(self, query: SearchQuery, *, include_drafts: bool = False) -> list[SearchHit]:
        return search_fiches(await self.list_fiches(include_drafts=include_drafts), query)

    async def list_glossary(self) -> list[GlossaryTerm]:
        return sort_glossary(self._glossary.values())

    async def upsert_fiche(self, fiche: Fiche) -> None:
        self._fiches[fiche.slug] = keep_confirmations(fiche, self._fiches.get(fiche.slug))

    async def upsert_glossary(self, terms: list[GlossaryTerm]) -> None:
        for term in terms:
            self._glossary[term.slug] = term

    # --- IncidentStore -------------------------------------------------------

    async def list_incidents(
        self,
        *,
        service_slug: str | None = None,
        country: str | None = None,
        active_only: bool = False,
        limit: int = 100,
    ) -> list[Incident]:
        selected = [
            i
            for i in self._incidents.values()
            if (service_slug is None or i.service_slug == service_slug)
            and (country is None or i.country == country)
            and (not active_only or i.is_active)
        ]
        selected.sort(key=lambda i: i.started_at, reverse=True)
        return selected[:limit]

    async def upsert_incident(self, incident: Incident) -> None:
        self._incidents[incident.id] = incident

    async def get_last_ingest(self, source: IncidentSource) -> datetime | None:
        return self._last_ingest.get(source)

    async def set_last_ingest(self, source: IncidentSource, at: datetime) -> None:
        self._last_ingest[source] = at

    # --- ContributionStore ---------------------------------------------------

    async def add_contribution(self, contribution: Contribution) -> None:
        self._contributions[contribution.id] = contribution

    async def get_contribution(self, contribution_id: str) -> Contribution | None:
        return self._contributions.get(contribution_id)

    async def list_contributions(
        self, *, status: ContributionStatus | None = None
    ) -> list[Contribution]:
        selected = [c for c in self._contributions.values() if status is None or c.status is status]
        return sorted(selected, key=lambda c: c.created_at)

    async def update_contribution(self, contribution: Contribution) -> None:
        self._contributions[contribution.id] = contribution

    async def add_confirmation(self, confirmation: Confirmation) -> None:
        self._confirmations.append(confirmation)
        if not confirmation.still_works:
            return
        day = confirmation.created_at.date()
        fiche_slug = confirmation.target_id.split(".", 1)[0]
        fiche = self._fiches.get(fiche_slug)
        if fiche is None:
            return
        if confirmation.target_kind is TargetKind.FICHE:
            self._fiches[fiche_slug] = fiche.model_copy(
                update={
                    "confirmations": fiche.confirmations + 1,
                    "last_confirmed_on": max(fiche.last_confirmed_on, day),
                }
            )
            return
        gotchas: list[Gotcha] = [
            g.model_copy(
                update={
                    "confirmations": g.confirmations + 1,
                    "last_confirmed_on": max(g.last_confirmed_on, day),
                }
            )
            if g.id == confirmation.target_id
            else g
            for g in fiche.gotchas
        ]
        self._fiches[fiche_slug] = fiche.model_copy(update={"gotchas": gotchas})

    async def close(self) -> None:
        return None
