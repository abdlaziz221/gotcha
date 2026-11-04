"""Connexion : retour de GitHub, connexion sur le site, code du jury, déconnexion."""

from __future__ import annotations

from urllib.parse import urlencode

from fastapi import APIRouter, Depends, HTTPException, Request
from starlette.responses import RedirectResponse, Response

from app.security.csrf import verify_csrf
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
from app.web.viewmodels import FormState, LoginPage, PageMeta

router = APIRouter()

SESSION_MAX_AGE = int(SESSION_TTL.total_seconds())
LOGIN_ERRORS = {
    "refus": "La connexion n'a pas abouti. Vous pouvez réessayer.",
    "bloque": "Ce compte est bloqué.",
}


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
async def login_with_github(services: ServicesDep, retour: str = "/") -> RedirectResponse:
    if not services.settings.site_auth:
        raise HTTPException(status_code=404)
    return RedirectResponse(await services.oauth.begin_web_login(retour), status_code=302)


@router.post(
    "/connexion/jury",
    dependencies=[
        Depends(verify_csrf),
        Depends(rate_limit("connexion-jury", limit=10, window_seconds=3600)),
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
    services: ServicesDep, state: str = "", code: str | None = None, error: str | None = None
) -> RedirectResponse:
    settings = services.settings
    if not (settings.mcp_auth or settings.site_auth):
        raise HTTPException(status_code=404)
    result = await services.oauth.finish_login(state, code, error)
    response = RedirectResponse(result.redirect_url, status_code=302)
    if result.session_token:
        set_session_cookie(response, settings, result.session_token, SESSION_MAX_AGE)
    return response
