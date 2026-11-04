"""Point d'entrée : uvicorn app.main:app

Assemble le site web, le serveur MCP (/mcp), les middlewares de sécurité et le
stockage choisi par la configuration.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.middleware.gzip import GZipMiddleware

from app.config import Settings
from app.container import Services, build_services
from app.mcp.server import build_mcp_server, mount_mcp
from app.security.csrf import CSRFCookieMiddleware
from app.security.headers import SecurityHeadersMiddleware
from app.security.ratelimit import PathQuotaMiddleware, RateLimiter
from app.web.errors import install_error_handlers
from app.web.routes import (
    auth,
    contributions,
    dev,
    fiches,
    health,
    incidents,
    pages,
    probe,
    review,
)
from app.web.templating import STATIC_DIR

ServicesFactory = Callable[[Settings], Awaitable[Services]]

# Routes OAuth du SDK : au plus tant d'appels par heure et par adresse IP.
OAUTH_QUOTAS = {"/register": (20, 3600), "/authorize": (60, 3600), "/token": (120, 3600)}


def create_app(
    settings: Settings | None = None, *, services_factory: ServicesFactory | None = None
) -> FastAPI:
    settings = settings or Settings.from_env()
    factory = services_factory or build_services

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        services = await factory(settings)
        app.state.services = services
        if not settings.ingest_live:
            # Extrait enregistré : lecture instantanée, l'état des services est prêt d'emblée.
            await services.incidents.refresh_if_stale()
        try:
            async with mcp.session_manager.run():
                yield
        finally:
            await services.close()

    app = FastAPI(
        title="Gotcha",
        lifespan=lifespan,
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )
    app.state.settings = settings
    app.state.rate_limiter = RateLimiter()

    app.add_middleware(CSRFCookieMiddleware, secure=settings.is_prod)
    app.add_middleware(GZipMiddleware, minimum_size=500)
    app.add_middleware(SecurityHeadersMiddleware, hsts=settings.is_prod)

    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
    for module in (pages, fiches, contributions, incidents, review, dev, health, auth):
        app.include_router(module.router)
    if settings.probe:
        app.include_router(probe.router)
    install_error_handlers(app)

    mcp = build_mcp_server(app)
    mount_mcp(app, mcp)
    if settings.mcp_auth:
        app.add_middleware(PathQuotaMiddleware, quotas=OAUTH_QUOTAS)
    return app


app = create_app()
