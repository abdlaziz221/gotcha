"""Pages d'erreur (L9) : chaque code propose une suite (recherche, réessayer, accueil)."""

from __future__ import annotations

from collections.abc import Callable

from starlette.testclient import TestClient


def test_404_offers_the_search(client: TestClient) -> None:
    response = client.get("/nexiste-pas")
    assert response.status_code == 404
    assert "Page introuvable" in response.text
    assert 'role="search"' in response.text


def test_429_explains_the_limit_and_offers_reading(
    client: TestClient, csrf: Callable[[str], str]
) -> None:
    token = csrf("/pannes/signaler")
    data = {"csrf_token": token, "fiche_slug": "mtn-momo", "description": "Paiements bloqués"}
    codes = [client.post("/pannes/signaler", data=data, follow_redirects=False).status_code]
    while codes[-1] != 429 and len(codes) < 20:
        codes.append(client.post("/pannes/signaler", data=data, follow_redirects=False).status_code)
    response = client.post("/pannes/signaler", data=data, follow_redirects=False)
    assert response.status_code == 429
    assert "Trop de demandes" in response.text
    assert 'href="/recherche">Rechercher un piège' in response.text


def test_500_offers_to_retry(client: TestClient) -> None:
    async def boom() -> None:
        raise RuntimeError("panne simulée pour le test")

    client.app.add_api_route("/test-erreur-500", boom)  # type: ignore[attr-defined]
    response = TestClient(client.app, raise_server_exceptions=False).get("/test-erreur-500?x=1")
    assert response.status_code == 500
    assert "Erreur du serveur" in response.text
    assert 'href="/test-erreur-500?x=1">Réessayer' in response.text
    assert "panne simulée" not in response.text


def test_rejected_forms_still_count_against_the_quota(client: TestClient) -> None:
    # Le quota passe avant le contrôle du jeton : sans jeton valide, le sixième envoi de
    # l'heure est refusé par le quota, et le formulaire n'est même pas lu.
    data = {"csrf_token": "faux", "fiche_slug": "mtn-momo", "description": "Paiements bloqués"}
    codes = [client.post("/pannes/signaler", data=data).status_code for _ in range(6)]
    assert codes == [403] * 5 + [429]
