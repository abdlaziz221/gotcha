"""Connexion : site, outil MCP (écran de consentement), retour de GitHub, jury, déconnexion.

Voir app/services/oauth.py. Toute connexion par GitHub, sur le site comme pour un outil
MCP, pose un cookie lié à sa demande : le retour de GitHub n'est accepté que dans le
navigateur qui l'a lancée. Sans lui, un lien de retour envoyé à quelqu'un d'autre
connecterait la victime au compte de l'attaquant (site) ou donnerait un code à
l'attaquant (outil MCP, « confused deputy »).
"""

from __future__ import annotations

import hmac
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, HTTPException, Request
from starlette.responses import RedirectResponse, Response

from app.domain.errors import InvalidInputError
from app.security.csrf import verify_csrf
from app.security.github import AUTHORIZE_URL as GITHUB_AUTHORIZE_URL
from app.security.headers import csp_allowing_forms_to
from app.security.ratelimit import rate_limit
from app.services.oauth import SESSION_TTL, safe_next_url
from app.web.deps import ServicesDep
from app.web.forms import form_values
from app.web.session import (
    clear_session_cookie,
    current_account,
    session_token,
    set_session_cookie,
)
from app.web.templating import render
from app.web.viewmodels import FormState, LoginPage, PageMeta, ToolConsentPage

router = APIRouter()

SESSION_MAX_AGE = int(SESSION_TTL.total_seconds())
LOGIN_ERRORS = {
    "refus": "La connexion n'a pas abouti. Vous pouvez réessayer.",
    "bloque": "Ce compte est bloqué.",
}
CONSENT_PATH = "/connexion/outil"
# __Host- en production : un sous-domaine voisin ne peut ni poser ni écraser ce cookie.
LOGIN_COOKIE = "gotcha_connexion"
SECURE_LOGIN_COOKIE = "__Host-gotcha_connexion"
LOGIN_COOKIE_SECONDS = 10 * 60  # durée de vie d'une demande de connexion (LOGIN_TTL)
EXPIRED = "Demande de connexion inconnue ou expirée : relancez la connexion."


def _cookie_name(request: Request) -> str:
    return SECURE_LOGIN_COOKIE if request.app.state.settings.is_prod else LOGIN_COOKIE


def _bind_to_browser(request: Request, response: Response, state: str) -> None:
    response.set_cookie(
        _cookie_name(request),
        state,
        max_age=LOGIN_COOKIE_SECONDS,
        path="/",
        secure=request.app.state.settings.is_prod,
        httponly=True,
        samesite="lax",  # le retour de GitHub est une navigation : le cookie est envoyé
    )


def _login_page(services: ServicesDep, retour: str, *, error: str | None = None) -> LoginPage:
    return LoginPage(
        meta=PageMeta(title="Se connecter", path="/connexion", noindex=True),
        github_url=f"/connexion/github?{urlencode({'retour': retour})}",
        retour=retour,
        jury_enabled=bool(services.settings.jury_code),
        form=FormState(errors={"form": error} if error else {}),
    )


@router.get("/connexion")
async def login(
    request: Request, services: ServicesDep, retour: str = "/", erreur: str = ""
) -> Response:
    if not services.settings.site_auth:
        raise HTTPException(status_code=404)
    next_url = safe_next_url(retour)
    if current_account(request) is not None:
        return RedirectResponse(next_url, status_code=303)
    page = _login_page(services, next_url, error=LOGIN_ERRORS.get(erreur))
    return render(request, "pages/login.html", page)


@router.get(
    "/connexion/github",
    dependencies=[Depends(rate_limit("connexion-site", limit=60, window_seconds=3600))],
)
async def login_with_github(
    request: Request, services: ServicesDep, retour: str = "/"
) -> RedirectResponse:
    if not services.settings.site_auth:
        raise HTTPException(status_code=404)
    state, github_url = await services.oauth.begin_web_login(retour)
    response = RedirectResponse(github_url, status_code=302)
    _bind_to_browser(request, response, state)
    return response


