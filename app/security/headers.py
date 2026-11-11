"""En-têtes de sécurité ajoutés à chaque réponse (middleware ASGI)."""

from __future__ import annotations

from urllib.parse import urlsplit

from starlette.datastructures import MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

# CSP stricte : aucun script ni style en ligne, tout vient du site lui-même.
CONTENT_SECURITY_POLICY = "; ".join(
    [
        "default-src 'self'",
        "img-src 'self' data:",
        "style-src 'self'",
        "script-src 'self'",
        "font-src 'self'",
        "connect-src 'self'",
        "object-src 'none'",
        "base-uri 'none'",
        "frame-ancestors 'none'",
        "form-action 'self'",
    ]
)


# Caractères qui changeraient le sens de la politique s'ils passaient dans une source.
_UNSAFE_IN_SOURCE = frozenset(" ;,'\"\t\r\n")


def form_target(url: str) -> str | None:
    """La source CSP qui autorise un formulaire à mener vers `url`, ou None.

    http et https : l'origine (schéma, machine, port). Autre schéma (cursor://) : le
    schéma seul. None si l'adresse contient de quoi modifier la politique.
    """
    parts = urlsplit(url)
    scheme = parts.scheme.lower()
    if scheme in ("http", "https"):
        ok = bool(parts.hostname) and "@" not in parts.netloc
        source = f"{scheme}://{parts.netloc.lower()}" if ok else ""
    else:
        ok = (
            scheme.isascii()
            and scheme[:1].isalpha()
            and all(c.isalnum() or c in "+.-" for c in scheme)
        )
        source = f"{scheme}:" if ok else ""
    if not source or any(c in _UNSAFE_IN_SOURCE for c in source):
        return None
    return source


def csp_allowing_forms_to(*urls: str) -> str:
    """La CSP du site, où les formulaires peuvent aussi mener vers ces adresses.

    `form-action` s'applique à chaque redirection qui suit l'envoi d'un formulaire :
    l'écran de consentement mène à GitHub puis à l'adresse de retour de l'outil, que
    `'self'` seul bloquerait dans le navigateur.
    """
    sources = [s for s in (form_target(u) for u in urls) if s]
    if not sources:
        return CONTENT_SECURITY_POLICY
    return CONTENT_SECURITY_POLICY.replace(
        "form-action 'self'", "form-action 'self' " + " ".join(dict.fromkeys(sources))
    )


class SecurityHeadersMiddleware:
    def __init__(self, app: ASGIApp, *, hsts: bool) -> None:
        self.app = app
        self.hsts = hsts

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def send_with_headers(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = MutableHeaders(scope=message)
                headers.setdefault("Content-Security-Policy", CONTENT_SECURITY_POLICY)
                headers.setdefault("X-Content-Type-Options", "nosniff")
                headers.setdefault("X-Frame-Options", "DENY")
                headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
                headers.setdefault("Cross-Origin-Opener-Policy", "same-origin")
                headers.setdefault(
                    "Permissions-Policy", "camera=(), microphone=(), geolocation=(), payment=()"
                )
                if self.hsts:
                    headers.setdefault(
                        "Strict-Transport-Security", "max-age=31536000; includeSubDomains"
                    )
            await send(message)

        await self.app(scope, receive, send_with_headers)
