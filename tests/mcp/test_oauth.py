"""Connexion au serveur MCP : le parcours d'un outil MCP, avec un faux GitHub."""

from __future__ import annotations

import base64
import hashlib
import json
import re
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
from tests.conftest import NOW, FakeIdentity, make_client

CALLBACK = "http://localhost:9000/callback"
RESOURCE = "http://localhost:8000/mcp"
VERIFIER = "v" * 64
CHALLENGE = (
    base64.urlsafe_b64encode(hashlib.sha256(VERIFIER.encode()).digest()).rstrip(b"=").decode()
)
MCP_HEADERS = {"Accept": "application/json, text/event-stream"}
TOOLS_LIST = {"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}}


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


def ask_login(client: TestClient, oauth_client: dict[str, Any], resource: str = RESOURCE) -> str:
    """Demande la connexion ; renvoie l'adresse de l'écran de consentement."""
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
    location = urlparse(response.headers["location"])
    assert location.path == "/connexion/outil"
    return f"{location.path}?{location.query}"


def answer_consent(client: TestClient, consent_url: str, decision: str) -> Any:
    page = client.get(consent_url)
    assert page.status_code == 200, page.text
    token = re.search(r'name="csrf_token" value="([^"]+)"', page.text)
    assert token
    demande = parse_qs(urlparse(consent_url).query)["demande"][0]
    form = {"csrf_token": token.group(1), "demande": demande, "decision": decision}
    return client.post("/connexion/outil", data=form, follow_redirects=False)


def start_login(client: TestClient, oauth_client: dict[str, Any], resource: str = RESOURCE) -> str:
    """Demande la connexion et l'accepte ; renvoie l'état transmis à GitHub."""
    response = answer_consent(client, ask_login(client, oauth_client, resource), "autoriser")
    assert response.status_code == 303, response.text
    assert response.headers["location"].startswith("https://github.example/authorize")
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
    # Identifiant stable : un compte renommé reste une seule personne.
    assert incidents[0].reported_by == "github:42"


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
    assert "relancez la connexion" in reused.text


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


# --- Proposer et confirmer ---------------------------------------------------------


def call_tool(client: TestClient, token: str, name: str, **arguments: Any) -> dict[str, Any]:
    body = {
        "jsonrpc": "2.0",
        "id": 3,
        "method": "tools/call",
        "params": {"name": name, "arguments": arguments},
    }
    response = post_mcp(client, token, body)
    assert response.status_code == 200, response.text
    return response.json()["result"]


PROPOSAL = {
    "service": "mtn-momo",
    "title": "Le callback exige une URL en HTTPS",
    "symptom": "Aucun callback n'arrive en bac à sable.",
    "cause": "Le service refuse les adresses en HTTP.",
    "fix": "Exposer une adresse en HTTPS.",
    "failed_attempts": "Changer de clé n'a rien changé.",
    "proof": "API v1, appel avec HTTPS réussi, sans HTTPS aucun appel reçu.",
}


def test_contributing_tools_only_exist_with_the_connection(
    auth_client: TestClient, client: TestClient
) -> None:
    _, tokens = connect(auth_client)
    names = {
        tool["name"]
        for tool in post_mcp(auth_client, tokens["access_token"]).json()["result"]["tools"]
    }
    assert {"propose_gotcha", "confirm_gotcha"} <= names
    anonymous = {tool["name"] for tool in post_mcp(client, None).json()["result"]["tools"]}
    assert not {"propose_gotcha", "confirm_gotcha"} & anonymous


@pytest.mark.anyio
async def test_proposal_needs_the_approval_of_the_developer(
    auth_client: TestClient, store: MemoryStore
) -> None:
    _, tokens = connect(auth_client)
    result = call_tool(
        auth_client, tokens["access_token"], "propose_gotcha", **PROPOSAL, developer_approved=False
    )
    assert result["isError"] is True
    assert "developer" in result["content"][0]["text"]
    assert await store.list_contributions() == []


@pytest.mark.anyio
async def test_proposal_waits_for_a_human_under_the_account(
    auth_client: TestClient, store: MemoryStore
) -> None:
    _, tokens = connect(auth_client)
    result = call_tool(
        auth_client, tokens["access_token"], "propose_gotcha", **PROPOSAL, developer_approved=True
    )
    assert result["structuredContent"]["status"] == "pending"
    saved = (await store.list_contributions())[0]
    assert saved.pseudo == "aminata"
    assert saved.account_id == "github:42"
    assert saved.email is None
    for heading in (
        "## Symptôme",
        "## Cause",
        "## Solution",
        "## Pistes qui ont échoué",
        "## Preuve",
    ):
        assert heading in saved.body_md
    fiche = await store.get_fiche("mtn-momo", include_drafts=True)
    assert fiche is not None
    assert PROPOSAL["title"] not in [gotcha.title for gotcha in fiche.gotchas]


@pytest.mark.anyio
async def test_proposal_with_a_secret_is_refused(
    auth_client: TestClient, store: MemoryStore
) -> None:
    _, tokens = connect(auth_client)
    result = call_tool(
        auth_client,
        tokens["access_token"],
        "propose_gotcha",
        **{**PROPOSAL, "proof": "-----BEGIN " + "PRIVATE KEY-----"},
        developer_approved=True,
    )
    assert result["isError"] is True
    assert "PRIVATE KEY" not in result["content"][0]["text"]
    assert await store.list_contributions() == []


@pytest.mark.parametrize(
    ("change", "expected"),
    [({"title": "x"}, "title"), ({"source_url": "pas une adresse"}, "source_url")],
)
def test_invalid_proposal_is_a_readable_error(
    auth_client: TestClient, change: dict[str, str], expected: str
) -> None:
    _, tokens = connect(auth_client)
    result = call_tool(
        auth_client,
        tokens["access_token"],
        "propose_gotcha",
        **{**PROPOSAL, **change},
        developer_approved=True,
    )
    assert result["isError"] is True
    assert expected in result["content"][0]["text"]


def test_proposal_for_an_unknown_service_is_refused(auth_client: TestClient) -> None:
    _, tokens = connect(auth_client)
    result = call_tool(
        auth_client,
        tokens["access_token"],
        "propose_gotcha",
        **{**PROPOSAL, "service": "inconnu"},
        developer_approved=True,
    )
    assert result["isError"] is True


def test_proposals_have_a_quota(auth_client: TestClient) -> None:
    _, tokens = connect(auth_client)
    results = [
        call_tool(
            auth_client,
            tokens["access_token"],
            "propose_gotcha",
            **PROPOSAL,
            developer_approved=True,
        )
        for _ in range(11)
    ]
    assert not results[9].get("isError")
    assert results[10]["isError"] is True


@pytest.mark.anyio
async def test_confirmation_needs_a_proof_and_counts_once(
    auth_client: TestClient, store: MemoryStore
) -> None:
    _, tokens = connect(auth_client)
    token = tokens["access_token"]
    gotcha_id = "mtn-momo.x-target-environment"
    empty = call_tool(
        auth_client, token, "confirm_gotcha", gotcha_id=gotcha_id, still_works=True, proof=""
    )
    assert empty["isError"] is True
    proof = "API v1, en-tête absent : erreur 400. En-tête présent : appel réussi."
    good = call_tool(
        auth_client, token, "confirm_gotcha", gotcha_id=gotcha_id, still_works=True, proof=proof
    )
    assert good["structuredContent"]["still_works"] is True
    fiche = await store.get_fiche("mtn-momo", include_drafts=True)
    assert fiche is not None
    gotcha = fiche.find_gotcha(gotcha_id)
    assert gotcha is not None
    assert gotcha.confirmations == 1
    again = call_tool(
        auth_client, token, "confirm_gotcha", gotcha_id=gotcha_id, still_works=True, proof=proof
    )
    assert again["isError"] is True


def test_confirming_an_unknown_gotcha_is_refused(auth_client: TestClient) -> None:
    _, tokens = connect(auth_client)
    result = call_tool(
        auth_client,
        tokens["access_token"],
        "confirm_gotcha",
        gotcha_id="mtn-momo.inconnu",
        still_works=True,
        proof="API v1, appel réussi.",
    )
    assert result["isError"] is True


@pytest.mark.anyio
async def test_usage_is_counted_without_keeping_the_search_text(
    auth_client: TestClient, store: MemoryStore, clock: FixedClock
) -> None:
    _, tokens = connect(auth_client)
    token = tokens["access_token"]
    call_tool(auth_client, token, "get_fiche", service="mtn-momo")
    call_tool(auth_client, token, "search_gotchas", query="X-Target-Environment")
    call_tool(auth_client, token, "search_gotchas", query="rien-de-tel-ici")
    call_tool(auth_client, token, "get_service_status", service="mtn-momo")
    totals = await store.usage_totals(clock.today())
    counted = {total.event.value: (total.count, total.accounts) for total in totals}
    assert counted["read_fiche"] == (1, 1)
    assert counted["search_hit"] == (1, 1)
    assert counted["search_miss"] == (1, 1)
    assert counted["read_status"] == (1, 1)


def test_reading_has_a_quota_per_account(
    auth_client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("app.mcp.server.READ_LIMIT", 1)
    _, tokens = connect(auth_client)
    token = tokens["access_token"]
    # Le quota est lu à chaque appel : le deuxième appel est refusé.
    assert not call_tool(auth_client, token, "list_services").get("isError")
    result = call_tool(auth_client, token, "list_services")
    assert result["isError"] is True
    assert "retry later" in result["content"][0]["text"]


def test_registration_with_a_nul_byte_is_refused_cleanly(auth_client: TestClient) -> None:
    body = {"client_name": "outil\u0000", "redirect_uris": [CALLBACK]}
    response = auth_client.post("/register", json=body)
    assert response.status_code == 400


# --- Consentement et adresses de retour ----------------------------------------------


def test_consent_screen_shows_the_tool_and_where_the_code_goes(auth_client: TestClient) -> None:
    page = auth_client.get(ask_login(auth_client, register(auth_client)))
    assert page.status_code == 200
    assert "outil" in page.text
    assert CALLBACK in page.text


def test_refusing_on_the_consent_screen_goes_back_to_the_tool(auth_client: TestClient) -> None:
    consent = ask_login(auth_client, register(auth_client))
    response = answer_consent(auth_client, consent, "refuser")
    assert response.status_code == 303
    query = parse_qs(urlparse(response.headers["location"]).query)
    assert query == {"error": ["access_denied"], "state": ["etat-outil"]}
    # La demande est effacée : l'écran ne la retrouve plus.
    assert auth_client.get(consent).status_code == 400


def test_a_login_link_sent_to_someone_else_gives_nothing(auth_client: TestClient) -> None:
    """« Confused deputy » : l'attaquant lance la connexion, la victime finit chez GitHub."""
    state = start_login(auth_client, register(auth_client))
    auth_client.cookies.clear()  # un autre navigateur, qui n'a rien accepté
    response = auth_client.get(
        "/github/callback", params={"state": state, "code": "bon"}, follow_redirects=False
    )
    assert response.status_code == 400
    assert "location" not in response.headers


@pytest.mark.parametrize(
    "uri",
    ["http://evil.example/cb", "javascript:alert(1)", "data:text/html,x", "file:///etc/passwd"],
)
def test_dangerous_redirect_uris_are_refused(auth_client: TestClient, uri: str) -> None:
    response = auth_client.post("/register", json={"client_name": "x", "redirect_uris": [uri]})
    assert response.status_code == 400
    assert response.json()["error"] == "invalid_client_metadata"


@pytest.mark.parametrize(
    "uri", ["https://outil.example/cb", "http://127.0.0.1:3000/cb", "cursor://outil/oauth"]
)
def test_usual_redirect_uris_are_accepted(auth_client: TestClient, uri: str) -> None:
    response = auth_client.post("/register", json={"client_name": "x", "redirect_uris": [uri]})
    assert response.status_code == 201, response.text


def test_registration_size_is_bounded(auth_client: TestClient) -> None:
    too_long = {"client_name": "x" * 101, "redirect_uris": [CALLBACK]}
    assert auth_client.post("/register", json=too_long).status_code == 400
    too_many = {"client_name": "x", "redirect_uris": [f"{CALLBACK}/{n}" for n in range(6)]}
    assert auth_client.post("/register", json=too_many).status_code == 400


def test_a_nul_byte_in_the_login_request_is_an_oauth_error(auth_client: TestClient) -> None:
    oauth_client = register(auth_client)
    response = auth_client.get(
        "/authorize",
        params={
            "response_type": "code",
            "client_id": oauth_client["client_id"],
            "redirect_uri": CALLBACK,
            "state": "etat\x00",
            "code_challenge": CHALLENGE,
            "code_challenge_method": "S256",
            "resource": RESOURCE,
        },
        follow_redirects=False,
    )
    assert response.status_code == 302
    assert parse_qs(urlparse(response.headers["location"]).query)["error"] == ["invalid_request"]


@pytest.mark.anyio
async def test_two_simultaneous_renewals_give_invalid_grant(auth_client: TestClient) -> None:
    from mcp.server.auth.provider import TokenError

    from app.mcp.oauth import GotchaOAuthProvider

    oauth_client, tokens = connect(auth_client)
    provider = GotchaOAuthProvider(lambda: auth_client.app.state.services, resource_url=RESOURCE)  # type: ignore[attr-defined]
    client_info = await provider.get_client(oauth_client["client_id"])
    assert client_info is not None
    refresh = await provider.load_refresh_token(client_info, tokens["refresh_token"])
    assert refresh is not None
    # Les deux fenêtres ont chargé le jeton ; la première le consomme.
    await provider.exchange_refresh_token(client_info, refresh, [])
    with pytest.raises(TokenError) as caught:
        await provider.exchange_refresh_token(client_info, refresh, [])
    assert caught.value.error == "invalid_grant"


def test_pages_never_read_bearer_tokens(auth_client: TestClient, store: MemoryStore) -> None:
    async def broken(*_args: object) -> None:
        raise RuntimeError("base en panne")

    store.get_oauth_grant = broken  # type: ignore[method-assign]
    headers = {"Authorization": "Bearer jeton-quelconque"}  # secret-scan: ignore (faux jeton)
    assert auth_client.get("/", headers=headers).status_code == 200
    assert auth_client.get("/static/css/app.css", headers=headers).status_code == 200