@router.get(
    CONSENT_PATH,
    dependencies=[Depends(rate_limit("connexion", limit=60, window_seconds=3600))],
)
async def tool_consent(request: Request, services: ServicesDep, demande: str = "") -> Response:
    if not services.settings.mcp_auth:
        raise HTTPException(status_code=404)
    login = await services.oauth.describe_login(demande)
    if login is None:
        raise InvalidInputError(EXPIRED)
    page = ToolConsentPage(
        meta=PageMeta(title="Autoriser un outil", path=CONSENT_PATH, noindex=True),
        client_name=login.client_name,
        redirect_uri=login.redirect_uri,
        request_id=demande,
    )
    response = render(request, "pages/tool_consent.html", page)
    # « Autoriser » mène à GitHub puis à l'outil, « Refuser » directement à l'outil.
    response.headers["Content-Security-Policy"] = csp_allowing_forms_to(
        GITHUB_AUTHORIZE_URL, login.redirect_uri
    )
    return response


@router.post(
    CONSENT_PATH,
    dependencies=[
        # Le quota d'abord : verify_csrf lit tout le formulaire, et un envoi refusé
        # pour son jeton ne consommait alors aucun essai.
        Depends(rate_limit("connexion", limit=60, window_seconds=3600)),
        Depends(verify_csrf),
    ],
)
async def tool_consent_answer(request: Request, services: ServicesDep) -> Response:
    if not services.settings.mcp_auth:
        raise HTTPException(status_code=404)
    form = await request.form()
    demande = form.get("demande")
    state = demande if isinstance(demande, str) else ""
    if form.get("decision") != "autoriser":
        return RedirectResponse(await services.oauth.refuse_login(state), status_code=303)
    response = RedirectResponse(await services.oauth.approve_login(state), status_code=303)
    _bind_to_browser(request, response, state)
    return response


@router.post(
    "/connexion/jury",
    dependencies=[
        # Le quota d'abord : verify_csrf lit tout le formulaire, et un envoi refusé
        # pour son jeton ne consommait alors aucun essai.
        Depends(rate_limit("connexion-jury", limit=10, window_seconds=3600)),
        Depends(verify_csrf),
    ],
)
async def login_with_code(request: Request, services: ServicesDep) -> Response:
    settings = services.settings
    if not (settings.site_auth and settings.jury_code):
        raise HTTPException(status_code=404)
    values = form_values(await request.form(), ("code", "retour"))
    next_url = safe_next_url(values["retour"])
    token = await services.oauth.login_with_code(values["code"])
    if token is None:
        page = _login_page(services, next_url, error="Code incorrect.")
        return render(request, "pages/login.html", page, status_code=422)
    response = RedirectResponse(next_url, status_code=303)
    set_session_cookie(response, settings, token, SESSION_MAX_AGE)
    return response


@router.post("/deconnexion", dependencies=[Depends(verify_csrf)])
async def logout(request: Request, services: ServicesDep) -> RedirectResponse:
    token = session_token(request)
    if token:
        await services.oauth.end_session(token)
    response = RedirectResponse("/", status_code=303)
    clear_session_cookie(response, services.settings)
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
) -> RedirectResponse:
    settings = services.settings
    if not (settings.mcp_auth or settings.site_auth):
        raise HTTPException(status_code=404)
    accepted = request.cookies.get(_cookie_name(request), "")
    # Comparaison en octets : compare_digest refuse les chaînes non ASCII.
    if not accepted or not hmac.compare_digest(accepted.encode(), state.encode()):
        raise InvalidInputError(
            "Cette connexion n'a pas été lancée dans ce navigateur : relancez la connexion."
        )
    result = await services.oauth.finish_login(state, code, error)
    response = RedirectResponse(result.redirect_url, status_code=302)
    if result.session_token:
        set_session_cookie(response, settings, result.session_token, SESSION_MAX_AGE)
    # La demande est consommée. Mêmes attributs qu'à la pose : sans Secure, le navigateur
    # refuse d'effacer un cookie __Host-.
    response.delete_cookie(
        _cookie_name(request),
        path="/",
        secure=settings.is_prod,
        httponly=True,
        samesite="lax",
    )
    return response
