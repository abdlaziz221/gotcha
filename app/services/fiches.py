"""Lecture des fiches, recherche et glossaire. Responsable : Abdoul Aziz."""

from __future__ import annotations

from app.domain.errors import NotFoundError
from app.domain.models import (
    Fiche,
    GlossaryTerm,
    Gotcha,
    SearchHit,
    SearchQuery,
    Service,
    is_storable,
)
from app.domain.ports import Clock, FicheStore
from app.services.freshness import needs_review


class FicheService:
    def __init__(self, store: FicheStore, clock: Clock, *, include_drafts: bool) -> None:
        self._store = store
        self._clock = clock
        self.include_drafts = include_drafts

    async def list(self) -> list[Fiche]:
        return await self._store.list_fiches(include_drafts=self.include_drafts)

    async def get(self, slug: str) -> Fiche:
        fiche = await self._store.get_fiche(slug, include_drafts=self.include_drafts)
        if fiche is None:
            raise NotFoundError(f"Fiche introuvable : {slug}")
        return fiche

    async def find(self, service_slug: str, country: str | None = None) -> Fiche:
        """La fiche d'un service dans un pays ; à défaut, sa fiche valable dans tous les pays."""
        country = country.upper() if country else None
        same_service = [f for f in await self.list() if f.service.slug == service_slug]
        for fiche in same_service:
            if fiche.country == country:
                return fiche
        if country is None and len(same_service) == 1:
            return same_service[0]
        for fiche in same_service:
            if fiche.country is None:
                return fiche
        where = f" ({country})" if country else ""
        raise NotFoundError(f"Aucune fiche pour le service {service_slug}{where}")

    async def services(self) -> list[Service]:
        seen: dict[str, Service] = {}
        for fiche in await self.list():
            seen.setdefault(fiche.service.slug, fiche.service)
        return sorted(seen.values(), key=lambda s: s.name.lower())

    async def search(
        self,
        text: str,
        *,
        service: str | None = None,
        country: str | None = None,
        limit: int = 20,
    ) -> list[SearchHit]:
        if not all(is_storable(value) for value in (text, service or "", country or "")):
            # Aucun texte enregistré ne contient ces caractères : rien ne peut correspondre.
            # Le modèle les refuse, la page de recherche répondrait sinon par une erreur 500.
            return []
        query = SearchQuery(
            text=text.strip()[:200],
            service=service or None,
            country=country.upper() if country else None,
            limit=limit,
        )
        return await self._store.search(query, include_drafts=self.include_drafts)

    async def glossary(self) -> list[GlossaryTerm]:
        return await self._store.list_glossary()

    def needs_review(self, item: Fiche | Gotcha) -> bool:
        return needs_review(item.last_confirmed_on, self._clock.today())
