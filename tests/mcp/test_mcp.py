"""Serveur MCP, appelé comme le ferait un agent : JSON-RPC sur POST /mcp."""

from __future__ import annotations

from typing import Any

from starlette.testclient import TestClient

HEADERS = {"Accept": "application/json, text/event-stream"}


def call(client: TestClient, method: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    response = client.post(
        "/mcp",
        json={"jsonrpc": "2.0", "id": 1, "method": method, "params": params or {}},
        headers=HEADERS,
    )
    assert response.status_code == 200, response.text
    return response.json()["result"]


def tool(client: TestClient, name: str, **arguments: Any) -> dict[str, Any]:
    return call(client, "tools/call", {"name": name, "arguments": arguments})


def test_tools_are_listed(client: TestClient) -> None:
    names = {t["name"] for t in call(client, "tools/list")["tools"]}
    assert names == {
        "list_services",
        "get_fiche",
        "search_gotchas",
        "get_service_status",
        "report_outage",
    }


def test_get_fiche_gives_gotchas_and_status(client: TestClient) -> None:
    result = tool(client, "get_fiche", service="mtn-momo", country="GH")
    fiche = result["structuredContent"]
    ids = {g["id"] for g in fiche["gotchas"]}
    assert "mtn-momo.x-target-environment" in ids
    gotcha = next(g for g in fiche["gotchas"] if g["id"] == "mtn-momo.x-target-environment")
    assert "[[" not in gotcha["cause"]
    assert gotcha["confidence"] == "sourced"
    assert gotcha["url"].endswith("/fiches/mtn-momo#piege-x-target-environment")
    assert fiche["status"]["status"] in {"normal", "degraded", "down"}
    assert fiche["warning"]  # brouillons : l'agent est prévenu


def test_search_gotchas(client: TestClient) -> None:
    result = tool(client, "search_gotchas", query="X-Target-Environment")
    hits = result["structuredContent"]["result"]
    assert hits[0]["fiche_slug"] == "mtn-momo"


def test_status_reflects_reports(client: TestClient) -> None:
    before = tool(client, "get_service_status", service="orange-money", country="SN")
    assert before["structuredContent"]["status"] == "normal"
    report = tool(
        client,
        "report_outage",
        service="orange-money",
        country="SN",
        description="Paiements bloqués.",
    )
    assert report["structuredContent"]["status"] == "degraded"
    after = tool(client, "get_service_status", service="orange-money", country="SN")
    assert after["structuredContent"]["status"] == "degraded"


def test_unknown_service_is_a_readable_tool_error(client: TestClient) -> None:
    result = tool(client, "get_fiche", service="inconnu")
    assert result["isError"] is True
    assert "Aucune fiche" in result["content"][0]["text"]


def test_outage_reports_are_rate_limited(client: TestClient) -> None:
    for _ in range(10):
        ok = tool(
            client, "report_outage", service="wave", country="SN", description="Paiements lents."
        )
        assert not ok.get("isError")
    limited = tool(
        client, "report_outage", service="wave", country="SN", description="Encore lent."
    )
    assert limited["isError"] is True


def test_contributor_email_is_never_exposed(client: TestClient) -> None:
    result = tool(client, "get_fiche", service="mtn-momo")
    assert "@example.com" not in str(result)
