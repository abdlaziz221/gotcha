"""Dépendances FastAPI partagées par les routes."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Request

from app.container import Services
from app.domain.countries import COUNTRY_NAMES
from app.domain.models import Fiche, GlossaryTerm
from app.web.labels import FLASH_MESSAGES
from app.web.viewmodels import Flash, Option


def get_services(request: Request) -> Services:
    return request.app.state.services


ServicesDep = Annotated[Services, Depends(get_services)]


def flash_from(request: Request) -> Flash | None:
    """Message de succès après redirection (?ok=<clé>) ; seules les clés connues passent."""
    message = FLASH_MESSAGES.get(request.query_params.get("ok", ""))
    return Flash(kind="success", message=message) if message else None


async def glossary_map(services: Services) -> dict[str, GlossaryTerm]:
    return {t.slug: t for t in await services.fiches.glossary()}


def fiche_options(fiches: list[Fiche], selected: str = "") -> list[Option]:
    return [Option(f.slug, f.title, f.slug == selected) for f in fiches]


def country_options(selected: str = "") -> list[Option]:
    ordered = sorted(COUNTRY_NAMES.items(), key=lambda item: item[1])
    return [Option(code, name, code == selected) for code, name in ordered]
