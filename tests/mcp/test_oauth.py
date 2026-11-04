"""Connexion au serveur MCP : le parcours d'un outil MCP, avec un faux GitHub."""

from __future__ import annotations

import base64
import hashlib
import json
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from io import BytesIO
from typing import Any
from urllib.parse import parse_qs, urlparse

import pytest
from starlette.testclient import TestClient

from app.config import Settings
from app.domain.errors import IdentityError
from app.domain.models import Account, ExternalIdentity, OAuthGrantKind
from app.security import github
from app.security.github import GitHubIdentity
from app.services.clock import FixedClock
from app.stores.memory.store import MemoryStore
from tests.conftest import NOW, make_client

CALLBACK = "http://localhost:9000/callback"
RESOURCE = "http://localhost:8000/mcp"
VERIFIER = "v" * 64
CHALLENGE = (
    base64.urlsafe_b64encode(hashlib.sha256(VERIFIER.encode()).digest()).rstrip(b"=").decode()
)
MCP_HEADERS = {"Accept": "application/json, text/event-stream"}
TOOLS_LIST = {"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}}


class FakeIdentity:
    def authorize_url(self, *, state: str, redirect_uri: str) -> str:
        return f"https://github.example/authorize?state={state}&redirect_uri={redirect_uri}"

    async def fetch_identity(self, code: str, redirect_uri: str) -> ExternalIdentity:
        if code == "mauvais":
            raise IdentityError("échec")
        assert redirect_uri.endswith("/github/callback")
        return ExternalIdentity(id="github:42", pseudo="aminata")


@pytest.fixture
def clock() -> FixedClock:
    """Le SDK compare les expirations à l'heure réelle : on part donc de l'heure réelle."""
    return FixedClock(datetime.now(UTC))


AUTH_SETTINGS = Settings(
    env="test", mcp_auth=True, github_client_id="identifiant", github_client_secret="secret"
)


@pytest.fixture
def store() -> MemoryStore:
    return MemoryStore.from_directories(AUTH_SETTINGS.content_dir, None, now=NOW)


@pytest.fixture
def auth_client(store: MemoryStore, clock: FixedClock) -> Iterator[TestClient]:
    with make_client(AUTH_SETTINGS, clock, identity=FakeIdentity(), store=store) as client:
        yield client


def register(client: TestClient) -> dict[str, Any]:
    response = client.post(
        "/register",
        json={
            "client_name": "outil",
            "redirect_uris": [CALLBACK],
            "grant_types": ["authorization_code", "refresh_token"],
            "response_types": ["code"],
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def start_login(client: TestClient, oauth_client: dict[str, Any], resource: str = RESOURCE) -> str:
    """Demande la connexion ; renvoie l'état transmis à GitHub."""
    response = client.get(
        "/authorize",
        params={
            "response_type": "code",
            "client_id": oauth_client["client_id"],
            "redirect_uri": CALLBACK,
            "state": "etat-outil",
            "code_challenge": CHALLENGE,
            "code_challenge_method": "S256",
            "resource": resource,
        },
        follow_redirects=False,
    )
    assert response.status_code == 302, response.text
    return parse_qs(urlparse(response.headers["location"]).query)["state"][0]


def github_returns(client: TestClient, **params: str) -> dict[str, list[str]]:
    response = client.get("/github/callback", params=params, follow_redirects=False)
    assert response.status_code == 302, response.text
    location = response.headers["location"]
    assert location.startswith(CALLBACK)
    return parse_qs(urlparse(location).query)


def get_code(client: TestClient, oauth_client: dict[str, Any], resource: str = RESOURCE) -> str:
    state = start_login(client, oauth_client, resource)
    query = github_returns(client, state=state, code="bon")
    assert query["state"] == ["etat-outil"]
    return query["code"][0]


def token_form(oauth_client: dict[str, Any], code: str, verifier: str = VERIFIER) -> dict[str, str]:
    return {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": CALLBACK,
        "client_id": oauth_client["client_id"],
        "client_secret": oauth_client["client_secret"],
        "code_verifier": verifier,
        "resource": RESOURCE,
    }


def connect(client: TestClient) -> tuple[dict[str, Any], dict[str, Any]]:
    oauth_client = register(client)
    response = client.post("/token", data=token_form(oauth_client, get_code(client, oauth_client)))
    assert response.status_code == 200, response.text
    return oauth_client, response.json()


def post_mcp(client: TestClient, token: str | None, body: dict[str, Any] | None = None) -> Any:
    headers = dict(MCP_HEADERS)
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return client.post("/mcp", json=body or TOOLS_LIST, headers=headers)


def refresh_form(oauth_client: dict[str, Any], refresh_token: str) -> dict[str, str]:
    return {
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
        "client_id": oauth_client["client_id"],
        "client_secret": oauth_client["client_secret"],
    }


def test_mcp_refuses_anonymous_calls_and_explains_how_to_connect(auth_client: TestClient) -> None:
    response = post_mcp(auth_client, None)
    assert response.status_code == 401
    metadata_url = (
        response.headers["www-authenticate"].split('resource_metadata="')[1].split('"')[0]
    )
    metadata = auth_client.get(urlparse(metadata_url).path).json()
    assert metadata["resource"] == RESOURCE
    server = auth_client.get("/.well-known/oauth-authorization-server").json()
    assert server["issuer"] == "http://localhost:8000"
    assert "S256" in server["code_challenge_methods_supported"]
    assert server["registration_endpoint"].endswith("/register")


def test_connected_agent_can_use_the_tools(auth_client: TestClient) -> None:
    _, tokens = connect(auth_client)
    response = post_mcp(auth_client, tokens["access_token"])
    assert response.status_code == 200, response.text
    names = {tool["name"] for tool in response.json()["result"]["tools"]}
    assert {"get_fiche", "report_outage"} <= names
    assert tokens["token_type"].lower() == "bearer"


@pytest.mark.anyio
async def test_outage_report_names_the_account(auth_client: TestClient, store: MemoryStore) -> None:
    _, tokens = connect(auth_client)
    body = {
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/call",
        "params": {
            "name": "report_outage",
            "arguments": {"service": "wave", "country": "SN", "description": "Paiements bloqués."},
        },
    }
    assert post_mcp(auth_client, tokens["access_token"], body).status_code == 200
    incidents = await store.list_incidents(service_slug="wave", country="SN")
    assert incidents[0].reported_by == "aminata"


@pytest.mark.parametrize("token", ["faux", ""])
def test_invalid_tokens_are_refused(auth_client: TestClient, token: str) -> None:
    assert post_mcp(auth_client, token).status_code == 401


def test_code_works_once_and_needs_the_right_pkce(auth_client: TestClient) -> None:
    oauth_client = register(auth_client)
    code = get_code(auth_client, oauth_client)
    wrong = auth_client.post("/token", data=token_form(oauth_client, code, "m" * 64))
    assert wrong.status_code == 400
    assert auth_client.post("/token", data=token_form(oauth_client, code)).status_code == 200
    assert auth_client.post("/token", data=token_form(oauth_client, code)).status_code == 400


def test_code_is_tied_to_its_client(auth_client: TestClient) -> None:
    owner, other = register(auth_client), register(auth_client)
    code = get_code(auth_client, owner)
    assert auth_client.post("/token", data=token_form(other, code)).status_code == 400


def test_token_for_another_server_is_refused(auth_client: TestClient) -> None:
    oauth_client = register(auth_client)
    code = get_code(auth_client, oauth_client, resource="https://ailleurs.example/mcp")
    form = {**token_form(oauth_client, code), "resource": "https://ailleurs.example/mcp"}
    tokens = auth_client.post("/token", data=form).json()
    assert post_mcp(auth_client, tokens["access_token"]).status_code == 401


def test_refresh_token_is_replaced_at_each_use(auth_client: TestClient) -> None:
    oauth_client, tokens = connect(auth_client)
    form = refresh_form(oauth_client, tokens["refresh_token"])
    renewed = auth_client.post("/token", data=form)
    assert renewed.status_code == 200, renewed.text
    assert post_mcp(auth_client, renewed.json()["access_token"]).status_code == 200
    assert auth_client.post("/token", data=form).status_code == 400


def test_expired_access_token_is_refused_then_renewed(
    auth_client: TestClient, clock: FixedClock
) -> None:
    oauth_client, tokens = connect(auth_client)
    clock.at += timedelta(hours=2)
    assert post_mcp(auth_client, tokens["access_token"]).status_code == 401
    form = refresh_form(oauth_client, tokens["refresh_token"])
    assert auth_client.post("/token", data=form).status_code == 200


async def _block(store: MemoryStore) -> None:
    await store.save_account(
        Account(id="github:42", pseudo="aminata", created_at=NOW, last_login_at=NOW, blocked=True)
    )


@pytest.mark.anyio
async def test_blocking_an_account_cuts_access_at_once(
    auth_client: TestClient, store: MemoryStore
) -> None:
    oauth_client, tokens = connect(auth_client)
    await _block(store)
    assert post_mcp(auth_client, tokens["access_token"]).status_code == 401
    form = refresh_form(oauth_client, tokens["refresh_token"])
    assert auth_client.post("/token", data=form).status_code == 400
    state = start_login(auth_client, oauth_client)
    assert github_returns(auth_client, state=state, code="bon")["error"] == ["access_denied"]


def test_connection_survives_a_restart(
    auth_client: TestClient, store: MemoryStore, clock: FixedClock
) -> None:
    _, tokens = connect(auth_client)
    with make_client(AUTH_SETTINGS, clock, identity=FakeIdentity(), store=store) as restarted:
        assert post_mcp(restarted, tokens["access_token"]).status_code == 200


@pytest.mark.anyio
async def test_tokens_are_stored_as_digests_only(
    auth_client: TestClient, store: MemoryStore, clock: FixedClock
) -> None:
    _, tokens = connect(auth_client)
    token = tokens["access_token"]
    assert await store.get_oauth_grant(OAuthGrantKind.ACCESS, token, clock.now()) is None
    digest = hashlib.sha256(token.encode()).hexdigest()
    assert await store.get_oauth_grant(OAuthGrantKind.ACCESS, digest, clock.now()) is not None


def test_refusal_on_github_goes_back_to_the_tool(auth_client: TestClient) -> None:
    state = start_login(auth_client, register(auth_client))
    query = github_returns(auth_client, state=state, error="access_denied")
    assert query == {"error": ["access_denied"], "state": ["etat-outil"]}


def test_github_failure_goes_back_to_the_tool(auth_client: TestClient) -> None:
    state = start_login(auth_client, register(auth_client))
    query = github_returns(auth_client, state=state, code="mauvais")
    assert query["error"] == ["server_error"]


def test_unknown_or_reused_login_is_refused(auth_client: TestClient) -> None:
    assert (
        auth_client.get("/github/callback", params={"state": "faux", "code": "x"}).status_code
        == 400
    )
    state = start_login(auth_client, register(auth_client))
    github_returns(auth_client, state=state, code="bon")
    reused = auth_client.get("/github/callback", params={"state": state, "code": "x"})
    assert reused.status_code == 400
    assert "relancez-la" in reused.text


def test_login_expires(auth_client: TestClient, clock: FixedClock) -> None:
    state = start_login(auth_client, register(auth_client))
    clock.at += timedelta(minutes=11)
    assert auth_client.get("/github/callback", params={"state": state}).status_code == 400


def test_site_keeps_its_error_pages(auth_client: TestClient) -> None:
    response = auth_client.get("/page-inexistante")
    assert response.status_code == 404
    assert "<html" in response.text.lower()


def test_registration_has_a_quota(auth_client: TestClient) -> None:
    body = {"client_name": "x", "redirect_uris": [CALLBACK]}
    codes = [auth_client.post("/register", json=body).status_code for _ in range(21)]
    assert codes[:20] == [201] * 20
    assert codes[20] == 429


def test_callback_does_not_exist_without_the_connection(client: TestClient) -> None:
    assert client.get("/github/callback", params={"state": "x"}).status_code == 404


def test_production_without_connection_only_exposes_reading(prod_client: TestClient) -> None:
    response = prod_client.post("/mcp", json=TOOLS_LIST, headers=MCP_HEADERS)
    assert response.status_code == 200, response.text
    names = {tool["name"] for tool in response.json()["result"]["tools"]}
    assert names == {"list_services", "get_fiche", "search_gotchas", "get_service_status"}


# --- GitHub --------------------------------------------------------------------


def test_github_login_asks_for_no_permission() -> None:
    url = GitHubIdentity("identifiant", "secret").authorize_url(
        state="etat", redirect_uri="https://gotcha.test/github/callback"
    )
    query = parse_qs(urlparse(url).query)
    assert url.startswith("https://github.com/login/oauth/authorize?")
    assert sorted(query) == ["client_id", "redirect_uri", "state"]


class _Answer(BytesIO):
    def __enter__(self) -> _Answer:
        return self


def _fake_github(monkeypatch: pytest.MonkeyPatch, *answers: dict[str, Any]) -> list[Any]:
    requests: list[Any] = []
    remaining = list(answers)

    def urlopen(request: Any, timeout: float) -> _Answer:
        assert timeout > 0
        requests.append(request)
        return _Answer(json.dumps(remaining.pop(0)).encode())

    monkeypatch.setattr(github.urllib.request, "urlopen", urlopen)
    return requests


@pytest.mark.anyio
async def test_github_identity_reads_the_public_profile(monkeypatch: pytest.MonkeyPatch) -> None:
    requests = _fake_github(
        monkeypatch, {"access_token": "jeton-github"}, {"id": 42, "login": "aminata"}
    )
    identity = await GitHubIdentity("identifiant", "secret").fetch_identity("code", "https://x")
    assert identity == ExternalIdentity(id="github:42", pseudo="aminata")
    assert requests[1].get_header("Authorization") == "Bearer jeton-github"


@pytest.mark.anyio
async def test_github_failure_hides_the_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    _fake_github(monkeypatch, {"error": "bad_verification_code"})
    with pytest.raises(IdentityError) as caught:
        await GitHubIdentity("identifiant", "secret-a-cacher").fetch_identity("code", "https://x")
    assert "secret-a-cacher" not in str(caught.value)
    assert caught.value.__cause__ is None
