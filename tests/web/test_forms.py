"""Formulaires : CSRF, contribution, confirmation, signalement, relecture, en-têtes de sécurité."""

from __future__ import annotations

from collections.abc import Callable

from starlette.testclient import TestClient

from app.config import Settings
from app.services.clock import FixedClock
from tests.conftest import FakeIdentity, make_client

GOOD_CONTRIBUTION = {
    "kind": "gotcha",
    "fiche_slug": "mtn-momo",
    "title": "Le callback exige une URL en HTTPS",
    "body_md": "Sans HTTPS, aucun callback n'arrive. Solution : exposer une URL https.",
    "pseudo": "dev_test",
    "email": "dev_test@example.com",
    "licence": "oui",
}


def test_post_without_csrf_token_is_refused(client: TestClient) -> None:
    client.get("/contribuer")
    response = client.post("/contribuer", data=GOOD_CONTRIBUTION)
    assert response.status_code == 403


def test_contribution_goes_to_review(client: TestClient, csrf: Callable[[str], str]) -> None:
    response = client.post(
        "/contribuer",
        data={**GOOD_CONTRIBUTION, "csrf_token": csrf("/contribuer")},
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert response.headers["location"] == "/contribuer/merci"
    review = client.get("/relecture").text
    assert "Le callback exige une URL en HTTPS" in review
    assert "dev_test@example.com" not in review  # l'e-mail reste privé


def test_contribution_with_a_secret_is_refused(
    client: TestClient, csrf: Callable[[str], str]
) -> None:
    data = {
        **GOOD_CONTRIBUTION,
        "body_md": "Mon code : Authorization: Bearer " + "abcDEF123456" * 3,
        "csrf_token": csrf("/contribuer"),
    }
    response = client.post("/contribuer", data=data)
    assert response.status_code == 422
    assert "semble contenir un secret" in response.text


def test_contribution_errors_are_shown_in_french(
    client: TestClient, csrf: Callable[[str], str]
) -> None:
    data = {"kind": "gotcha", "fiche_slug": "mtn-momo", "csrf_token": csrf("/contribuer")}
    response = client.post("/contribuer", data=data)
    assert response.status_code == 422
    assert "Le titre doit faire entre 5 et 160 caractères." in response.text
    assert "licence CC BY 4.0" in response.text


def test_confirm_gotcha_increments_counter(client: TestClient, csrf: Callable[[str], str]) -> None:
    token = csrf("/fiches/mtn-momo")
    response = client.post(
        "/fiches/mtn-momo/confirmer",
        data={
            "csrf_token": token,
            "target_kind": "gotcha",
            "target_id": "mtn-momo.x-target-environment",
        },
        follow_redirects=False,
    )
    assert response.status_code == 303
    page = client.get(response.headers["location"]).text
    assert "Votre confirmation est enregistrée" in page
    assert "1 confirmation" in page


def test_confirm_rejects_target_of_another_fiche(
    client: TestClient, csrf: Callable[[str], str]
) -> None:
    response = client.post(
        "/fiches/mtn-momo/confirmer",
        data={
            "csrf_token": csrf("/fiches/mtn-momo"),
            "target_kind": "gotcha",
            "target_id": "wave-sn.pas-de-bac-a-sable",
        },
    )
    assert response.status_code == 400


def test_outage_report_shows_on_the_fiche(client: TestClient, csrf: Callable[[str], str]) -> None:
    assert "badge--degraded" not in client.get("/fiches/orange-money-sn").text
    response = client.post(
        "/pannes/signaler",
        data={
            "csrf_token": csrf("/pannes/signaler"),
            "fiche_slug": "orange-money-sn",
            "description": "Les paiements restent en attente depuis 20 minutes.",
        },
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert "badge--degraded" in client.get(response.headers["location"]).text


def test_review_approves_a_contribution(client: TestClient, csrf: Callable[[str], str]) -> None:
    token = csrf("/relecture")
    response = client.post(
        "/relecture/fictif0000000000000000000000001",
        data={"csrf_token": token, "action": "approve"},
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert "fictif0000000000000000000000001" not in client.get("/relecture").text


def test_security_headers_and_cookie(client: TestClient) -> None:
    response = client.get("/")
    csp = response.headers["content-security-policy"]
    assert "script-src 'self'" in csp
    assert "frame-ancestors 'none'" in csp
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["cross-origin-opener-policy"] == "same-origin"
    assert "HttpOnly" in response.headers["set-cookie"]
    assert "SameSite=Lax" in response.headers["set-cookie"]


def test_production_csrf_cookie_cannot_be_planted_by_a_sibling_subdomain(
    prod_client: TestClient,
) -> None:
    prod_client.base_url = prod_client.base_url.copy_with(scheme="https")
    cookie = prod_client.get("/contribuer").headers["set-cookie"]
    assert cookie.startswith("__Host-gotcha_csrf=")
    assert "; Secure" in cookie
    assert "Domain=" not in cookie

    # Un autre site du même hébergeur pose un cookie sans préfixe et soumet sa valeur.
    planted = "x" * 43
    prod_client.cookies.clear()
    prod_client.cookies.set("gotcha_csrf", planted)
    response = prod_client.post("/contribuer", data={**GOOD_CONTRIBUTION, "csrf_token": planted})
    assert response.status_code == 403


def test_production_form_works_with_the_secure_cookie(clock: FixedClock) -> None:
    settings = Settings(
        env="prod",
        store="memory",
        show_drafts=False,
        load_fixtures=False,
        site_auth=True,
        github_client_id="identifiant",
        github_client_secret="secret",
        jury_code="code",
        site_url="https://gotcha.test",
    )
    with make_client(settings, clock, identity=FakeIdentity()) as client:
        client.base_url = client.base_url.copy_with(scheme="https")
        page = client.get("/connexion").text
        token = page.split('name="csrf_token" value="')[1].split('"')[0]
        form = {"csrf_token": token, "code": "code", "retour": "/"}
        assert client.post("/connexion/jury", data=form, follow_redirects=False).status_code == 303
