"""Règles du modèle de données, de la fraîcheur et du calcul d'état."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

import pytest
from pydantic import ValidationError

from app.domain.models import Gotcha, Incident, IncidentSource, Publication, Source, Status
from app.domain.text import plain_snippet, strip_term_links
from app.services.freshness import needs_review
from app.services.status import REPORT_TTL, compute_status

NOW = datetime(2026, 11, 2, 12, 0, tzinfo=UTC)


def _gotcha(**changes: object) -> Gotcha:
    data: dict[str, object] = {
        "id": "demo.piege",
        "fiche_slug": "demo",
        "title": "Un piège",
        "symptom_md": "s",
        "cause_md": "c",
        "fix_md": "f",
        "severity": "major",
        "environments": ["sandbox"],
        "sources": [{"title": "Forum", "url": "https://example.com", "accessed_on": "2026-10-28"}],
        "last_confirmed_on": "2026-10-28",
    }
    data.update(changes)
    return Gotcha.model_validate(data)


def _incident(**changes: object) -> Incident:
    data: dict[str, object] = {
        "id": "i1",
        "source": IncidentSource.FLUTTERWAVE,
        "service_slug": "wave",
        "country": "SN",
        "status": Status.DEGRADED,
        "title": "Panne",
        "started_at": NOW - timedelta(hours=1),
    }
    data.update(changes)
    return Incident.model_validate(data)


def test_published_gotcha_requires_a_verifier() -> None:
    with pytest.raises(ValidationError, match="verified_by"):
        _gotcha(publication=Publication.PUBLISHED)
    assert _gotcha(publication=Publication.PUBLISHED, verified_by="loum").verified_by == "loum"


def test_gotcha_id_must_start_with_its_fiche() -> None:
    with pytest.raises(ValidationError):
        _gotcha(id="autre.piege")


def test_source_needs_url_or_author() -> None:
    with pytest.raises(ValidationError):
        Source(title="Sans rien", accessed_on=date(2026, 10, 1))
    assert Source(title="Terrain", author="khalifa", accessed_on=date(2026, 10, 1))


def test_needs_review_after_90_days() -> None:
    today = date(2026, 11, 2)
    assert not needs_review(today - timedelta(days=90), today)
    assert needs_review(today - timedelta(days=91), today)


def test_status_normal_without_incident() -> None:
    assert compute_status("wave", "SN", [], NOW).status is Status.NORMAL


def test_status_takes_the_worst_active_incident() -> None:
    incidents = [_incident(), _incident(id="i2", status=Status.DOWN)]
    status = compute_status("wave", "SN", incidents, NOW)
    assert status.status is Status.DOWN
    assert len(status.active_incidents) == 2


def test_status_ignores_resolved_other_country_and_other_service() -> None:
    incidents = [
        _incident(resolved_at=NOW - timedelta(minutes=5)),
        _incident(id="i2", country="CI"),
        _incident(id="i3", service_slug="orange-money"),
    ]
    assert compute_status("wave", "SN", incidents, NOW).status is Status.NORMAL


def test_unattributed_incident_hits_payment_services_of_the_country() -> None:
    incidents = [_incident(service_slug=None)]
    assert compute_status("wave", "SN", incidents, NOW).status is Status.DEGRADED
    assert (
        compute_status("datacloud", "SN", incidents, NOW, is_payment=False).status is Status.NORMAL
    )


def test_community_reports_expire() -> None:
    old = _incident(
        source=IncidentSource.COMMUNITY, started_at=NOW - REPORT_TTL - timedelta(minutes=1)
    )
    assert compute_status("wave", "SN", [old], NOW).status is Status.NORMAL


def test_glossary_syntax_is_removed_from_plain_text() -> None:
    assert (
        strip_term_links("Le [[jeton-acces|jeton]] et le [[webhook]]") == "Le jeton et le webhook"
    )
    assert plain_snippet("Appel `requesttopay` **refusé**") == "Appel requesttopay refusé"
    assert plain_snippet("x" * 300, length=10).endswith("…")
