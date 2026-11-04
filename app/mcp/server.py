"""Enregistrement des outils auprès du SDK MCP officiel (mcp 2.x, licence MIT).

Responsable : Khalifa. Transport HTTP « streamable », sans état (stateless) et en
réponses JSON : compatible avec le Serverless, aucune connexion longue. Point
d'entrée : POST /mcp.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from functools import wraps
from typing import TYPE_CHECKING, ParamSpec, TypeVar

from mcp.server.auth.middleware.auth_context import get_access_token
from mcp.server.auth.settings import AuthSettings, ClientRegistrationOptions, RevocationOptions
from mcp.server.mcpserver import Context, MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp.server.transport_security import TransportSecuritySettings
from mcp.types import ToolAnnotations

from app.domain.errors import GotchaError
from app.mcp import tools
from app.mcp.oauth import GotchaOAuthProvider
from app.mcp.schemas import FicheOut, OutageReportOut, SearchResultOut, ServiceOut, StatusOut
from app.security.ratelimit import client_ip

if TYPE_CHECKING:
    from fastapi import FastAPI

    from app.container import Services

P = ParamSpec("P")
R = TypeVar("R")

INSTRUCTIONS = (
    "Gotcha is a field notebook of undocumented pitfalls (gotchas) for African payment APIs "
    "(Wave, Orange Money, MTN MoMo, M-Pesa) and for deploying on the Datacloud platform. "
    "Before writing integration or deployment code: call get_fiche for the service and "
    "country, apply every gotcha it lists, then call get_service_status and warn the user "
    "if the service is degraded or down. Gotchas are written and verified by developers; "
    "cite their URL when you rely on one."
)
REPORT_INSTRUCTIONS = " If you hit an outage, report it with report_outage."

READ_ONLY = ToolAnnotations(read_only_hint=True, open_world_hint=False)
REPORT = ToolAnnotations(read_only_hint=False, destructive_hint=False, idempotent_hint=False)

# Signalements de pannes par les agents : au plus 10 par heure et par adresse IP.
REPORT_LIMIT, REPORT_WINDOW_SECONDS = 10, 3600


def _tool_errors(func: Callable[P, Awaitable[R]]) -> Callable[P, Awaitable[R]]:
    """Traduit les erreurs métier en ToolError : l'agent reçoit un message lisible."""

    @wraps(func)
    async def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        try:
            return await func(*args, **kwargs)
        except GotchaError as exc:
            raise ToolError(str(exc)) from exc

    return wrapper


def build_mcp_server(app: FastAPI) -> MCPServer:
    settings = app.state.settings
    can_write = settings.mcp_auth or not settings.is_prod

    def services() -> Services:
        return app.state.services

    resource_url = f"{settings.site_url}/mcp"
    mcp = MCPServer(
        name="gotcha",
        title="Gotcha",
        instructions=INSTRUCTIONS + (REPORT_INSTRUCTIONS if can_write else ""),
        version="0.1.0",
        auth_server_provider=(
            GotchaOAuthProvider(services, resource_url=resource_url) if settings.mcp_auth else None
        ),
        auth=(
            AuthSettings.model_validate(
                {
                    "issuer_url": settings.site_url,
                    "resource_server_url": resource_url,
                    "validate_token_resource": True,
                    "client_registration_options": ClientRegistrationOptions(enabled=True),
                    "revocation_options": RevocationOptions(enabled=True),
                }
            )
            if settings.mcp_auth
            else None
        ),
    )

    @mcp.tool(annotations=READ_ONLY)
    @_tool_errors
    async def list_services() -> list[ServiceOut]:
        """List the payment and hosting services covered by Gotcha, with one fiche per country."""
        return await tools.list_services(services())

    @mcp.tool(annotations=READ_ONLY)
    @_tool_errors
    async def get_fiche(service: str, country: str | None = None) -> FicheOut:
        """Get the full fiche of a service: steps, gotchas, sandbox vs production, status.

        service: service slug from list_services (e.g. "mtn-momo", "wave", "orange-money").
        country: ISO 3166-1 alpha-2 code (e.g. "SN"); omit for a fiche valid in every country.
        """
        return await tools.get_fiche(services(), service, country)

    @mcp.tool(annotations=READ_ONLY)
    @_tool_errors
    async def search_gotchas(
        query: str, service: str | None = None, country: str | None = None
    ) -> list[SearchResultOut]:
        """Search gotchas by keyword, HTTP header, error code or symptom.

        Example: query="X-Target-Environment".
        """
        return await tools.search_gotchas(services(), query, service, country)

    @mcp.tool(annotations=READ_ONLY)
    @_tool_errors
    async def get_service_status(service: str, country: str | None = None) -> StatusOut:
        """Current status of a service in a country: normal, degraded or down, with incidents."""
        return await tools.get_service_status(services(), service, country)

    if not can_write:
        return mcp

    @mcp.tool(annotations=REPORT)
    @_tool_errors
    async def report_outage(
        service: str, description: str, ctx: Context, country: str | None = None
    ) -> OutageReportOut:
        """Report an outage you just observed (failed or timed-out payments). Rate-limited."""
        token = get_access_token()
        subject = token.subject if token is not None else None
        request = getattr(ctx.request_context, "request", None) if ctx else None
        headers = getattr(request, "headers", None) or {}
        peer = request.client.host if request is not None and request.client else None
        who = subject or client_ip(headers, peer, proxy_hops=settings.proxy_hops)
        if not app.state.rate_limiter.hit(
            f"mcp-outage:{who}", limit=REPORT_LIMIT, window_seconds=REPORT_WINDOW_SECONDS
        ):
            raise ToolError("Too many outage reports from this client: retry later.")
        pseudo = await services().oauth.account_pseudo(subject) if subject else None
        return await tools.report_outage(
            services(), service, description, country, reported_by=pseudo or "agent"
        )

    return mcp


def mount_mcp(app: FastAPI, mcp: MCPServer) -> None:
    """Ajoute à l'application FastAPI la route POST /mcp et, si besoin, les routes OAuth.

    On reprend les routes et les middlewares du SDK : sans ses middlewares, même un jeton
    valide serait refusé. Monter son application sur « / » remplacerait les pages d'erreur
    du site (D20). La session du SDK doit tourner pendant toute la vie de l'application :
    voir `mcp.session_manager.run()` dans le lifespan de app/main.py.
    """
    settings = app.state.settings
    security = TransportSecuritySettings(
        enable_dns_rebinding_protection=True,
        allowed_hosts=list(settings.allowed_hosts),
        allowed_origins=[settings.site_url, "http://localhost:*", "http://127.0.0.1:*"],
    )
    sdk_app = mcp.streamable_http_app(
        streamable_http_path="/mcp",
        stateless_http=True,
        json_response=True,
        transport_security=security,
    )
    app.router.routes.extend(sdk_app.routes)
    # add_middleware place le dernier ajouté à l'extérieur : on garde l'ordre du SDK.
    for middleware in reversed(sdk_app.user_middleware):
        app.add_middleware(middleware.cls, *middleware.args, **middleware.kwargs)
