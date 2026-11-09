"""Journal des pannes et formulaire de signalement."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, Request
from pydantic import ValidationError
from starlette.responses import RedirectResponse, Response

from app.domain.errors import InvalidInputError, NotFoundError
from app.domain.models import Account, OutageReport
from app.security.csrf import verify_csrf
from app.security.ratelimit import rate_limit
from app.web.deps import ServicesDep, country_options, fiche_options, flash_from
from app.web.forms import FIELD_ERRORS, field_errors, form_values
from app.web.presenters import fiche_card, fiche_url, incident_view, service_names
from app.web.session import writer_account
from app.web.templating import render
from app.web.viewmodels import FormState, IncidentsPage, PageMeta, ReportOutagePage

router = APIRouter()

REPORT_META = PageMeta(title="Signaler une panne", path="/pannes/signaler", noindex=True)


@router.get("/pannes")
async def incidents(
    request: Request, services: ServicesDep, background: BackgroundTasks
) -> Response:
    background.add_task(services.incidents.refresh_if_stale)
    fiches = await services.fiches.list()
    names = service_names(fiches)
    statuses = await services.incidents.statuses_for(fiches)
    now = services.clock.now()
    views = [incident_view(i, names, now) for i in await services.incidents.recent(limit=80)]
    page = IncidentsPage(
        meta=PageMeta(title="Journal des pannes", path="/pannes"),
        active=[v for v in views if v.is_active],
        recent=[v for v in views if not v.is_active][:40],
        flash=flash_from(request),
        services=[
            fiche_card(f, statuses[f.slug], names, needs_review=services.fiches.needs_review(f))
            for f in fiches
        ],
    )
    return render(request, "pages/incidents.html", page)


@router.get("/pannes/signaler", dependencies=[Depends(writer_account)])
async def report_form(request: Request, services: ServicesDep, fiche: str = "") -> Response:
    page = ReportOutagePage(
        meta=REPORT_META,
        form=FormState(values={"fiche_slug": fiche}),
        fiche_options=fiche_options(await services.fiches.list(), fiche),
        country_options=country_options(),
    )
    return render(request, "pages/report_outage.html", page)


@router.post(
    "/pannes/signaler",
    dependencies=[
        Depends(verify_csrf),
        Depends(rate_limit("signaler", limit=5, window_seconds=3600)),
    ],
)
async def report_submit(
    request: Request,
    services: ServicesDep,
    account: Annotated[Account | None, Depends(writer_account)],
) -> Response:
    values = form_values(await request.form(), ("fiche_slug", "country", "description", "pseudo"))
    errors: dict[str, str] = {}
    try:
        fiche = await services.fiches.get(values["fiche_slug"])
    except NotFoundError:
        fiche = None
        errors["fiche_slug"] = FIELD_ERRORS["fiche_slug"]

    if fiche is not None:
        try:
            await services.incidents.report(
                OutageReport(
                    service_slug=fiche.service.slug,
                    country=fiche.country or values["country"] or None,
                    description=values["description"],
                    reported_by=(
                        account.pseudo[:40]
                        if account is not None
                        else values["pseudo"][:40] or None
                    ),
                )
            )
            return RedirectResponse(f"{fiche_url(fiche.slug)}?ok=signalement", status_code=303)
        except ValidationError as exc:
            errors.update(field_errors(exc))
        except InvalidInputError as exc:
            errors["form"] = str(exc)

    page = ReportOutagePage(
        meta=REPORT_META,
        form=FormState(values=values, errors=errors),
        fiche_options=fiche_options(await services.fiches.list(), values["fiche_slug"]),
        country_options=country_options(values["country"]),
    )
    return render(request, "pages/report_outage.html", page, status_code=422)
