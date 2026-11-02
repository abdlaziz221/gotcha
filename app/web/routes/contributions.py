"""Formulaire « Contribuer » : un piège, une étape ou une correction, relu avant publication."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from pydantic import ValidationError
from starlette.responses import RedirectResponse, Response

from app.domain.errors import InvalidInputError, NotFoundError, SecretDetectedError
from app.domain.models import ContributionInput, ContributionKind
from app.security.csrf import verify_csrf
from app.security.ratelimit import rate_limit
from app.web.deps import ServicesDep, fiche_options
from app.web.forms import FIELD_ERRORS, field_errors, form_values
from app.web.labels import CONTRIBUTION_KIND_LABELS
from app.web.templating import render
from app.web.viewmodels import ContributePage, FormState, MessagePage, Option, PageMeta

router = APIRouter()

FIELDS = (
    "kind",
    "fiche_slug",
    "title",
    "body_md",
    "source_url",
    "api_version",
    "pseudo",
    "email",
    "licence",
)
META = PageMeta(title="Contribuer", path="/contribuer", noindex=True)


def _kind_options(selected: str) -> list[Option]:
    return [
        Option(k.value, label, k.value == selected) for k, label in CONTRIBUTION_KIND_LABELS.items()
    ]


@router.get("/contribuer")
async def contribute_form(request: Request, services: ServicesDep, fiche: str = "") -> Response:
    fiches = await services.fiches.list()
    page = ContributePage(
        meta=META,
        form=FormState(values={"fiche_slug": fiche, "kind": ContributionKind.GOTCHA.value}),
        fiche_options=fiche_options(fiches, fiche),
        kind_options=_kind_options(ContributionKind.GOTCHA.value),
    )
    return render(request, "pages/contribute.html", page)


@router.post(
    "/contribuer",
    dependencies=[
        Depends(verify_csrf),
        Depends(rate_limit("contribuer", limit=5, window_seconds=3600)),
    ],
)
async def contribute_submit(request: Request, services: ServicesDep) -> Response:
    values = form_values(await request.form(), FIELDS)
    errors: dict[str, str] = {}
    if values["licence"] != "oui":
        errors["licence"] = FIELD_ERRORS["licence"]
    data = None
    try:
        data = ContributionInput(
            kind=values["kind"],
            fiche_slug=values["fiche_slug"],
            title=values["title"],
            body_md=values["body_md"],
            source_url=values["source_url"] or None,
            api_version=values["api_version"] or None,
            pseudo=values["pseudo"],
            email=values["email"],
        )
    except ValidationError as exc:
        errors.update(field_errors(exc))

    if data is not None and not errors:
        try:
            await services.contributions.submit(data)
            return RedirectResponse("/contribuer/merci", status_code=303)
        except SecretDetectedError as exc:
            errors["body_md"] = (
                f"Votre texte semble contenir un secret ({', '.join(exc.kinds)}). "
                "Retirez-le, puis renvoyez."
            )
        except NotFoundError:
            errors["fiche_slug"] = FIELD_ERRORS["fiche_slug"]
        except InvalidInputError as exc:
            errors["form"] = str(exc)

    fiches = await services.fiches.list()
    page = ContributePage(
        meta=META,
        form=FormState(values=values, errors=errors),
        fiche_options=fiche_options(fiches, values["fiche_slug"]),
        kind_options=_kind_options(values["kind"]),
    )
    return render(request, "pages/contribute.html", page, status_code=422)


@router.get("/contribuer/merci")
async def contribute_thanks(request: Request) -> Response:
    page = MessagePage(
        meta=PageMeta(
            title="Merci pour votre contribution", path="/contribuer/merci", noindex=True
        ),
        heading="Merci, votre contribution est bien reçue",
        message=(
            "Un relecteur la vérifie avant publication. Elle sera publiée avec votre pseudo, "
            "sous licence CC BY 4.0. Votre e-mail reste privé."
        ),
        back_url="/",
        back_label="Retour à l'accueil",
    )
    return render(request, "pages/message.html", page)
