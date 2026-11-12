"""Connexion sur le site : aperçu public, compte pour le reste (D23)."""

from __future__ import annotations

import html
import re
from collections.abc import Iterator
from dataclasses import replace
from urllib.parse import parse_qs, urlparse

import pytest
from starlette.testclient import TestClient

from app.config import Settings
from app.domain.models import Account, ErrorCode, UsageEvent
from app.domain.text import plain_snippet
from app.services.clock import FixedClock
from app.stores.memory.store import MemoryStore
from tests.conftest import NOW, FakeIdentity, make_client

SITE_SETTINGS = Settings(
    env="test",
    site_auth=True,
    github_client_id="identifiant",
    github_client_secret="secret",
    jury_code="code-du-jury",
)
LOCKED = "mtn-momo"
OPEN = "datacloud-sn"
GOOD_BODY = "Sans HTTPS, aucun callback n'arrive. Solution : exposer une URL https."


@pytest.fixture
def store() -> MemoryStore:
    return MemoryStore.from_directories(SITE_SETTINGS.content_dir, None, now=NOW)


@pytest.fixture
def site(store: MemoryStore, clock: FixedClock) -> Iterator[TestClient]:
    with make_client(SITE_SETTINGS, clock, identity=FakeIdentity(), store=store) as client:
        yield client


def log_in(client: TestClient, retour: str = "/") -> str:
    """Se connecte par le faux GitHub ; renvoie l'adresse de retour."""
    start = client.get("/connexion/github", params={"retour": retour}, follow_redirects=False)
    assert start.status_code == 302
    state = parse_qs(urlparse(start.headers["location"]).query)["state"][0]
    back = client.get(
        "/github/callback", params={"state": state, "code": "bon"}, follow_redirects=False
    )
    assert back.status_code == 302
    return back.headers["location"]


def csrf_token(client: TestClient, path: str) -> str:
    match = re.search(r'name="csrf_token" value="([^"]+)"', client.get(path).text)
    assert match, f"aucun jeton CSRF sur {path}"
    return match.group(1)


async def _fiche(store: MemoryStore, slug: str):  # noqa: ANN202
    fiche = await store.get_fiche(slug, include_drafts=True)
    assert fiche is not None
    return fiche


@pytest.mark.anyio
async def test_preview_sends_neither_solutions_nor_steps(
    site: TestClient, store: MemoryStore
) -> None:
    fiche = await _fiche(store, LOCKED)
    page = site.get(f"/fiches/{LOCKED}").text
    assert "Aperçu public" in page
    assert "connexion avec GitHub" in page
    for gotcha in fiche.gotchas:
        assert gotcha.title.split("'")[0] in page
        assert plain_snippet(gotcha.fix_md, 40).rstrip("…") not in page
    for step in fiche.steps:
        assert step.title not in page
    assert "Suivre pas à pas" not in page
    assert "Bac à sable et production" not in page
    assert "Sourcé" in page


def test_preview_cannot_be_bypassed_with_step_mode(site: TestClient) -> None:
    page = site.get(f"/fiches/{LOCKED}", params={"mode": "pas-a-pas", "etape": 1}).text
    assert "Étape 1 sur" not in page


def test_preview_does_not_address_agents(site: TestClient) -> None:
    page = site.get(f"/fiches/{LOCKED}").text.lower()
    assert "agent, " not in page
    assert "dis à ton" not in page


@pytest.mark.anyio
async def test_open_fiche_is_readable_without_an_account(
    site: TestClient, store: MemoryStore
) -> None:
    fiche = await _fiche(store, OPEN)
    page = html.unescape(site.get(f"/fiches/{OPEN}").text)
    assert "Aperçu public" not in page
    assert fiche.steps[0].title in page


@pytest.mark.anyio
async def test_member_reads_everything(site: TestClient, store: MemoryStore) -> None:
    fiche = await _fiche(store, LOCKED)
    assert log_in(site, f"/fiches/{LOCKED}") == f"/fiches/{LOCKED}"
    response = site.get(f"/fiches/{LOCKED}")
    assert "Aperçu public" not in response.text
    assert fiche.steps[0].title in html.unescape(response.text)
    assert "Se déconnecter (aminata)" in response.text
    assert response.headers["cache-control"] == "private, no-store"


