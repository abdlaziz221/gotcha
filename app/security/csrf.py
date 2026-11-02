"""Protection CSRF par double soumission : un jeton en cookie, recopié dans chaque formulaire.

- Le middleware pose le cookie et met le jeton dans request.state.csrf_token.
- Chaque route POST déclare la dépendance verify_csrf.
- Chaque formulaire contient : <input type="hidden" name="csrf_token" value="{{ csrf_token }}">
"""

from __future__ import annotations

import secrets
from http.cookies import SimpleCookie

from fastapi import HTTPException, Request
from starlette.datastructures import MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

COOKIE_NAME = "gotcha_csrf"
FIELD_NAME = "csrf_token"


def _cookie_value(scope: Scope) -> str | None:
    for name, value in scope.get("headers", []):
        if name == b"cookie":
            cookie = SimpleCookie()
            cookie.load(value.decode("latin-1"))
            if COOKIE_NAME in cookie:
                return cookie[COOKIE_NAME].value
    return None


class CSRFCookieMiddleware:
    def __init__(self, app: ASGIApp, *, secure: bool) -> None:
        self.app = app
        self.secure = secure

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        token = _cookie_value(scope)
        is_new = token is None or len(token) < 32
        if is_new:
            token = secrets.token_urlsafe(32)
        scope.setdefault("state", {})["csrf_token"] = token

        async def send_with_cookie(message: Message) -> None:
            if is_new and message["type"] == "http.response.start":
                attrs = f"{COOKIE_NAME}={token}; Path=/; HttpOnly; SameSite=Lax"
                if self.secure:
                    attrs += "; Secure"
                MutableHeaders(scope=message).append("Set-Cookie", attrs)
            await send(message)

        await self.app(scope, receive, send_with_cookie)


async def verify_csrf(request: Request) -> None:
    """Dépendance FastAPI : refuse un POST dont le jeton ne correspond pas au cookie."""
    form = await request.form()
    sent = form.get(FIELD_NAME)
    expected = request.cookies.get(COOKIE_NAME)
    if not isinstance(sent, str) or not expected or not secrets.compare_digest(sent, expected):
        raise HTTPException(status_code=403, detail="Formulaire expiré : rechargez la page.")
