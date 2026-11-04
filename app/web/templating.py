"""Moteur de gabarits Jinja2 et fonction de rendu commune à toutes les routes."""

from __future__ import annotations

from pathlib import Path

from fastapi import Request
from fastapi.templating import Jinja2Templates
from starlette.responses import Response

from app.domain.countries import country_name
from app.web.labels import date_fr, datetime_fr

WEB_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = WEB_DIR / "templates"
STATIC_DIR = WEB_DIR / "static"

SITE = {
    "name": "Gotcha",
    "tagline": "Ce que les devs ont déjà résolu sur le paiement et le déploiement en Afrique",
    "hosting": "Hébergé à Dakar sur Datacloud",
    "license": "Contributions publiées sous licence CC BY 4.0",
}

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
templates.env.trim_blocks = True
templates.env.lstrip_blocks = True
templates.env.globals["site"] = SITE
templates.env.filters["date_fr"] = date_fr
templates.env.filters["datetime_fr"] = datetime_fr
templates.env.filters["country_name"] = country_name


def render(request: Request, template: str, page: object, *, status_code: int = 200) -> Response:
    """Rend un gabarit de pages/ avec son contexte `page` (voir app/web/viewmodels.py)."""
    context = {"page": page, "csrf_token": getattr(request.state, "csrf_token", "")}
    return templates.TemplateResponse(request, template, context, status_code=status_code)
