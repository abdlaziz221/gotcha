"""Règles du modèle de données, de la fraîcheur et du calcul d'état."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

import pytest
from pydantic import ValidationError

from app.domain.models import Gotcha, Incident, IncidentSource, Publication, Source, Status
from app.domain.text import plain_snippet, strip_term_links
from app.services.freshness import needs_review
from app.services.status import (
    CONFIRMATION_WINDOW,
    CONFIRMING_REPORTERS,
    REPORT_TTL,
    compute_status,
)

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


def _report(
    reported_by: str | None, *, age: timedelta = timedelta(0), **changes: object
) -> Incident:
    return _incident(
        id=f"community:{reported_by}:{age}:{changes}",
        source=IncidentSource.COMMUNITY,
        status=Status.DEGRADED,
        reported_by=reported_by,
        started_at=NOW - age,
        **changes,
    )


def test_report_still_counts_at_exactly_the_ttl() -> None:
    assert compute_status("wave", "SN", [_report("awa", age=REPORT_TTL)], NOW).status is (
        Status.DEGRADED
    )


def test_imported_incident_does_not_expire() -> None:
    old = _incident(
        source=IncidentSource.FLUTTERWAVE,
        status=Status.DOWN,
        started_at=NOW - timedelta(days=3),
    )
    assert compute_status("wave", "SN", [old], NOW).status is Status.DOWN


def test_new_report_keeps_the_service_degraded_after_the_first_expires() -> None:
    reports = [_report("awa", age=REPORT_TTL + timedelta(hours=1)), _report("awa")]
    status = compute_status("wave", "SN", reports, NOW)
    assert status.status is Status.DEGRADED
    assert status.since == NOW
    assert len(status.active_incidents) == 1


def test_several_people_make_the_service_down() -> None:
    names = [f"dev{n}" for n in range(CONFIRMING_REPORTERS)]
    assert compute_status("wave", "SN", [_report(n) for n in names], NOW).status is Status.DOWN
    below = [_report(n) for n in names[:-1]]
    assert compute_status("wave", "SN", below, NOW).status is Status.DEGRADED


@pytest.mark.parametrize(
    "reporters",
    [
        ["awa"] * 10,
        ["Awa", "awa", " AWA "],
        [None] * 10,
        [None, ""],
    ],
)
def test_one_person_or_anonymous_reports_cannot_make_the_service_down(
    reporters: list[str | None],
) -> None:
    reports = [_report(name, age=timedelta(minutes=i)) for i, name in enumerate(reporters)]
    assert compute_status("wave", "SN", reports, NOW).status is Status.DEGRADED


def test_anonymous_reports_count_as_one_person() -> None:
    reports = [
        _report(None),
        _report(None, age=timedelta(minutes=1)),
        _report("awa"),
        _report("bo"),
    ]
    assert compute_status("wave", "SN", reports, NOW).status is Status.DOWN


def test_old_reports_do_not_confirm_the_outage() -> None:
    late = CONFIRMATION_WINDOW + timedelta(minutes=1)
    reports = [_report("awa"), _report("bo"), _report("cheikh", age=late)]
    assert compute_status("wave", "SN", reports, NOW).status is Status.DEGRADED


def test_reports_from_other_countries_or_resolved_do_not_confirm_the_outage() -> None:
    reports = [
        _report("awa"),
        _report("bo"),
        _report("cheikh", country="CI"),
        _report("diane", resolved_at=NOW),
    ]
    assert compute_status("wave", "SN", reports, NOW).status is Status.DEGRADED


def test_glossary_syntax_is_removed_from_plain_text() -> None:
    assert (
        strip_term_links("Le [[jeton-acces|jeton]] et le [[webhook]]") == "Le jeton et le webhook"
    )
    assert plain_snippet("Appel `requesttopay` **refusé**") == "Appel requesttopay refusé"
    assert plain_snippet("x" * 300, length=10).endswith("…")
