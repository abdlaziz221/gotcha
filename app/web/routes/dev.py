"""Guide de style (/styleguide) : l'atelier de Loum. Introuvable en production."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from starlette.responses import Response

from app.domain.models import Status
from app.web.deps import ServicesDep, glossary_map
from app.web.labels import STATUS_LABELS
from app.web.presenters import fiche_card, gotcha_view, service_names
from app.web.templating import render
from app.web.viewmodels import Flash, FormState, Option, PageMeta, StatusView, StyleguidePage

router = APIRouter()


@router.get("/styleguide")
async def styleguide(request: Request, services: ServicesDep) -> Response:
    if services.settings.is_prod:
        raise HTTPException(status_code=404)
    fiches = await services.fiches.list()
    statuses = await services.incidents.statuses_for(fiches)
    names = service_names(fiches)
    now = services.clock.now()
    glossary = await glossary_map(services)
    first_gotcha = next((g for f in fiches for g in f.gotchas), None)
    page = StyleguidePage(
        meta=PageMeta(title="Guide de style", path="/styleguide", noindex=True),
        statuses=[
            StatusView(
                status=s,
                label=STATUS_LABELS[s],
                since=now if s in (Status.DEGRADED, Status.DOWN) else None,
            )
            for s in Status
        ],
        cards=[
            fiche_card(f, statuses[f.slug], names, needs_review=services.fiches.needs_review(f))
            for f in fiches[:3]
        ],
        gotcha=gotcha_view(first_gotcha, glossary, needs_review=False) if first_gotcha else None,
        flashes=[
            Flash("success", "Merci ! Votre confirmation est enregistrée."),
            Flash("error", "Formulaire expiré : rechargez la page."),
            Flash("info", "Cette fiche n'a pas été confirmée depuis 90 jours."),
        ],
        form=FormState(
            values={"title": "Un"},
            errors={"title": "Le titre doit faire entre 5 et 160 caractères."},
        ),
        options=[Option("a", "Première option"), Option("b", "Option choisie", selected=True)],
    )
    return render(request, "pages/styleguide.html", page)
