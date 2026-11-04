"""Traduit les appels OAuth du SDK MCP vers OAuthService. Responsable : Abdoul Aziz.

Le SDK fournit les routes (/authorize, /token, /register, /revoke), PKCE et la découverte
(réponse 401, métadonnées). Toute la logique et le stockage sont dans app/services/oauth.py.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

from mcp.server.auth.provider import (
    AccessToken,
    AuthorizationCode,
    AuthorizationParams,
    OAuthAuthorizationServerProvider,
    RefreshToken,
)
from mcp.shared.auth import OAuthClientInformationFull, OAuthToken

from app.domain.models import OAuthGrantKind

if TYPE_CHECKING:
    from app.container import Services
    from app.services.oauth import OAuthService, TokenPair


def _oauth_token(pair: TokenPair, scopes: list[str]) -> OAuthToken:
    return OAuthToken(
        access_token=pair.access_token,
        token_type="Bearer",  # noqa: S106 (type de jeton, pas un secret)
        expires_in=pair.expires_in,
        refresh_token=pair.refresh_token,
        scope=" ".join(scopes) or None,
    )


class GotchaOAuthProvider(
    OAuthAuthorizationServerProvider[AuthorizationCode, RefreshToken, AccessToken]
):
    def __init__(self, services: Callable[[], Services], *, resource_url: str) -> None:
        self._services = services
        self._resource_url = resource_url

    @property
    def _oauth(self) -> OAuthService:
        return self._services().oauth

    async def get_client(self, client_id: str) -> OAuthClientInformationFull | None:
        data = await self._oauth.get_client(client_id)
        return OAuthClientInformationFull.model_validate(data) if data else None

    async def register_client(self, client_info: OAuthClientInformationFull) -> None:
        await self._oauth.register_client(
            client_info.client_id, client_info.model_dump(mode="json")
        )

    async def authorize(
        self, client: OAuthClientInformationFull, params: AuthorizationParams
    ) -> str:
        data = params.model_dump(mode="json")
        return await self._oauth.begin_login({**data, "client_id": client.client_id})

    async def load_authorization_code(
        self, client: OAuthClientInformationFull, authorization_code: str
    ) -> AuthorizationCode | None:
        data = await self._oauth.get_code(authorization_code)
        if data is None or data["client_id"] != client.client_id:
            return None
        return AuthorizationCode(
            code=authorization_code,
            scopes=data["scopes"] or [],
            expires_at=data["expires_at"],
            client_id=data["client_id"],
            code_challenge=data["code_challenge"],
            redirect_uri=data["redirect_uri"],
            redirect_uri_provided_explicitly=data["redirect_uri_provided_explicitly"],
            resource=data["resource"],
            subject=data["subject"],
        )

    async def exchange_authorization_code(
        self,
        client: OAuthClientInformationFull,  # noqa: ARG002 (imposé par le SDK)
        authorization_code: AuthorizationCode,
    ) -> OAuthToken:
        if await self._oauth.take_code(authorization_code.code) is None:
            raise ValueError("code déjà utilisé")
        pair = await self._oauth.issue_tokens(
            client_id=authorization_code.client_id,
            subject=authorization_code.subject or "",
            scopes=authorization_code.scopes,
            resource=authorization_code.resource or self._resource_url,
        )
        return _oauth_token(pair, authorization_code.scopes)

    async def load_refresh_token(
        self, client: OAuthClientInformationFull, refresh_token: str
    ) -> RefreshToken | None:
        data = await self._oauth.get_refresh(refresh_token)
        if data is None or data["client_id"] != client.client_id:
            return None
        return RefreshToken(
            token=refresh_token,
            client_id=data["client_id"],
            scopes=data["scopes"],
            expires_at=int(data["expires_at"]),
            resource=data["resource"],
            subject=data["subject"],
        )

    async def exchange_refresh_token(
        self,
        client: OAuthClientInformationFull,  # noqa: ARG002 (imposé par le SDK)
        refresh_token: RefreshToken,
        scopes: list[str],
    ) -> OAuthToken:
        if await self._oauth.take_refresh(refresh_token.token) is None:
            raise ValueError("jeton de renouvellement déjà utilisé")
        kept = scopes or refresh_token.scopes
        pair = await self._oauth.issue_tokens(
            client_id=refresh_token.client_id,
            subject=refresh_token.subject or "",
            scopes=kept,
            resource=refresh_token.resource,
        )
        return _oauth_token(pair, kept)

    async def load_access_token(self, token: str) -> AccessToken | None:
        data = await self._oauth.get_access(token)
        if data is None:
            return None
        return AccessToken(
            token=token,
            client_id=data["client_id"],
            scopes=data["scopes"],
            expires_at=int(data["expires_at"]),
            resource=data["resource"],
            subject=data["subject"],
        )

    async def revoke_token(self, token: AccessToken | RefreshToken) -> None:
        kind = OAuthGrantKind.REFRESH if isinstance(token, RefreshToken) else OAuthGrantKind.ACCESS
        await self._oauth.revoke(kind, token.token)
