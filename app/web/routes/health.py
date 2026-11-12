"""Santé du service : /healthz (et /healthz?db=1 pour tester la base PostgreSQL)."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable

from fastapi import APIRouter, Request
from starlette.responses import JSONResponse

from app.security.ratelimit import RateLimiter, client_ip
from app.web.deps import ServicesDep

router = APIRouter()

# Test de la base : par adresse et par minute. /healthz sans paramètre reste libre, car
# l'hébergeur l'appelle souvent pour savoir si le service vit.
DB_CHECK_LIMIT = 30
DB_CHECK_WINDOW_SECONDS = 60
DB_CHECK_TIMEOUT_SECONDS = 3


@router.get("/healthz")
async def healthz(request: Request, services: ServicesDep, db: bool = False) -> JSONResponse:
    body: dict[str, str] = {"status": "ok"}
    if not db:
        return JSONResponse(body)
    settings = services.settings
    peer = request.client.host if request.client else None
    ip = client_ip(request.headers, peer, proxy_hops=settings.proxy_hops)
    limiter: RateLimiter = request.app.state.rate_limiter
    if not limiter.hit(f"sante:{ip}", limit=DB_CHECK_LIMIT, window_seconds=DB_CHECK_WINDOW_SECONDS):
        return JSONResponse({"status": "ok", "database": "trop de demandes"}, status_code=429)
    # Le pool du stockage, et non une connexion neuve à chaque appel : des appels en rafale
    # ouvraient autant de connexions et saturaient la base.
    ping: Callable[[], Awaitable[bool]] | None = getattr(services.store, "ping", None)
    if settings.store != "postgres" or ping is None:
        body["database"] = "non configurée"
        return JSONResponse(body)
    try:
        await asyncio.wait_for(ping(), timeout=DB_CHECK_TIMEOUT_SECONDS)
        body["database"] = "ok"
    except Exception as exc:  # on ne renvoie que le type d'erreur, jamais l'URL de connexion
        body.update(status="degraded", database=f"erreur : {type(exc).__name__}")
        return JSONResponse(body, status_code=503)
    return JSONResponse(body)
