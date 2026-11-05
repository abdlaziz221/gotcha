"""Services métier sur le stockage mémoire et le contenu de test."""

from __future__ import annotations

from datetime import timedelta

import pytest

from app.config import Settings
from app.container import Services, build_services
from app.domain.errors import InvalidInputError, NotFoundError, SecretDetectedError
from app.domain.models import (
    Contribution,
    ContributionInput,
    ContributionStatus,
    Incident,
    IncidentSource,
    OutageReport,
    Status,
    TargetKind,
)
from app.domain.ports import IncidentFeed
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


class RacingStore(MemoryStore):
    """Un autre relecteur refuse la contribution juste après notre lecture."""

    async def get_contribution(self, contribution_id: str) -> Contribution | None:
        current = await super().get_contribution(contribution_id)
        if current is not None and current.status is ContributionStatus.PENDING:
            await self.update_contribution(
                current.model_copy(update={"status": ContributionStatus.REJECTED})
            )
        return current


async def test_review_loses_against_a_simultaneous_reviewer() -> None:
    store = RacingStore(load_fiches(TEST_CONTENT_DIR), load_glossary(TEST_CONTENT_DIR))
    services = await build_services(
        Settings(env="test"), clock=FixedClock(NOW), store=store, feeds=[FakeFeed()]
    )
    contribution = await services.contributions.submit(_input())
    with pytest.raises(InvalidInputError):
        await services.contributions.review(contribution.id, approve=True, reviewer="aziz")
    saved = await MemoryStore.get_contribution(store, contribution.id)
    assert saved is not None
    assert saved.status is ContributionStatus.REJECTED


async def test_confirm_checks_the_target() -> None:
    services = await _services()
    await services.contributions.confirm(TargetKind.GOTCHA, "demo-pay-sn.jeton-expire")
    with pytest.raises(NotFoundError):
        await services.contributions.confirm(TargetKind.GOTCHA, "demo-pay-sn.absent")
    with pytest.raises(NotFoundError):
        await services.contributions.confirm(TargetKind.FICHE, "demo-pay-sn\x00")
    with pytest.raises(InvalidInputError):
        await services.contributions.confirm(TargetKind.FICHE, "demo-pay-sn", pseudo="a\x00b")


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


def _feed_incident() -> Incident:
    return Incident(
        id="flutterwave:x:SN:wave",
        source=IncidentSource.FLUTTERWAVE,
        service_slug="wave",
        country="SN",
        status=Status.DEGRADED,
        title="Panne",
        started_at=NOW,
    )


async def _services_with_store(store: MemoryStore, feeds: list[IncidentFeed]) -> Services:
    return await build_services(
        Settings(env="test"), clock=FixedClock(NOW), store=store, feeds=feeds
    )


async def _database_down(*_args: object, **_kwargs: object) -> None:
    raise ConnectionError("base injoignable")


@pytest.mark.parametrize("method", ["get_last_ingest", "upsert_incident", "set_last_ingest"])
async def test_refresh_survives_store_failures(
    method: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    store = MemoryStore(load_fiches(TEST_CONTENT_DIR), load_glossary(TEST_CONTENT_DIR))
    monkeypatch.setattr(store, method, _database_down)
    services = await _services_with_store(store, [FakeFeed([_feed_incident()])])
    assert await services.incidents.refresh_if_stale() == 0


async def test_failed_feed_does_not_stop_the_next_one() -> None:
    store = MemoryStore(load_fiches(TEST_CONTENT_DIR), load_glossary(TEST_CONTENT_DIR))
    working = FakeFeed([_feed_incident()])
    services = await _services_with_store(store, [FakeFeed(fail=True), working])
    assert await services.incidents.refresh_if_stale() == 1
    assert working.calls == 1
