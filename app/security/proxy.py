"""Protocole d'origine derrière le proxy de confiance (en-tête X-Forwarded-Proto).

uvicorn tourne avec --no-proxy-headers : l'adresse du visiteur est lue par l'application
(client_ip, GOTCHA_PROXY_HOPS), jamais en croyant n'importe quel X-Forwarded-For. Sans ce
middleware, le site se croirait en HTTP derrière le proxy HTTPS, et les redirections
automatiques (barre oblique finale, /mcp vers /mcp/) enverraient vers une adresse http://.
"""

from __future__ import annotations

from starlette.datastructures import Headers
from starlette.types import ASGIApp, Receive, Scope, Send

from app.security.ratelimit import forwarded_values


class ForwardedProtoMiddleware:
    def __init__(self, app: ASGIApp, *, proxy_hops: int) -> None:
        self.app = app
        self.proxy_hops = proxy_hops

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "http" and self.proxy_hops > 0:
            # Même règle que pour l'adresse : la valeur posée par le dernier proxy de confiance.
            values = forwarded_values(Headers(scope=scope), "x-forwarded-proto")
            if len(values) >= self.proxy_hops:
                proto = values[-self.proxy_hops].lower()
                if proto in ("http", "https"):
                    scope = {**scope, "scheme": proto}
        await self.app(scope, receive, send)
