"""Connexion des agents au serveur MCP : comptes, codes et jetons. Responsable : Abdoul Aziz.

Gotcha est le serveur d'autorisation des outils MCP, et GitHub ne sert qu'à identifier le
développeur. L'agent ne reçoit que des jetons de Gotcha : le jeton GitHub est utilisé une
fois pour lire le profil public, puis oublié. Jetons et codes sont opaques, et le stockage
n'en garde que l'empreinte : bloquer un compte coupe l'accès tout de suite.
"""

from __future__ import annotations

import hashlib
import json
import secrets
from dataclasses import dataclass
from datetime import timedelta
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from app.domain.errors import IdentityError, InvalidInputError
from app.domain.models import Account, OAuthGrantKind, is_storable
from app.domain.ports import AccountStore, Clock, IdentityProvider

# Taille maximale de la description d'un outil (/register est ouvert à tous).
MAX_CLIENT_NAME = 100
MAX_REDIRECT_URIS = 5
MAX_REDIRECT_URI_LENGTH = 500
MAX_CLIENT_DATA_BYTES = 4096
LOOPBACK_HOSTS = {"localhost", "127.0.0.1", "[::1]", "::1"}
# Schémas qui exécuteraient du code ou liraient un fichier au lieu de rendre la main à l'outil.
FORBIDDEN_SCHEMES = {"javascript", "data", "file", "vbscript", "about", "blob"}

LOGIN_TTL = timedelta(minutes=10)
CODE_TTL = timedelta(minutes=5)
ACCESS_TTL = timedelta(hours=1)
REFRESH_TTL = timedelta(days=30)


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


def redirect_uri_problem(uri: str) -> str | None:
    """Pourquoi une adresse de retour est refusée, ou None si elle est acceptable.

    https partout ; http seulement vers la machine elle-même (outils en ligne de commande) ;
    les schémas propres à une application (cursor://, vscode://) restent permis, car l'écran
    de consentement affiche l'adresse avant toute connexion.
    """
    if len(uri) > MAX_REDIRECT_URI_LENGTH:
        return "adresse de retour trop longue"
    parts = urlsplit(uri)
    scheme = parts.scheme.lower()
    if not scheme or scheme in FORBIDDEN_SCHEMES:
        return f"schéma d'adresse de retour refusé : {scheme or 'aucun'}"
    if scheme == "http" and (parts.hostname or "").lower() not in LOOPBACK_HOSTS:
        return "http n'est permis que vers la machine locale (localhost, 127.0.0.1)"
    if scheme in ("http", "https") and not parts.hostname:
        return "adresse de retour sans nom de machine"
    return None


def _with_query(url: str, **params: str | None) -> str:
    """Ajoute des paramètres à une adresse, sans toucher à ceux qu'elle contient déjà."""
    parts = urlsplit(url)
    query = parse_qsl(parts.query, keep_blank_values=True)
    query += [(key, value) for key, value in params.items() if value is not None]
    return urlunsplit(parts._replace(query=urlencode(query)))


@dataclass(frozen=True)
class LoginRequest:
    """Ce que l'écran de consentement montre au développeur."""

    client_name: str
    redirect_uri: str


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
        consent_url: str,
    ) -> None:
        self._store = store
        self._clock = clock
        self._identity = identity
        self._callback_url = callback_url
        self._consent_url = consent_url

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
        if len(str(data.get("client_name") or "")) > MAX_CLIENT_NAME:
            raise InvalidInputError(
                f"Nom de l'outil trop long ({MAX_CLIENT_NAME} caractères au plus)."
            )
        uris = [str(uri) for uri in data.get("redirect_uris") or []]
        if len(uris) > MAX_REDIRECT_URIS:
            raise InvalidInputError(f"{MAX_REDIRECT_URIS} adresses de retour au plus.")
        for uri in uris:
            if problem := redirect_uri_problem(uri):
                raise InvalidInputError(f"Adresse de retour refusée : {problem}.")
        if len(json.dumps(data).encode()) > MAX_CLIENT_DATA_BYTES:
            raise InvalidInputError("Description de l'outil trop longue.")
        await self._store.save_oauth_client(client_id, data)

    # --- Connexion du développeur ----------------------------------------------

    async def begin_login(self, data: dict[str, Any]) -> str:
        """Garde la demande de l'outil MCP et renvoie l'adresse de l'écran de consentement.

        Sans cet écran, n'importe qui pourrait enregistrer un outil avec sa propre adresse
        de retour, puis envoyer le lien /authorize à un développeur déjà connu de GitHub :
        GitHub répondrait sans rien demander et le code partirait chez l'attaquant.
        """
        if self._identity is None:
            raise InvalidInputError("La connexion n'est pas activée sur ce serveur.")
        if not _storable(data):
            raise InvalidInputError("Demande de connexion invalide (caractère interdit).")
        await self._store.delete_expired_oauth_grants(self._clock.now())
        state, _ = await self._new_grant(OAuthGrantKind.LOGIN, data, LOGIN_TTL)
        return _with_query(self._consent_url, demande=state)

    async def describe_login(self, state: str) -> LoginRequest | None:
        """La demande en attente, pour l'écran de consentement ; None si inconnue ou expirée."""
        if not is_storable(state):
            return None
        now = self._clock.now()
        login = await self._store.get_oauth_grant(OAuthGrantKind.LOGIN, _digest(state), now)
        if login is None:
            return None
        client = await self._store.get_oauth_client(login["client_id"]) or {}
        name = str(client.get("client_name") or login["client_id"])
        return LoginRequest(client_name=name, redirect_uri=login["redirect_uri"])

    async def approve_login(self, state: str) -> str:
        """Le développeur accepte : renvoie l'adresse de connexion chez GitHub."""
        if self._identity is None or await self.describe_login(state) is None:
            raise InvalidInputError(
                "Demande de connexion inconnue ou expirée : relancez-la depuis votre outil."
            )
        return self._identity.authorize_url(state=state, redirect_uri=self._callback_url)

    async def refuse_login(self, state: str) -> str:
        """Le développeur refuse : la demande est effacée, l'outil reçoit access_denied."""
        login = None
        if is_storable(state):
            now = self._clock.now()
            login = await self._store.take_oauth_grant(OAuthGrantKind.LOGIN, _digest(state), now)
        if login is None:
            raise InvalidInputError(
                "Demande de connexion inconnue ou expirée : relancez-la depuis votre outil."
            )
        return _with_query(login["redirect_uri"], error="access_denied", state=login.get("state"))

    async def finish_login(self, state: str, code: str | None, error: str | None) -> str:
        """Traite le retour de GitHub ; renvoie l'adresse de retour vers l'outil MCP."""
        if self._identity is None:
            raise InvalidInputError("La connexion n'est pas activée sur ce serveur.")
        login = (
            await self._store.take_oauth_grant(
                OAuthGrantKind.LOGIN, _digest(state), self._clock.now()
            )
            if is_storable(state)
            else None
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
