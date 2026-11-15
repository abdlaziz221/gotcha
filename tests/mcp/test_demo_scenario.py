"""Scénario de la démo du jury (docs/DEMO.md), rejoué sans agent.

L'agent ne répond jamais deux fois pareil ; ce test vérifie ce dont la démo dépend
vraiment, avec la configuration de production (brouillons masqués) : ce que Gotcha
répond à chaque étape. S'il échoue, la démo échouera aussi.
"""

from __future__ import annotations

from starlette.testclient import TestClient

from tests.mcp.test_mcp import tool


def test_1_wave_has_no_sandbox_and_says_why(prod_client: TestClient) -> None:
    """1:00 : l'agent consulte Gotcha avant d'écrire la configuration Wave."""
    fiche = tool(prod_client, "get_fiche", service="wave", country="SN")["structuredContent"]
    trap = next(g for g in fiche["gotchas"] if g["id"] == "wave-sn.pas-de-bac-a-sable")
    assert "bac à sable" in trap["title"].lower()
    assert trap["confidence"] == "sourced"
    assert any("https://docs.wave.com/" in s for s in trap["sources"])
    assert trap["url"] == "https://gotcha.test/fiches/wave-sn#piege-pas-de-bac-a-sable"
    assert fiche["warning"] is None  # tout est relu : rien à « vérifier deux fois »


def test_1_search_finds_the_wave_trap(prod_client: TestClient) -> None:
    """Un agent qui cherche au lieu de demander la fiche tombe sur le même piège."""
    hits = tool(prod_client, "search_gotchas", query="Wave bac à sable")["structuredContent"]
    urls = {h["url"] for h in hits["result"]}
    assert "https://gotcha.test/fiches/wave-sn#piege-pas-de-bac-a-sable" in urls


def test_1_wave_page_is_open_without_account(prod_client: TestClient) -> None:
    """Le juré peut ouvrir le lien cité par l'agent sans se connecter (D27)."""
    page = prod_client.get("/fiches/wave-sn")
    assert page.status_code == 200
    assert "Aucun bac à sable public" in page.text
    assert prod_client.get("/fiches/wave-sn?mode=pas-a-pas&etape=1").status_code == 200


def test_spare_mpesa_trap_confirms_by_status_query(prod_client: TestClient) -> None:
    """Piège de rechange : M-Pesa, ne pas livrer sur le seul callback."""
    fiche = tool(prod_client, "get_fiche", service="mpesa", country="KE")["structuredContent"]
    trap = next(g for g in fiche["gotchas"] if g["id"] == "mpesa-ke.callbacks-a-verifier")
    assert "stkpushquery" in trap["fix"]


def test_2_live_outage_reaches_the_agent(client: TestClient) -> None:
    """2:10 : une panne signalée fait passer la fiche en « dégradé » pour l'agent suivant.

    En production, report_outage demande la connexion GitHub ; ici, la configuration de
    développement l'ouvre sans compte, avec le même code de signalement.
    """
    before = tool(client, "get_fiche", service="orange-money", country="SN")
    assert before["structuredContent"]["status"]["status"] == "normal"
    report = tool(
        client,
        "report_outage",
        service="orange-money",
        country="SN",
        description="Les paiements restent en attente depuis 10 minutes.",
    )
    assert report["structuredContent"]["status"] == "degraded"
    after = tool(client, "get_fiche", service="orange-money", country="SN")
    assert after["structuredContent"]["status"]["status"] == "degraded"
