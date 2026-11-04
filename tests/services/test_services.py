"""Services métier sur le stockage mémoire et le contenu de test."""

from __future__ import annotations

from datetime import timedelta

import pytest

from app.config import Settings
from app.container import Services, build_services
from app.domain.errors import InvalidInputError, NotFoundError, SecretDetectedError
from app.domain.models import (
    ContributionInput,
    ContributionStatus,
    Incident,
    IncidentSource,
    OutageReport,
    Status,
    TargetKind,
)
from app.services.clock import FixedClock
from app.stores.content_files import load_fiches, load_glossary
from app.stores.memory.store import MemoryStore
from tests.conftest import NOW, TEST_CONTENT_DIR

pytestmark = pytest.mark.anyio


class FakeFeed:
    source = IncidentSource.FLUTTERWAVE

    def __init__(self, incidents: list[Incident] | None = None, fail: bool = False) -> None:
        self.incidents = incidents or []
        self.fail = fail
        self.calls = 0

    async def fetch(self) -> list[Incident]:
        self.calls += 1
        if self.fail:
            raise ConnectionError("flux injoignable")
        return self.incidents


async def _services(feed: FakeFeed | None = None, clock: FixedClock | None = None) -> Services:
    store = MemoryStore(load_fiches(TEST_CONTENT_DIR), load_glossary(TEST_CONTENT_DIR))
    return await build_services(
        Settings(env="test"),
        clock=clock or FixedClock(NOW),
        store=store,
        feeds=[feed or FakeFeed()],
    )


def _input(**changes: object) -> ContributionInput:
    data: dict[str, object] = {
        "kind": "gotcha",
        "fiche_slug": "demo-pay-sn",
        "title": "Un nouveau piège",
        "body_md": "Le callback arrive deux fois quand on répond lentement.",
        "pseudo": "dev",
        "email": "dev@example.com",
    }
    data.update(changes)
    return ContributionInput.model_validate(data)


async def test_find_falls_back_to_the_fiche_valid_everywhere() -> None:
    services = await _services()
    assert (await services.fiches.find("demo-pay", "sn")).slug == "demo-pay-sn"
    assert (await services.fiches.find("demo-host", "CI")).slug == "demo-host"
    with pytest.raises(NotFoundError):
        await services.fiches.find("demo-pay", "KE")


async def test_submit_stores_a_pending_contribution() -> None:
    services = await _services()
    contribution = await services.contributions.submit(_input())
    assert contribution.status is ContributionStatus.PENDING
    assert [c.id for c in await services.contributions.pending()] == [contribution.id]


async def test_submit_refuses_secrets_and_never_stores_them() -> None:
    services = await _services()
    with pytest.raises(SecretDetectedError):
        await services.contributions.submit(_input(body_md="Ma clé : sk_live_" + "Ab12" * 6))
    assert await services.contributions.pending() == []


async def test_submit_checks_fiche_and_email() -> None:
    services = await _services()
    with pytest.raises(NotFoundError):
        await services.contributions.submit(_input(fiche_slug="inconnue"))
    with pytest.raises(InvalidInputError):
        await services.contributions.submit(_input(email="pas-un-email"))


async def test_review_once_only() -> None:
    services = await _services()
    contribution = await services.contributions.submit(_input())
    reviewed = await services.contributions.review(contribution.id, approve=True, reviewer="aziz")
    assert reviewed.status is ContributionStatus.APPROVED
    with pytest.raises(InvalidInputError):
        await services.contributions.review(contribution.id, approve=False, reviewer="aziz")


async def test_confirm_checks_the_target() -> None:
    services = await _services()
    await services.contributions.confirm(TargetKind.GOTCHA, "demo-pay-sn.jeton-expire")
    with pytest.raises(NotFoundError):
        await services.contributions.confirm(TargetKind.GOTCHA, "demo-pay-sn.absent")


async def test_report_makes_the_service_degraded() -> None:
    services = await _services()
    fiche = await services.fiches.get("demo-pay-sn")
    assert (await services.incidents.status_for(fiche)).status is Status.NORMAL
    await services.incidents.report(
        OutageReport(service_slug="demo-pay", country="SN", description="Paiements en attente.")
    )
    assert (await services.incidents.status_for(fiche)).status is Status.DEGRADED
    with pytest.raises(InvalidInputError):
        await services.incidents.report(
            OutageReport(service_slug="inconnu", description="Service qui n'existe pas.")
        )


async def test_refresh_respects_min_interval_and_survives_failures() -> None:
    clock = FixedClock(NOW)
    feed = FakeFeed()
    services = await _services(feed, clock)
    await services.incidents.refresh_if_stale()
    await services.incidents.refresh_if_stale()
    assert feed.calls == 1
    clock.at = NOW + timedelta(minutes=11)
    await services.incidents.refresh_if_stale()
    assert feed.calls == 2

    failing = await _services(FakeFeed(fail=True))
    assert await failing.incidents.refresh_if_stale() == 0
