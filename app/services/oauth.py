"""Connexion des agents au serveur MCP : comptes, codes et jetons. Responsable : Abdoul Aziz.

Gotcha est le serveur d'autorisation des outils MCP, et GitHub ne sert qu'à identifier le
développeur. L'agent ne reçoit que des jetons de Gotcha : le jeton GitHub est utilisé une
fois pour lire le profil public, puis oublié. Jetons et codes sont opaques, et le stockage
n'en garde que l'empreinte : bloquer un compte coupe l'accès tout de suite.
"""

from __future__ import annotations

import hashlib
import secrets
from dataclasses import dataclass
from datetime import timedelta
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from app.domain.errors import IdentityError, InvalidInputError
from app.domain.models import Account, OAuthGrantKind
from app.domain.ports import AccountStore, Clock, IdentityProvider

LOGIN_TTL = timedelta(minutes=10)
CODE_TTL = timedelta(minutes=5)
ACCESS_TTL = timedelta(hours=1)
REFRESH_TTL = timedelta(days=30)


def _digest(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _with_query(url: str, **params: str | None) -> str:
    """Ajoute des paramètres à une adresse, sans toucher à ceux qu'elle contient déjà."""
    parts = urlsplit(url)
    query = parse_qsl(parts.query, keep_blank_values=True)
    query += [(key, value) for key, value in params.items() if value is not None]
    return urlunsplit(parts._replace(query=urlencode(query)))


@dataclass(frozen=True)
class TokenPair:
    access_token: str
    refresh_token: str
    expires_in: int


class OAuthService:
    def __init__(
        self,
        store: AccountStore,
        clock: Clock,
        identity: IdentityProvider | None,
        *,
        callback_url: str,
    ) -> None:
        self._store = store
        self._clock = clock
        self._identity = identity
        self._callback_url = callback_url

    async def _new_grant(
        self, kind: OAuthGrantKind, data: dict[str, Any], ttl: timedelta
    ) -> tuple[str, float]:
        token = secrets.token_urlsafe(32)
        expires_at = self._clock.now() + ttl
        stored = {**data, "expires_at": expires_at.timestamp()}
        await self._store.add_oauth_grant(kind, _digest(token), stored, expires_at)
        return token, expires_at.timestamp()

    # --- Outils MCP enregistrés ------------------------------------------------

    async def get_client(self, client_id: str) -> dict[str, Any] | None:
        return await self._store.get_oauth_client(client_id)

    async def register_client(self, client_id: str, data: dict[str, Any]) -> None:
        await self._store.save_oauth_client(client_id, data)

    # --- Connexion du développeur ----------------------------------------------

    async def begin_login(self, data: dict[str, Any]) -> str:
        """Garde la demande de l'outil MCP et renvoie l'adresse de connexion chez GitHub."""
        if self._identity is None:
            raise InvalidInputError("La connexion n'est pas activée sur ce serveur.")
        await self._store.delete_expired_oauth_grants(self._clock.now())
        state, _ = await self._new_grant(OAuthGrantKind.LOGIN, data, LOGIN_TTL)
        return self._identity.authorize_url(state=state, redirect_uri=self._callback_url)

    async def finish_login(self, state: str, code: str | None, error: str | None) -> str:
        """Traite le retour de GitHub ; renvoie l'adresse de retour vers l'outil MCP."""
        if self._identity is None:
            raise InvalidInputError("La connexion n'est pas activée sur ce serveur.")
        login = await self._store.take_oauth_grant(
            OAuthGrantKind.LOGIN, _digest(state), self._clock.now()
        )
        if login is None:
            raise InvalidInputError(
                "Demande de connexion inconnue ou expirée : relancez-la depuis votre outil."
            )
        back, client_state = login["redirect_uri"], login.get("state")
        if error or not code:
            return _with_query(back, error="access_denied", state=client_state)
        try:
            identity = await self._identity.fetch_identity(code, self._callback_url)
        except IdentityError:
            return _with_query(back, error="server_error", state=client_state)

        now = self._clock.now()
        account = await self._store.get_account(identity.id)
        if account is not None and account.blocked:
            return _with_query(back, error="access_denied", state=client_state)
        created_at = account.created_at if account is not None else now
        await self._store.save_account(
            Account(
                id=identity.id, pseudo=identity.pseudo, created_at=created_at, last_login_at=now
            )
        )
        data = {key: value for key, value in login.items() if key != "expires_at"}
        authorization_code, _ = await self._new_grant(
            OAuthGrantKind.CODE, {**data, "subject": identity.id}, CODE_TTL
        )
        return _with_query(back, code=authorization_code, state=client_state)

    # --- Codes et jetons -------------------------------------------------------

    async def get_code(self, code: str) -> dict[str, Any] | None:
        now = self._clock.now()
        return await self._store.get_oauth_grant(OAuthGrantKind.CODE, _digest(code), now)

    async def take_code(self, code: str) -> dict[str, Any] | None:
        """Un code ne sert qu'une fois : le second appel renvoie None."""
        now = self._clock.now()
        return await self._store.take_oauth_grant(OAuthGrantKind.CODE, _digest(code), now)

    async def issue_tokens(
        self, *, client_id: str, subject: str, scopes: list[str], resource: str | None
    ) -> TokenPair:
        data = {"client_id": client_id, "subject": subject, "scopes": scopes, "resource": resource}
        access, _ = await self._new_grant(OAuthGrantKind.ACCESS, data, ACCESS_TTL)
        refresh, _ = await self._new_grant(OAuthGrantKind.REFRESH, data, REFRESH_TTL)
        return TokenPair(access, refresh, int(ACCESS_TTL.total_seconds()))

    async def _for_active_account(self, grant: dict[str, Any] | None) -> dict[str, Any] | None:
        if grant is None:
            return None
        account = await self._store.get_account(grant["subject"])
        return grant if account is not None and not account.blocked else None

    async def get_access(self, token: str) -> dict[str, Any] | None:
        now = self._clock.now()
        grant = await self._store.get_oauth_grant(OAuthGrantKind.ACCESS, _digest(token), now)
        return await self._for_active_account(grant)

    async def get_refresh(self, token: str) -> dict[str, Any] | None:
        now = self._clock.now()
        grant = await self._store.get_oauth_grant(OAuthGrantKind.REFRESH, _digest(token), now)
        return await self._for_active_account(grant)

    async def take_refresh(self, token: str) -> dict[str, Any] | None:
        """Un jeton de renouvellement ne sert qu'une fois : il est remplacé à chaque usage."""
        now = self._clock.now()
        return await self._store.take_oauth_grant(OAuthGrantKind.REFRESH, _digest(token), now)

    async def revoke(self, kind: OAuthGrantKind, token: str) -> None:
        await self._store.take_oauth_grant(kind, _digest(token), self._clock.now())

    async def account_pseudo(self, account_id: str) -> str | None:
        account = await self._store.get_account(account_id)
        return account.pseudo if account is not None else None
