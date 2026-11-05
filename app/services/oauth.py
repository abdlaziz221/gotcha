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
from app.domain.models import Account, ExternalIdentity, OAuthGrantKind, is_storable
from app.domain.ports import AccountStore, Clock, IdentityProvider

LOGIN_TTL = timedelta(minutes=10)
CODE_TTL = timedelta(minutes=5)
ACCESS_TTL = timedelta(hours=1)
REFRESH_TTL = timedelta(days=30)
SESSION_TTL = timedelta(days=30)
JURY_ACCOUNT = ExternalIdentity(id="jury:code", pseudo="jury")


def _digest(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _storable(value: object) -> bool:
    """Faux si un texte de la description d'un outil ne peut pas être enregistré (octet nul)."""
    if isinstance(value, str):
        return is_storable(value)
    if isinstance(value, dict):
        return all(_storable(k) and _storable(v) for k, v in value.items())
    if isinstance(value, list | tuple):
        return all(_storable(v) for v in value)
    return True


def _with_query(url: str, **params: str | None) -> str:
    """Ajoute des paramètres à une adresse, sans toucher à ceux qu'elle contient déjà."""
    parts = urlsplit(url)
    query = parse_qsl(parts.query, keep_blank_values=True)
    query += [(key, value) for key, value in params.items() if value is not None]
    return urlunsplit(parts._replace(query=urlencode(query)))


def safe_next_url(url: str) -> str:
    """Adresse de retour après connexion : seulement une page de ce site."""
    if not url.startswith("/") or url.startswith("//") or "\\" in url:
        return "/"
    return url


@dataclass(frozen=True)
class LoginResult:
    redirect_url: str
    session_token: str | None = None


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
        jury_code: str = "",
    ) -> None:
        self._store = store
        self._clock = clock
        self._identity = identity
        self._callback_url = callback_url
        self._jury_code = jury_code

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
        if not _storable(data):
            raise InvalidInputError("Description de l'outil invalide (caractère interdit).")
        await self._store.save_oauth_client(client_id, data)

    # --- Connexion du développeur ----------------------------------------------

    async def begin_login(self, data: dict[str, Any]) -> str:
        """Garde la demande de l'outil MCP et renvoie l'adresse de connexion chez GitHub."""
        if self._identity is None:
            raise InvalidInputError("La connexion n'est pas activée sur ce serveur.")
        await self._store.delete_expired_oauth_grants(self._clock.now())
        state, _ = await self._new_grant(OAuthGrantKind.LOGIN, data, LOGIN_TTL)
        return self._identity.authorize_url(state=state, redirect_uri=self._callback_url)

    async def begin_web_login(self, next_url: str) -> str:
        """Connexion sur le site : renvoie l'adresse de connexion chez GitHub."""
        return await self.begin_login({"web": True, "next": safe_next_url(next_url)})

    async def finish_login(self, state: str, code: str | None, error: str | None) -> LoginResult:
        """Traite le retour de GitHub : vers l'outil MCP, ou vers le site avec une session."""
        if self._identity is None:
            raise InvalidInputError("La connexion n'est pas activée sur ce serveur.")
        login = await self._store.take_oauth_grant(
            OAuthGrantKind.LOGIN, _digest(state), self._clock.now()
        )
        if login is None:
            raise InvalidInputError(
                "Demande de connexion inconnue ou expirée : relancez la connexion."
            )

        def refused(reason: str) -> LoginResult:
            if login.get("web"):
                query = urlencode({"erreur": "bloque" if reason == "blocked" else "refus"})
                query += "&" + urlencode({"retour": login["next"]})
                return LoginResult(f"/connexion?{query}")
            mcp_error = "server_error" if reason == "failed" else "access_denied"
            return LoginResult(
                _with_query(login["redirect_uri"], error=mcp_error, state=login.get("state"))
            )

        if error or not code:
            return refused("denied")
        try:
            identity = await self._identity.fetch_identity(code, self._callback_url)
        except IdentityError:
            return refused("failed")
        if not await self._save_account(identity):
            return refused("blocked")

        if login.get("web"):
            token = await self._new_session(identity.id)
            return LoginResult(login["next"], session_token=token)
        data = {key: value for key, value in login.items() if key != "expires_at"}
        authorization_code, _ = await self._new_grant(
            OAuthGrantKind.CODE, {**data, "subject": identity.id}, CODE_TTL
        )
        return LoginResult(
            _with_query(login["redirect_uri"], code=authorization_code, state=login.get("state"))
        )

    async def _save_account(self, identity: ExternalIdentity) -> bool:
        """Crée ou met à jour le compte ; renvoie False s'il est bloqué."""
        now = self._clock.now()
        account = await self._store.get_account(identity.id)
        if account is not None and account.blocked:
            return False
        created_at = account.created_at if account is not None else now
        await self._store.save_account(
            Account(
                id=identity.id, pseudo=identity.pseudo, created_at=created_at, last_login_at=now
            )
        )
        return True

    async def _new_session(self, account_id: str) -> str:
        token, _ = await self._new_grant(
            OAuthGrantKind.SESSION, {"subject": account_id}, SESSION_TTL
        )
        return token

    async def login_with_code(self, code: str) -> str | None:
        """Accès du jury ; renvoie un jeton de session, ou None si le code est faux."""
        if not self._jury_code or not secrets.compare_digest(code, self._jury_code):
            return None
        if not await self._save_account(JURY_ACCOUNT):
            return None
        return await self._new_session(JURY_ACCOUNT.id)

    async def session_account(self, token: str) -> Account | None:
        now = self._clock.now()
        grant = await self._store.get_oauth_grant(OAuthGrantKind.SESSION, _digest(token), now)
        if grant is None:
            return None
        account = await self._store.get_account(grant["subject"])
        return account if account is not None and not account.blocked else None

    async def end_session(self, token: str) -> None:
        await self.revoke(OAuthGrantKind.SESSION, token)

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
