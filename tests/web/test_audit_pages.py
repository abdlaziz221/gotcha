"""Audit L10 : chaque page publique pèse moins de 200 Ko et reste lisible par un lecteur d'écran.

Complète test_page_weight_under_200_kb (accueil et deux fiches) sur toutes les autres pages.
Les contrastes et le focus clavier ont été vérifiés dans le navigateur (voir DESIGN_SYSTEM.md).
"""

from __future__ import annotations

import re
from html.parser import HTMLParser

import pytest
from starlette.testclient import TestClient

MAX_PAGE_BYTES = 200 * 1024
PAGES = [
    "/",
    "/recherche",
    "/recherche?q=callback",
    "/fiches/wave-sn",
    "/fiches/wave-sn?mode=pas-a-pas&etape=1",
    "/pannes",
    "/pannes/signaler",
    "/contribuer",
    "/glossaire",
    "/ou-sont-vos-donnees",
    "/brancher",
    "/nexiste-pas",
]


class _Audit(HTMLParser):
    """Relève la langue, les titres h1, les champs et leurs libellés."""

    def __init__(self) -> None:
        super().__init__()
        self.lang = ""
        self.h1 = 0
        self.fields: list[str] = []
        self.labelled: set[str] = set()
        self.label_depth = 0
        self.wrapped: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        a = dict(attrs)
        if tag == "html":
            self.lang = a.get("lang") or ""
        elif tag == "h1":
            self.h1 += 1
        elif tag == "label":
            self.label_depth += 1
            if a.get("for"):
                self.labelled.add(a["for"] or "")
        elif tag in ("input", "select", "textarea") and a.get("type") != "hidden":
            if a.get("aria-label") or a.get("aria-labelledby"):
                return
            if self.label_depth:
                self.wrapped.append(a.get("id") or tag)
            else:
                self.fields.append(a.get("id") or "")

    def handle_endtag(self, tag: str) -> None:
        if tag == "label" and self.label_depth:
            self.label_depth -= 1


@pytest.mark.parametrize("path", PAGES)
def test_page_weighs_less_than_200_kb(client: TestClient, path: str) -> None:
    page = client.get(path).text
    assets = re.findall(r'(?:href|src)="(/static/[^"]+)"', page)
    total = len(page.encode()) + sum(len(client.get(a).content) for a in set(assets))
    assert total < MAX_PAGE_BYTES, f"{path} pèse {total} octets"


@pytest.mark.parametrize("path", PAGES)
def test_page_is_readable_by_a_screen_reader(client: TestClient, path: str) -> None:
    audit = _Audit()
    audit.feed(client.get(path).text)
    assert audit.lang == "fr"
    assert audit.h1 == 1, f"{path} : {audit.h1} titres h1"
    unlabelled = [f for f in audit.fields if f not in audit.labelled]
    assert not unlabelled, f"{path} : champs sans libellé {unlabelled}"
