"""Pages du site : toutes répondent, aucun lien mort, pages légères, mode production sûr."""

from __future__ import annotations

import html
import re
from collections import deque

import pytest
from starlette.testclient import TestClient

PAGES = [
    "/",
    "/recherche",
    "/recherche?q=jeton",
    "/fiches/mtn-momo",
    "/fiches/mtn-momo?mode=pas-a-pas&etape=2",
    "/contribuer",
    "/contribuer/merci",
    "/pannes",
    "/pannes/signaler",
    "/relecture",
    "/glossaire",
    "/ou-sont-vos-donnees",
    "/styleguide",
]

MAX_PAGE_BYTES = 200 * 1024  # exigence : pages de moins de 200 Ko


@pytest.mark.parametrize("path", PAGES)
def test_page_answers_and_shows_hosting(client: TestClient, path: str) -> None:
    response = client.get(path)
    assert response.status_code == 200
    assert "Hébergé à Dakar sur Datacloud" in response.text


def test_no_dead_internal_link(client: TestClient) -> None:
    """« Aucun bouton mort » : chaque lien interne trouvé depuis l'accueil répond 200."""
    seen: set[str] = set()
    queue = deque(["/"])
    while queue and len(seen) < 200:
        path = queue.popleft()
        if path in seen:
            continue
        seen.add(path)
        response = client.get(path)
        assert response.status_code == 200, f"{path} répond {response.status_code}"
        if "text/html" not in response.headers.get("content-type", ""):
            continue
        for href in re.findall(r'(?:href|src)="(/[^"]*)"', response.text):
            target = html.unescape(href).split("#", 1)[0]
            if target and target not in seen:
                queue.append(target)
    assert len(seen) > 10


@pytest.mark.parametrize("path", ["/", "/fiches/mtn-momo", "/fiches/mpesa-ke"])
def test_page_weight_under_200_kb(client: TestClient, path: str) -> None:
    page = client.get(path).text
    assets = re.findall(r'(?:href|src)="(/static/[^"]+)"', page)
    total = len(page.encode()) + sum(len(client.get(a).content) for a in set(assets))
    assert total < MAX_PAGE_BYTES, f"{path} pèse {total} octets"


def test_unknown_fiche_is_a_friendly_404(client: TestClient) -> None:
    response = client.get("/fiches/inconnue")
    assert response.status_code == 404
    assert "Page introuvable" in response.text
    assert client.get("/fiches/%00").status_code == 404


def test_step_by_step_mode(client: TestClient) -> None:
    page = client.get("/fiches/mtn-momo?mode=pas-a-pas&etape=2").text
    assert "Étape 2 sur" in page
    assert "Étape précédente" in page


def test_search_finds_the_demo_gotcha(client: TestClient) -> None:
    page = client.get("/recherche?q=X-Target-Environment").text
    assert "/fiches/mtn-momo#piege-x-target-environment" in page
    assert client.get("/recherche?q=%00").status_code == 200
    assert client.get("/recherche?q=jeton%00&service=%00&pays=%00").status_code == 200


def test_production_hides_drafts_and_dev_pages(prod_client: TestClient) -> None:
    home = prod_client.get("/")
    assert home.status_code == 200
    assert "Brouillon" not in home.text
    assert prod_client.get("/fiches/mtn-momo").status_code == 404
    assert prod_client.get("/styleguide").status_code == 404
    assert prod_client.get("/relecture").status_code == 404


def test_healthz(client: TestClient) -> None:
    assert client.get("/healthz").json()["status"] == "ok"
