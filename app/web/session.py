"""Session du visiteur connecté : cookie opaque, dont le stockage ne garde que l'empreinte."""

from __future__ import annotations

from urllib.parse import urlsplit

from fastapi import HTTPException, Request
from starlette.responses import Response
from starlette.types import ASGIApp, Receive, Scope, Send

from app.config import Settings
from app.domain.models import Account

COOKIE_NAME = "gotcha_session"
# En production (HTTPS), le préfixe __Host- interdit à un site voisin de poser ce cookie.
SECURE_COOKIE_NAME = "__Host-gotcha_session"


class LoginRequiredError(Exception):
    """Le visiteur doit se connecter ; il revient ensuite sur `next_url`."""

    def __init__(self, next_url: str) -> None:
        self.next_url = next_url
        super().__init__(next_url)


def _cookie_name(settings: Settings) -> str:
    return SECURE_COOKIE_NAME if settings.is_prod else COOKIE_NAME


def set_session_cookie(response: Response, settings: Settings, token: str, max_age: int) -> None:
    response.set_cookie(
        _cookie_name(settings),
        token,
        max_age=max_age,
        path="/",
        secure=settings.is_prod,
        httponly=True,
        samesite="lax",
    )


def clear_session_cookie(response: Response, settings: Settings) -> None:
    response.delete_cookie(
        _cookie_name(settings), path="/", secure=settings.is_prod, httponly=True, samesite="lax"
    )


def session_token(request: Request) -> str | None:
    return request.cookies.get(_cookie_name(request.app.state.settings))


class AccountMiddleware:
    """Retrouve le compte du visiteur et le place dans request.state.account."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "http" and not scope["path"].startswith("/static"):
            request = Request(scope)
            token = session_token(request)
            if token:
                services = request.app.state.services
                account = await services.oauth.session_account(token)
                scope.setdefault("state", {})["account"] = account
        await self.app(scope, receive, send)


def current_account(request: Request) -> Account | None:
    return getattr(request.state, "account", None)


def can_write(settings: Settings, account: Account | None) -> bool:
    """Sans connexion, seul le développement local accepte encore les formulaires anonymes."""
    if settings.site_auth:
        return account is not None
    return not settings.is_prod


def _return_address(request: Request) -> str:
    """Où revenir après la connexion.

    Pour un formulaire envoyé (POST), revenir à son adresse ferait un GET sur une route
    POST : erreur 405. On revient à la page d'où il est parti (Referer du même site),
    sinon à la page parente (/fiches/x/confirmer devient /fiches/x).
    """
    if request.method == "GET":
        query = f"?{request.url.query}" if request.url.query else ""
        return f"{request.url.path}{query}"
    referer = urlsplit(request.headers.get("referer", ""))
    if referer.netloc == request.url.netloc and referer.path:
        return referer.path + (f"?{referer.query}" if referer.query else "")
    return request.url.path.rsplit("/", 1)[0] or "/"


def writer_account(request: Request) -> Account | None:
    """Dépendance des formulaires : aucune écriture anonyme en production.

    Renvoie le compte du visiteur, ou None pour un formulaire anonyme en développement.
    """
    settings: Settings = request.app.state.settings
    account = current_account(request)
    if can_write(settings, account):
        return account
    if settings.site_auth:
        raise LoginRequiredError(_return_address(request))
    raise HTTPException(status_code=403, detail="Les contributions sont fermées pour l'instant.")
