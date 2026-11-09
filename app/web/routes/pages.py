"""Accueil, recherche, glossaire et page « Où sont vos données »."""

from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Request
from starlette.responses import Response

from app.domain.countries import country_name
from app.domain.models import SearchHitKind
from app.web.deps import ServicesDep, flash_from
from app.web.labels import SEARCH_HIT_LABELS
from app.web.presenters import fiche_card, fiche_url, incident_view, service_names
from app.web.session import current_account
from app.web.templating import render
from app.web.viewmodels import (
    ConnectPage,
    GlossaryPage,
    HomePage,
    Option,
    PageMeta,
    SearchHitView,
    SearchPage,
    StaticPage,
)

router = APIRouter()


@router.get("/")
async def home(request: Request, services: ServicesDep, background: BackgroundTasks) -> Response:
    background.add_task(services.incidents.refresh_if_stale)
    fiches = await services.fiches.list()
    statuses = await services.incidents.statuses_for(fiches)
    names = service_names(fiches)
    now = services.clock.now()
    recent = await services.incidents.recent(active_only=True, limit=30)
    active = [v for v in (incident_view(i, names, now) for i in recent) if v.is_active]
    page = HomePage(
        meta=PageMeta(title="Gotcha, ce que les devs ont déjà résolu en Afrique", path="/"),
        cards=[
            fiche_card(f, statuses[f.slug], names, needs_review=services.fiches.needs_review(f))
            for f in fiches
        ],
        active_incidents=active[:5],
        gotcha_total=sum(len(f.gotchas) for f in fiches),
        flash=flash_from(request),
    )
    return render(request, "pages/home.html", page)


@router.get("/recherche")
async def search(
    request: Request, services: ServicesDep, q: str = "", service: str = "", pays: str = ""
) -> Response:
    fiches = await services.fiches.list()
    hits = []
    if q or service or pays:
        hits = await services.fiches.search(q, service=service or None, country=pays or None)
    countries = sorted({f.country for f in fiches if f.country}, key=country_name)
    locked = services.settings.site_auth and current_account(request) is None
    opened = {f.slug for f in fiches if f.open_access}
    titles = {f.slug: f.title for f in fiches}
    page = SearchPage(
        meta=PageMeta(title="Rechercher un piège", path="/recherche"),
        query=q,
        hits=[
            SearchHitView(
                kind=h.kind,
                kind_label=SEARCH_HIT_LABELS[h.kind],
                title=h.title,
                snippet=(
                    "Réservé aux membres : compte gratuit, connexion avec GitHub."
                    if locked and h.kind is SearchHitKind.ERROR_CODE and h.fiche_slug not in opened
                    else h.snippet
                ),
                url=fiche_url(h.fiche_slug) + (f"#{h.anchor}" if h.anchor else ""),
                fiche_title=titles.get(h.fiche_slug, ""),
            )
            for h in hits
        ],
        service_options=[
            Option(s.slug, s.name, s.slug == service) for s in await services.fiches.services()
        ],
        country_options=[Option(c, country_name(c), c == pays) for c in countries],
    )
    return render(request, "pages/search.html", page)


@router.get("/brancher")
async def connect(request: Request, services: ServicesDep) -> Response:
    page = ConnectPage(
        meta=PageMeta(
            title="Brancher votre agent",
            path="/brancher",
            description="Ajouter le serveur MCP de Gotcha à votre agent de codage.",
        ),
        login_required=services.settings.mcp_auth,
        mcp_url=f"{services.settings.site_url}/mcp",
    )
    return render(request, "pages/connect.html", page)


@router.get("/glossaire")
async def glossary(request: Request, services: ServicesDep) -> Response:
    page = GlossaryPage(
        meta=PageMeta(title="Glossaire", path="/glossaire"),
        terms=await services.fiches.glossary(),
    )
    return render(request, "pages/glossary.html", page)


@router.get("/ou-sont-vos-donnees")
async def data_location(request: Request) -> Response:
    page = StaticPage(meta=PageMeta(title="Où sont vos données", path="/ou-sont-vos-donnees"))
    return render(request, "pages/data.html", page)
