"""Niveaux de confiance, preuves et dates des sources (D22)."""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any

import pytest
from starlette.testclient import TestClient

from app.domain.models import ConfidenceLevel, Gotcha, Source
from app.stores.content_files import ContentError, load_fiche
from app.web.presenters import gotcha_view, source_view

SOURCE = {"title": "Source", "url": "https://example.com", "accessed_on": date(2026, 11, 1)}


def _gotcha(**changes: Any) -> Gotcha:
    data: dict[str, Any] = {
        "id": "demo.piege",
        "fiche_slug": "demo",
        "title": "Un piège de test",
        "symptom_md": "Symptôme",
        "cause_md": "Cause",
        "fix_md": "Solution",
        "severity": "major",
        "environments": ["sandbox"],
        "sources": [SOURCE],
        "last_confirmed_on": date(2026, 11, 1),
    }
    return Gotcha(**{**data, **changes})


def test_a_gotcha_is_sourced_by_default() -> None:
    assert _gotcha().confidence is ConfidenceLevel.SOURCED


@pytest.mark.parametrize("level", ["reproduced", "production"])
def test_a_tested_gotcha_needs_a_proof(level: str) -> None:
    with pytest.raises(ValueError, match="sans preuve"):
        _gotcha(confidence=level)
    assert _gotcha(confidence=level, proof_md="API v1, résultat obtenu : 400").proof_md


def test_view_shows_level_attempts_and_proof() -> None:
    view = gotcha_view(
        _gotcha(
            confidence="reproduced",
            proof_md="API v1, résultat obtenu : 400",
            failed_attempts_md="Changer de clé n'a rien changé.",
        ),
        {},
        needs_review=False,
    )
    assert view.confidence_label == "Reproduit"
    assert view.proof_html is not None
    assert "résultat obtenu" in view.proof_html
    assert view.failed_attempts_html is not None
    assert "Changer de clé" in view.failed_attempts_html


def test_source_keeps_its_publication_date() -> None:
    source = Source(**SOURCE, published_on=date(2024, 7, 24))
    assert source_view(source).published_on == date(2024, 7, 24)


def _write_fiche(root: Path, body: str, *, meta: str = "") -> Path:
    fiche = root / "demo"
    (fiche / "pieges").mkdir(parents=True)
    (fiche / "fiche.yml").write_text(
        "service: {slug: demo, name: Demo, kind: payment, operator: Demo}\n"
        "title: Demo\nsummary: Demo\nlast_confirmed_on: 2026-11-01\n",
        "utf-8",
    )
    (fiche / "pieges" / "piege.md").write_text(
        "---\ntitle: Un piège de test\nseverity: major\nenvironments: [sandbox]\n"
        f"last_confirmed_on: 2026-11-01\n{meta}"
        "sources:\n  - {title: Source, url: 'https://example.com', accessed_on: 2026-11-01}\n"
        f"---\n\n{body}",
        "utf-8",
    )
    return fiche


def test_optional_sections_are_read(tmp_path: Path) -> None:
    fiche = _write_fiche(
        tmp_path,
        "## Symptôme\n\nS\n\n## Cause\n\nC\n\n## Solution\n\nF\n\n"
        "## Pistes qui ont échoué\n\nA\n\n## Preuve\n\nP\n",
        meta="confidence: reproduced\n",
    )
    gotcha = load_fiche(fiche).gotchas[0]
    assert gotcha.failed_attempts_md == "A"
    assert gotcha.proof_md == "P"
    assert gotcha.confidence is ConfidenceLevel.REPRODUCED


def test_required_sections_stay_required(tmp_path: Path) -> None:
    fiche = _write_fiche(tmp_path, "## Symptôme\n\nS\n\n## Preuve\n\nP\n")
    with pytest.raises(ContentError, match="sections manquantes"):
        load_fiche(fiche)


def test_page_does_not_claim_a_confirmation_nobody_made(client: TestClient) -> None:
    page = client.get("/fiches/mtn-momo").text
    assert "Sourcé" in page
    assert "0 confirmation" in page
    assert "dernière le" not in page
    assert "confirmé le" not in page


def test_page_shows_when_a_source_was_published(client: TestClient) -> None:
    assert "publié le 24 juil. 2024" in client.get("/fiches/mtn-momo").text
