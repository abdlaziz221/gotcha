"""Connexion d'un outil MCP : écran de consentement, puis retour de GitHub.

Voir app/services/oauth.py. L'écran de consentement est obligatoire pour chaque outil
enregistré (sécurité MCP, « confused deputy ») : il montre l'outil et son adresse de
retour, et un cookie lie la suite de la connexion au navigateur qui a accepté.
"""

from __future__ import annotations

import hmac

from fastapi import APIRouter, Depends, HTTPException, Request
from starlette.responses import RedirectResponse, Response

from app.domain.errors import InvalidInputError
from app.security.csrf import verify_csrf
from app.security.ratelimit import rate_limit
from app.web.deps import ServicesDep
from app.web.templating import render
from app.web.viewmodels import PageMeta, ToolConsentPage

router = APIRouter()

CONSENT_PATH = "/connexion/outil"
# __Host- en production : un sous-domaine voisin ne peut ni poser ni écraser ce cookie.
LOGIN_COOKIE = "gotcha_connexion_outil"
SECURE_LOGIN_COOKIE = "__Host-gotcha_connexion_outil"
LOGIN_COOKIE_SECONDS = 10 * 60  # durée de vie d'une demande de connexion (LOGIN_TTL)


def _cookie_name(request: Request) -> str:
    return SECURE_LOGIN_COOKIE if request.app.state.settings.is_prod else LOGIN_COOKIE


def _require_mcp_auth(services: ServicesDep) -> None:
    if not services.settings.mcp_auth:
        raise HTTPException(status_code=404)


@router.get(
    CONSENT_PATH,
    dependencies=[Depends(rate_limit("connexion", limit=60, window_seconds=3600))],
)
async def tool_consent(request: Request, services: ServicesDep, demande: str = "") -> Response:
    _require_mcp_auth(services)
    login = await services.oauth.describe_login(demande)
    if login is None:
        raise InvalidInputError(
            "Demande de connexion inconnue ou expirée : relancez-la depuis votre outil."
        )
    page = ToolConsentPage(
        meta=PageMeta(title="Autoriser un outil", path=CONSENT_PATH, noindex=True),
        client_name=login.client_name,
        redirect_uri=login.redirect_uri,
        request_id=demande,
    )
    return render(request, "pages/tool_consent.html", page)


@router.post(
    CONSENT_PATH,
    dependencies=[
        Depends(verify_csrf),
        Depends(rate_limit("connexion", limit=60, window_seconds=3600)),
    ],
)
async def tool_consent_answer(request: Request, services: ServicesDep) -> Response:
    _require_mcp_auth(services)
    form = await request.form()
    demande = form.get("demande")
    state = demande if isinstance(demande, str) else ""
    if form.get("decision") != "autoriser":
        return RedirectResponse(await services.oauth.refuse_login(state), status_code=303)
    response = RedirectResponse(await services.oauth.approve_login(state), status_code=303)
    response.set_cookie(
        _cookie_name(request),
        state,
        max_age=LOGIN_COOKIE_SECONDS,
        path="/",
        secure=services.settings.is_prod,
        httponly=True,
        samesite="lax",  # le retour de GitHub est une navigation : le cookie est envoyé
    )
    return response


@router.get(
    "/github/callback",
    dependencies=[Depends(rate_limit("connexion", limit=60, window_seconds=3600))],
)
async def github_callback(
    request: Request,
    services: ServicesDep,
    state: str = "",
    code: str | None = None,
    error: str | None = None,
) -> Response:
    _require_mcp_auth(services)
    accepted = request.cookies.get(_cookie_name(request), "")
    # Comparaison en octets : compare_digest refuse les chaînes non ASCII.
    if not accepted or not hmac.compare_digest(accepted.encode(), state.encode()):
        raise InvalidInputError(
            "Cette connexion n'a pas été acceptée dans ce navigateur :"
            " relancez-la depuis votre outil."
        )
    response = RedirectResponse(
        await services.oauth.finish_login(state, code, error), status_code=302
    )
    response.delete_cookie(_cookie_name(request), path="/")
    return response
