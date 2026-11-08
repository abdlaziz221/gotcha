"""Page « Brancher votre agent », état par service sur /pannes, fiche des résultats de recherche."""

from __future__ import annotations

from starlette.testclient import TestClient


def test_connect_page_gives_the_mcp_address_and_each_agent(client: TestClient) -> None:
    page = client.get("/brancher").text
    assert "Brancher votre agent" in page
    assert "http://testserver/mcp" in page
    assert "claude mcp add --transport http gotcha http://testserver/mcp" in page
    for name in (
        "Codex",
        "Cursor",
        "VS Code et GitHub Copilot",
        "Windsurf",
        "Antigravity",
        "Gemini CLI",
        "Cline",
        "OpenCode",
        "Grok CLI",
        "Hermes Agent",
    ):
        assert name in page
    assert "grok mcp add --transport http gotcha http://testserver/mcp" in page
    assert "search_gotchas" in page


def test_incidents_page_shows_the_state_of_each_service(client: TestClient) -> None:
    page = client.get("/pannes").text
    assert "État par service" in page
    assert 'href="/fiches/mtn-momo"' in page


def test_search_result_names_its_fiche(client: TestClient) -> None:
    page = client.get("/recherche?q=X-Target-Environment").text
    assert "MTN MoMo" in page