def test_session_cookie_is_protected(site: TestClient) -> None:
    start = site.get("/connexion/github", follow_redirects=False)
    state = parse_qs(urlparse(start.headers["location"]).query)["state"][0]
    back = site.get(
        "/github/callback", params={"state": state, "code": "bon"}, follow_redirects=False
    )
    cookie = back.headers["set-cookie"]
    assert cookie.startswith("gotcha_session=")
    assert "HttpOnly" in cookie
    assert "SameSite=lax" in cookie
    assert "Max-Age=2592000" in cookie


def test_production_session_cookie_is_host_only(clock: FixedClock, store: MemoryStore) -> None:
    settings = Settings(
        env="prod",
        store="memory",
        show_drafts=False,
        load_fixtures=False,
        site_auth=True,
        github_client_id="identifiant",
        github_client_secret="secret",
        jury_code="code-du-jury",
        site_url="https://gotcha.test",
    )
    with make_client(settings, clock, identity=FakeIdentity(), store=store) as client:
        client.base_url = client.base_url.copy_with(scheme="https")
        token = csrf_token(client, "/connexion")
        response = client.post(
            "/connexion/jury",
            data={"csrf_token": token, "code": "code-du-jury", "retour": "/"},
            follow_redirects=False,
        )
        cookie = response.headers["set-cookie"]
        assert cookie.startswith("__Host-gotcha_session=")
        assert "Secure" in cookie


@pytest.mark.parametrize("path", ["/contribuer?fiche=mtn-momo", "/pannes/signaler"])
def test_forms_ask_visitors_to_log_in(site: TestClient, path: str) -> None:
    response = site.get(path, follow_redirects=False)
    assert response.status_code == 303
    location = urlparse(response.headers["location"])
    assert location.path == "/connexion"
    assert parse_qs(location.query)["retour"] == [path]


