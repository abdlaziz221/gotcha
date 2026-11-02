"""Page d'une fiche (vue complète ou pas à pas) et bouton « ça marche encore »."""

from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from starlette.responses import RedirectResponse, Response

from app.domain.countries import country_name
from app.domain.models import Publication, TargetKind
from app.security.csrf import verify_csrf
from app.security.ratelimit import rate_limit
from app.web.deps import ServicesDep, flash_from, glossary_map
from app.web.forms import form_values
from app.web.presenters import (
    fiche_url,
    gotcha_view,
    source_view,
    status_view,
    step_views,
)
from app.web.templating import render
from app.web.viewmodels import FichePage, PageMeta, StepMode

router = APIRouter()


@router.get("/fiches/{slug}")
async def fiche_detail(
    request: Request,
    slug: str,
    services: ServicesDep,
    background: BackgroundTasks,
    mode: str | None = None,
    etape: int | None = None,
) -> Response:
    background.add_task(services.incidents.refresh_if_stale)
    fiche = await services.fiches.get(slug)
    status = await services.incidents.status_for(fiche)
    glossary = await glossary_map(services)
    steps = step_views(fiche, glossary)

    step_mode = None
    if mode == "pas-a-pas" and steps:
        index = min(max(etape or 1, 1), len(steps))
        step_mode = StepMode(
            current=steps[index - 1],
            index=index,
            total=len(steps),
            prev_url=steps[index - 2].url if index > 1 else None,
            next_url=steps[index].url if index < len(steps) else None,
            exit_url=fiche_url(slug),
        )

    page = FichePage(
        meta=PageMeta(title=fiche.title, path=fiche_url(slug), description=fiche.summary),
        slug=fiche.slug,
        title=fiche.title,
        service_name=fiche.service.name,
        service_docs_url=str(fiche.service.docs_url) if fiche.service.docs_url else None,
        kind=fiche.service.kind,
        country_name=country_name(fiche.country),
        summary=fiche.summary,
        api_version=fiche.api_version,
        status=status_view(status, {fiche.service.slug: fiche.service.name}),
        prerequisites=fiche.prerequisites,
        steps=steps,
        gotchas=[
            gotcha_view(g, glossary, needs_review=services.fiches.needs_review(g))
            for g in fiche.gotchas
        ],
        differences=fiche.differences,
        error_codes=fiche.error_codes,
        sources=[source_view(s) for s in fiche.sources],
        needs_review=services.fiches.needs_review(fiche),
        is_draft=fiche.publication is not Publication.PUBLISHED,
        last_confirmed_on=fiche.last_confirmed_on,
        confirmations=fiche.confirmations,
        contribute_url=f"/contribuer?fiche={slug}",
        report_url=f"/pannes/signaler?fiche={slug}",
        step_mode=step_mode,
        flash=flash_from(request),
    )
    return render(request, "pages/fiche.html", page)


@router.post(
    "/fiches/{slug}/confirmer",
    dependencies=[
        Depends(verify_csrf),
        Depends(rate_limit("confirmer", limit=30, window_seconds=3600)),
    ],
)
async def confirm(request: Request, slug: str, services: ServicesDep) -> Response:
    form = await request.form()
    values = form_values(form, ("target_kind", "target_id", "still_works", "api_version", "pseudo"))
    try:
        kind = TargetKind(values["target_kind"])
    except ValueError:
        raise HTTPException(status_code=400, detail="Cible de confirmation invalide.") from None
    target_id = values["target_id"] or slug
    if target_id.split(".", 1)[0] != slug:
        raise HTTPException(status_code=400, detail="Cible de confirmation invalide.")

    await services.contributions.confirm(
        kind,
        target_id,
        still_works=values["still_works"] != "0",
        api_version=values["api_version"][:40] or None,
        pseudo=values["pseudo"][:40] or None,
    )
    anchor = "piege-" + target_id.split(".", 1)[1] if kind is TargetKind.GOTCHA else "confirmer"
    return RedirectResponse(f"{fiche_url(slug)}?ok=confirmation#{anchor}", status_code=303)