def test_anonymous_post_is_refused(site: TestClient) -> None:
    token = csrf_token(site, "/connexion")
    response = site.post(
        f"/fiches/{LOCKED}/confirmer",
        data={"csrf_token": token, "target_kind": "fiche", "target_id": LOCKED, "proof": "API v1"},
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert response.headers["location"].startswith("/connexion")


@pytest.mark.anyio
async def test_contribution_uses_the_account(site: TestClient, store: MemoryStore) -> None:
    log_in(site)
    page = site.get("/contribuer").text
    assert 'name="pseudo"' not in page
    assert 'name="email"' not in page
    assert "aminata" in page
    response = site.post(
        "/contribuer",
        data={
            "csrf_token": csrf_token(site, "/contribuer"),
            "kind": "gotcha",
            "fiche_slug": LOCKED,
            "title": "Le callback exige une URL en HTTPS",
            "body_md": GOOD_BODY,
            "licence": "oui",
            # Un visiteur ne choisit pas l'identité sous laquelle il publie.
            "pseudo": "usurpateur",
            "email": "usurpateur@example.com",
        },
        follow_redirects=False,
    )
    assert response.status_code == 303, response.text
    saved = (await store.list_contributions())[-1]
    assert saved.pseudo == "aminata"
    assert saved.account_id == "github:42"
    assert saved.email is None


@pytest.mark.anyio
async def test_confirmation_needs_a_proof_and_counts_once(
    site: TestClient, store: MemoryStore
) -> None:
    log_in(site)
    target = {"target_kind": "fiche", "target_id": LOCKED}
    token = csrf_token(site, f"/fiches/{LOCKED}")
    url = f"/fiches/{LOCKED}/confirmer"

    missing = site.post(url, data={"csrf_token": token, **target})
    assert missing.status_code == 400
    assert "preuve" in missing.text

    form = {"csrf_token": token, **target, "proof": "API v1, appel réussi le 4 novembre."}
    assert site.post(url, data=form, follow_redirects=False).status_code == 303
    saved = (await store.list_confirmations())[0]
    assert saved.proof == form["proof"]
    assert saved.account_id == "github:42"
    assert (await _fiche(store, LOCKED)).confirmations == 1

    again = site.post(url, data=form)
    assert again.status_code == 400
    assert "déjà donné cette réponse" in again.text
    assert (await _fiche(store, LOCKED)).confirmations == 1

    # « Ça ne marche plus » reste possible juste après « ça marche » : c'est l'information
    # la plus utile pour la relecture.
    broken = {**form, "still_works": "0", "proof": "API v1, refusé le 10 novembre."}
    assert site.post(url, data=broken, follow_redirects=False).status_code == 303
    assert any(not c.still_works for c in await store.list_confirmations())


def test_secret_in_a_proof_is_refused(site: TestClient) -> None:
    log_in(site)
    response = site.post(
        f"/fiches/{LOCKED}/confirmer",
        data={
            "csrf_token": csrf_token(site, f"/fiches/{LOCKED}"),
            "target_kind": "fiche",
            "target_id": LOCKED,
            "proof": "Ma clé : -----BEGIN " + "PRIVATE KEY-----",
        },
    )
    assert response.status_code >= 400


@pytest.mark.anyio
async def test_outage_is_reported_under_the_account(site: TestClient, store: MemoryStore) -> None:
    log_in(site)
    token = csrf_token(site, "/pannes/signaler")
    response = site.post(
        "/pannes/signaler",
        data={
            "csrf_token": token,
            "fiche_slug": "wave-sn",
            "description": "Les paiements échouent depuis une heure.",
            "pseudo": "usurpateur",
        },
        follow_redirects=False,
    )
    assert response.status_code == 303, response.text
    # L'identifiant stable du compte, comme par le serveur MCP : ni le pseudo saisi, ni le
    # pseudo GitHub, qui change si le compte est renommé.
    assert (await store.list_incidents(service_slug="wave"))[0].reported_by == "github:42"


def test_jury_code(site: TestClient) -> None:
    token = csrf_token(site, "/connexion")
    wrong = site.post("/connexion/jury", data={"csrf_token": token, "code": "faux", "retour": "/"})
    assert wrong.status_code == 422
    assert "Code incorrect" in wrong.text
    assert "gotcha_session" not in site.cookies

    right = site.post(
        "/connexion/jury",
        data={"csrf_token": token, "code": "code-du-jury", "retour": f"/fiches/{LOCKED}"},
        follow_redirects=False,
    )
    assert right.headers["location"] == f"/fiches/{LOCKED}"
    assert "Aperçu public" not in site.get(f"/fiches/{LOCKED}").text


def test_jury_form_is_hidden_without_a_code(store: MemoryStore, clock: FixedClock) -> None:
    settings = Settings(
        env="test", site_auth=True, github_client_id="identifiant", github_client_secret="secret"
    )
    with make_client(settings, clock, identity=FakeIdentity(), store=store) as client:
        assert "Accès du jury" not in client.get("/connexion").text
        token = client.cookies["gotcha_csrf"]
        response = client.post("/connexion/jury", data={"csrf_token": token, "code": ""})
        assert response.status_code == 404


@pytest.mark.parametrize(
    "retour",
    ["https://ailleurs.example", "//ailleurs.example", "/\\ailleurs.example", "javascript:x"],
)
def test_login_cannot_redirect_elsewhere(site: TestClient, retour: str) -> None:
    assert log_in(site, retour) == "/"


def test_logout_ends_the_session(site: TestClient) -> None:
    log_in(site)
    token = csrf_token(site, "/")
    assert (
        site.post("/deconnexion", data={"csrf_token": token}, follow_redirects=False).status_code
        == 303
    )
    assert "Aperçu public" in site.get(f"/fiches/{LOCKED}").text


@pytest.mark.anyio
async def test_stolen_session_stops_working_after_logout(site: TestClient) -> None:
    log_in(site)
    stolen = dict(site.cookies)
    site.post("/deconnexion", data={"csrf_token": csrf_token(site, "/")}, follow_redirects=False)
    for name, value in stolen.items():
        site.cookies.set(name, value)
    assert "Aperçu public" in site.get(f"/fiches/{LOCKED}").text


@pytest.mark.anyio
async def test_blocked_account_loses_access(site: TestClient, store: MemoryStore) -> None:
    log_in(site)
    await store.save_account(
        Account(id="github:42", pseudo="aminata", created_at=NOW, last_login_at=NOW, blocked=True)
    )
    assert "Aperçu public" in site.get(f"/fiches/{LOCKED}").text
    assert log_in(site).startswith("/connexion?erreur=bloque")


def test_refused_login_comes_back_to_the_login_page(site: TestClient) -> None:
    start = site.get("/connexion/github", params={"retour": "/pannes"}, follow_redirects=False)
    state = parse_qs(urlparse(start.headers["location"]).query)["state"][0]
    back = site.get(
        "/github/callback",
        params={"state": state, "error": "access_denied"},
        follow_redirects=False,
    )
    assert back.headers["location"] == "/connexion?erreur=refus&retour=%2Fpannes"
    assert "n'a pas abouti" in html.unescape(site.get(back.headers["location"]).text)


def test_github_failure_comes_back_to_the_login_page(site: TestClient) -> None:
    start = site.get("/connexion/github", follow_redirects=False)
    state = parse_qs(urlparse(start.headers["location"]).query)["state"][0]
    back = site.get(
        "/github/callback", params={"state": state, "code": "mauvais"}, follow_redirects=False
    )
    assert back.headers["location"].startswith("/connexion?erreur=refus")


@pytest.mark.anyio
async def test_search_keeps_error_advice_for_members(site: TestClient, store: MemoryStore) -> None:
    fiche = await _fiche(store, LOCKED)
    error = ErrorCode(code="E999", meaning="Refus", action="Renouveler le jeton secret")
    await store.upsert_fiche(fiche.model_copy(update={"error_codes": [error]}))
    assert error.action not in site.get("/recherche", params={"q": "E999"}).text
    log_in(site)
    assert error.action in site.get("/recherche", params={"q": "E999"}).text


def test_login_page_only_exists_with_the_connection(client: TestClient) -> None:
    assert client.get("/connexion").status_code == 404
    assert client.get("/connexion/github").status_code == 404
    assert "Se connecter" not in client.get("/").text


def test_production_without_connection_reads_freely_and_writes_nothing(
    prod_client: TestClient,
) -> None:
    page = prod_client.get("/").text
    assert 'href="/contribuer"' not in page
    assert "Se connecter" not in page
    assert prod_client.get("/contribuer").status_code == 403
    assert prod_client.get("/pannes/signaler").status_code == 403
    assert 'href="/pannes/signaler"' not in prod_client.get("/pannes").text


def test_data_page_explains_the_connection(site: TestClient) -> None:
    page = site.get("/ou-sont-vos-donnees").text
    assert "GitHub" in page
    assert "Pas de compte" not in page


def test_a_login_link_sent_to_a_victim_connects_nobody(site: TestClient) -> None:
    """CSRF de connexion : l'attaquant lance la connexion, la victime finit le retour."""
    start = site.get("/connexion/github", follow_redirects=False)
    state = parse_qs(urlparse(start.headers["location"]).query)["state"][0]
    site.cookies.clear()  # le navigateur de la victime n'a pas lancé cette connexion
    back = site.get(
        "/github/callback", params={"state": state, "code": "bon"}, follow_redirects=False
    )
    assert back.status_code == 400
    assert "gotcha_session" not in back.headers.get("set-cookie", "")


def test_a_jury_code_with_an_accent_is_compared_safely(
    store: MemoryStore, clock: FixedClock
) -> None:
    settings = replace(SITE_SETTINGS, jury_code="Téranga-2026")
    with make_client(settings, clock, identity=FakeIdentity(), store=store) as client:
        token = csrf_token(client, "/connexion")
        wrong = client.post(
            "/connexion/jury", data={"csrf_token": token, "code": "Téranga", "retour": "/"}
        )
        assert wrong.status_code == 422
        right = client.post(
            "/connexion/jury",
            data={"csrf_token": token, "code": "Téranga-2026", "retour": "/"},
            follow_redirects=False,
        )
        assert right.status_code == 303


def test_an_expired_session_on_a_form_comes_back_to_its_page(site: TestClient) -> None:
    token = csrf_token(site, "/connexion")
    form = {"csrf_token": token, "target_kind": "fiche", "target_id": LOCKED, "proof": "API v1"}
    sent_from = f"http://testserver/fiches/{LOCKED}?mode=pas-a-pas"
    response = site.post(
        f"/fiches/{LOCKED}/confirmer",
        data=form,
        headers={"Referer": sent_from},
        follow_redirects=False,
    )
    retour = parse_qs(urlparse(response.headers["location"]).query)["retour"]
    assert retour == [f"/fiches/{LOCKED}?mode=pas-a-pas"]
    # Sans Referer : la page parente, jamais l'adresse du POST (405 au retour).
    response = site.post(f"/fiches/{LOCKED}/confirmer", data=form, follow_redirects=False)
    assert parse_qs(urlparse(response.headers["location"]).query)["retour"] == [f"/fiches/{LOCKED}"]


def test_pages_that_depend_on_the_visitor_are_never_cached(site: TestClient) -> None:
    for path in ("/", "/recherche?q=jeton", f"/fiches/{LOCKED}"):
        response = site.get(path)
        assert response.headers["cache-control"] == "private, no-store"
        assert "Cookie" in response.headers["vary"]


@pytest.mark.anyio
async def test_a_failing_usage_counter_never_breaks_a_contribution(
    site: TestClient, store: MemoryStore
) -> None:
    async def broken(*_args: object) -> None:
        raise RuntimeError("base en panne")

    store.add_usage = broken  # type: ignore[method-assign]
    log_in(site)
    response = site.post(
        "/contribuer",
        data={
            "csrf_token": csrf_token(site, "/contribuer"),
            "kind": "gotcha",
            "fiche_slug": LOCKED,
            "title": "Le callback exige une URL en HTTPS",
            "body_md": GOOD_BODY,
            "licence": "oui",
        },
        follow_redirects=False,
    )
    assert response.status_code == 303, response.text
    assert len(await store.list_contributions()) >= 1


# --- A18 : fiches ouvertes sans compte (D27), consultations anonymisées -----------------


async def _open_reads(store: MemoryStore) -> int:
    totals = {t.event: t.count for t in await store.usage_totals(NOW.date())}
    return totals.get(UsageEvent.READ_OPEN_FICHE, 0)


@pytest.mark.anyio
async def test_the_wave_fiche_is_open_without_an_account(site: TestClient) -> None:
    page = site.get("/fiches/wave-sn")
    assert page.status_code == 200
    assert "Aperçu public" not in page.text  # la fiche entière, pas l'aperçu
    assert "Aperçu public" in site.get(f"/fiches/{LOCKED}").text


@pytest.mark.anyio
async def test_anonymous_reads_of_open_fiches_are_counted_once_a_day(
    site: TestClient, store: MemoryStore
) -> None:
    for _ in range(3):  # recharger la page ne compte qu'une fois
        assert site.get("/fiches/wave-sn").status_code == 200
    assert await _open_reads(store) == 1
    site.get("/fiches/wave-sn", headers={"X-Forwarded-For": "203.0.113.9"})
    site.get(f"/fiches/{OPEN}")  # autre fiche ouverte, même visiteur : comptée à part
    assert await _open_reads(store) == 2
    site.get(f"/fiches/{LOCKED}")  # fiche en aperçu : pas comptée ici
    assert await _open_reads(store) == 2


@pytest.mark.anyio
async def test_a_member_reading_an_open_fiche_is_not_counted_as_anonymous(
    site: TestClient, store: MemoryStore
) -> None:
    log_in(site)
    site.get("/fiches/wave-sn")
    assert await _open_reads(store) == 0
    totals = {t.event: t for t in await store.usage_totals(NOW.date())}
    assert totals[UsageEvent.READ_FICHE].accounts == 1


@pytest.mark.anyio
async def test_nothing_about_the_anonymous_reader_is_stored(
    site: TestClient, store: MemoryStore
) -> None:
    site.get("/fiches/wave-sn", headers={"X-Forwarded-For": "203.0.113.9"})
    stored = repr(vars(store))  # tout ce que le stockage garde réellement
    assert "203.0.113.9" not in stored
    assert "testclient" not in stored
