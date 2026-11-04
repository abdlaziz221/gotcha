"""Tests de contrat : MemoryStore et PostgresStore doivent se comporter exactement pareil.

PostgreSQL : définir GOTCHA_TEST_DATABASE_URL (base jetable !) pour activer ces tests.
"""

from __future__ import annotations

import os
from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta

import pytest

from app.config import ROOT_DIR
from app.domain.models import (
    Account,
    Confirmation,
    Contribution,
    ContributionKind,
    ContributionStatus,
    Incident,
    IncidentSource,
    OAuthGrantKind,
    SearchHitKind,
    SearchQuery,
    Status,
    TargetKind,
)
from app.domain.ports import Store
from app.stores.content_files import load_fiches, load_glossary
from app.stores.memory.store import MemoryStore
from tests.conftest import TEST_CONTENT_DIR

pytestmark = pytest.mark.anyio

T0 = datetime(2026, 11, 1, 8, 0, tzinfo=UTC)


async def _postgres_store() -> Store:
    import asyncpg

    from app.stores.postgres.migrate import apply_migrations
    from app.stores.postgres.store import PostgresStore

    url = os.environ.get("GOTCHA_TEST_DATABASE_URL")
    if not url:
        pytest.skip("GOTCHA_TEST_DATABASE_URL non défini")
    conn = await asyncpg.connect(url)
    try:
        await apply_migrations(conn, ROOT_DIR / "migrations")
        await conn.execute(
            "TRUNCATE fiches, gotchas, fiche_revisions, glossary_terms, confirmations,"
            " contributions, incidents, ingest_runs, accounts, oauth_clients, oauth_grants CASCADE"
        )
    finally:
        await conn.close()
    store = await PostgresStore.connect(url)
    for fiche in load_fiches(TEST_CONTENT_DIR):
        await store.upsert_fiche(fiche)
    await store.upsert_glossary(load_glossary(TEST_CONTENT_DIR))
    return store


@pytest.fixture(params=["memory", pytest.param("postgres", marks=pytest.mark.postgres)])
async def store(request: pytest.FixtureRequest) -> AsyncIterator[Store]:
    if request.param == "memory":
        s: Store = MemoryStore(load_fiches(TEST_CONTENT_DIR), load_glossary(TEST_CONTENT_DIR))
    else:
        s = await _postgres_store()
    yield s
    await s.close()


def _incident(n: int, **changes: object) -> Incident:
    data: dict[str, object] = {
        "id": f"community:{n}",
        "source": IncidentSource.COMMUNITY,
        "service_slug": "demo-pay",
        "country": "SN",
        "status": Status.DEGRADED,
        "title": f"Panne {n}",
        "started_at": T0 + timedelta(minutes=n),
    }
    data.update(changes)
    return Incident.model_validate(data)


def _contribution(n: int) -> Contribution:
    return Contribution(
        id=f"c{n}",
        kind=ContributionKind.GOTCHA,
        fiche_slug="demo-pay-sn",
        title=f"Contribution {n}",
        body_md="Un texte assez long pour être valide.",
        pseudo="dev",
        email="dev@example.com",
        created_at=T0 + timedelta(minutes=n),
    )


# --- Fiches ------------------------------------------------------------------


async def test_without_drafts_only_published_fiches_and_gotchas(store: Store) -> None:
    fiches = await store.list_fiches(include_drafts=False)
    assert [f.slug for f in fiches] == ["demo-pay-sn"]
    assert [g.id for g in fiches[0].gotchas] == ["demo-pay-sn.jeton-expire"]


async def test_with_drafts_all_fiches_sorted_by_title(store: Store) -> None:
    fiches = await store.list_fiches(include_drafts=True)
    assert [f.slug for f in fiches] == ["demo-host", "demo-pay-sn"]
    pay = fiches[1]
    assert {g.id for g in pay.gotchas} == {"demo-pay-sn.jeton-expire", "demo-pay-sn.brouillon"}


async def test_get_fiche_respects_drafts(store: Store) -> None:
    assert await store.get_fiche("demo-host", include_drafts=False) is None
    assert await store.get_fiche("demo-host", include_drafts=True) is not None
    assert await store.get_fiche("inconnue", include_drafts=True) is None


async def test_fiche_keeps_all_its_content(store: Store) -> None:
    fiche = await store.get_fiche("demo-pay-sn", include_drafts=False)
    assert fiche is not None
    assert fiche.service.slug == "demo-pay"
    assert fiche.country == "SN"
    assert [s.title for s in fiche.steps] == ["Créer un compte", "Payer"]
    assert fiche.differences[0].sandbox == "EUR"
    assert fiche.error_codes[0].code == "E42"


async def test_search_finds_gotcha_by_keyword(store: Store) -> None:
    hits = await store.search(SearchQuery(text="jeton"), include_drafts=False)
    assert hits, "aucun résultat"
    assert hits[0].kind is SearchHitKind.GOTCHA
    assert hits[0].fiche_slug == "demo-pay-sn"
    assert hits[0].anchor == "piege-jeton-expire"


async def test_search_ignores_case_and_accents(store: Store) -> None:
    hits = await store.search(SearchQuery(text="SENEGAL"), include_drafts=False)
    assert any(h.fiche_slug == "demo-pay-sn" for h in hits)


async def test_search_finds_error_code(store: Store) -> None:
    hits = await store.search(SearchQuery(text="E42"), include_drafts=False)
    assert any(h.kind is SearchHitKind.ERROR_CODE for h in hits)


async def test_search_filters_and_hides_drafts(store: Store) -> None:
    assert await store.search(SearchQuery(text="jeton", service="autre"), include_drafts=True) == []
    assert await store.search(SearchQuery(text="jeton", country="KE"), include_drafts=True) == []
    hidden = await store.search(SearchQuery(text="surprenant"), include_drafts=False)
    assert hidden == []
    shown = await store.search(SearchQuery(text="surprenant"), include_drafts=True)
    assert [h.anchor for h in shown] == ["piege-brouillon"]


async def test_search_respects_limit(store: Store) -> None:
    hits = await store.search(SearchQuery(text="", limit=1), include_drafts=True)
    assert len(hits) == 1


async def test_glossary_sorted_by_term(store: Store) -> None:
    terms = await store.list_glossary()
    assert [t.slug for t in terms] == ["jeton-acces", "webhook"]


# --- Pannes ------------------------------------------------------------------


async def test_incidents_newest_first_with_filters(store: Store) -> None:
    await store.upsert_incident(_incident(1))
    await store.upsert_incident(_incident(2, resolved_at=T0 + timedelta(hours=1)))
    await store.upsert_incident(_incident(3, country="CI"))
    assert [i.id for i in await store.list_incidents()] == [
        "community:3",
        "community:2",
        "community:1",
    ]
    assert [i.id for i in await store.list_incidents(active_only=True)] == [
        "community:3",
        "community:1",
    ]
    assert [i.id for i in await store.list_incidents(country="SN")] == [
        "community:2",
        "community:1",
    ]
    assert await store.list_incidents(service_slug="autre") == []
    assert len(await store.list_incidents(limit=1)) == 1


async def test_upsert_incident_is_idempotent(store: Store) -> None:
    await store.upsert_incident(_incident(1))
    await store.upsert_incident(_incident(1, resolved_at=T0 + timedelta(hours=2)))
    incidents = await store.list_incidents()
    assert len(incidents) == 1
    assert incidents[0].resolved_at == T0 + timedelta(hours=2)


async def test_last_ingest_round_trip(store: Store) -> None:
    assert await store.get_last_ingest(IncidentSource.FLUTTERWAVE) is None
    await store.set_last_ingest(IncidentSource.FLUTTERWAVE, T0)
    assert await store.get_last_ingest(IncidentSource.FLUTTERWAVE) == T0


# --- Contributions et confirmations -------------------------------------------


async def test_contributions_queue(store: Store) -> None:
    await store.add_contribution(_contribution(2))
    await store.add_contribution(_contribution(1))
    pending = await store.list_contributions(status=ContributionStatus.PENDING)
    assert [c.id for c in pending] == ["c1", "c2"]

    approved = pending[0].model_copy(update={"status": ContributionStatus.APPROVED})
    await store.update_contribution(approved)
    assert [c.id for c in await store.list_contributions(status=ContributionStatus.PENDING)] == [
        "c2"
    ]
    fetched = await store.get_contribution("c1")
    assert fetched is not None
    assert fetched.status is ContributionStatus.APPROVED
    assert fetched.email == "dev@example.com"
    assert await store.get_contribution("absente") is None


async def test_confirmation_updates_gotcha(store: Store) -> None:
    await store.add_confirmation(
        Confirmation(
            target_kind=TargetKind.GOTCHA,
            target_id="demo-pay-sn.jeton-expire",
            created_at=datetime(2026, 11, 2, 9, 0, tzinfo=UTC),
        )
    )
    fiche = await store.get_fiche("demo-pay-sn", include_drafts=False)
    assert fiche is not None
    gotcha = fiche.find_gotcha("demo-pay-sn.jeton-expire")
    assert gotcha is not None
    assert gotcha.confirmations == 1
    assert gotcha.last_confirmed_on.isoformat() == "2026-11-02"


async def test_confirmation_updates_fiche_unless_negative(store: Store) -> None:
    day = datetime(2026, 11, 2, 9, 0, tzinfo=UTC)
    await store.add_confirmation(
        Confirmation(target_kind=TargetKind.FICHE, target_id="demo-pay-sn", created_at=day)
    )
    await store.add_confirmation(
        Confirmation(
            target_kind=TargetKind.FICHE, target_id="demo-pay-sn", still_works=False, created_at=day
        )
    )
    fiche = await store.get_fiche("demo-pay-sn", include_drafts=False)
    assert fiche is not None
    assert fiche.confirmations == 1
    assert fiche.last_confirmed_on.isoformat() == "2026-11-02"


# --- Rechargement du contenu (scripts/seed.py) ---------------------------------


async def test_gotchas_keep_their_order(store: Store) -> None:
    fiche = await store.get_fiche("demo-pay-sn", include_drafts=True)
    assert fiche is not None
    assert [g.id for g in fiche.gotchas] == ["demo-pay-sn.brouillon", "demo-pay-sn.jeton-expire"]


async def test_reseeding_keeps_confirmations(store: Store) -> None:
    day = datetime(2026, 11, 2, 9, 0, tzinfo=UTC)
    await store.add_confirmation(
        Confirmation(target_kind=TargetKind.FICHE, target_id="demo-pay-sn", created_at=day)
    )
    await store.add_confirmation(
        Confirmation(
            target_kind=TargetKind.GOTCHA, target_id="demo-pay-sn.jeton-expire", created_at=day
        )
    )
    reloaded = next(f for f in load_fiches(TEST_CONTENT_DIR) if f.slug == "demo-pay-sn")
    await store.upsert_fiche(reloaded)

    fiche = await store.get_fiche("demo-pay-sn", include_drafts=True)
    assert fiche is not None
    assert fiche.confirmations == 1
    assert fiche.last_confirmed_on.isoformat() == "2026-11-02"
    gotcha = fiche.find_gotcha("demo-pay-sn.jeton-expire")
    assert gotcha is not None
    assert gotcha.confirmations == 1


async def test_reseeding_removes_gotchas_deleted_from_content(store: Store) -> None:
    fiche = await store.get_fiche("demo-pay-sn", include_drafts=True)
    assert fiche is not None
    await store.upsert_fiche(fiche.model_copy(update={"gotchas": fiche.gotchas[1:]}))
    updated = await store.get_fiche("demo-pay-sn", include_drafts=True)
    assert updated is not None
    assert [g.id for g in updated.gotchas] == ["demo-pay-sn.jeton-expire"]


# --- Comptes et connexion OAuth --------------------------------------------------


async def test_account_is_created_then_updated(store: Store) -> None:
    assert await store.get_account("github:1") is None
    account = Account(id="github:1", pseudo="awa", created_at=T0, last_login_at=T0)
    await store.save_account(account)
    later = account.model_copy(update={"pseudo": "awa2", "last_login_at": T0 + timedelta(days=1)})
    await store.save_account(later)
    saved = await store.get_account("github:1")
    assert saved is not None
    assert saved.pseudo == "awa2"
    assert saved.created_at == T0
    assert saved.last_login_at == T0 + timedelta(days=1)


async def test_a_new_login_does_not_lift_a_block(store: Store) -> None:
    account = Account(id="github:1", pseudo="awa", created_at=T0, last_login_at=T0)
    await store.save_account(account.model_copy(update={"blocked": True}))
    await store.save_account(account)
    saved = await store.get_account("github:1")
    assert saved is not None
    assert saved.blocked


async def test_oauth_client_round_trip(store: Store) -> None:
    assert await store.get_oauth_client("c1") is None
    await store.save_oauth_client("c1", {"client_name": "outil", "redirect_uris": ["http://x"]})
    assert await store.get_oauth_client("c1") == {
        "client_name": "outil",
        "redirect_uris": ["http://x"],
    }


async def test_oauth_grant_expires(store: Store) -> None:
    await store.add_oauth_grant(OAuthGrantKind.ACCESS, "k", {"a": 1}, T0 + timedelta(hours=1))
    assert await store.get_oauth_grant(OAuthGrantKind.ACCESS, "k", T0) == {"a": 1}
    assert await store.get_oauth_grant(OAuthGrantKind.REFRESH, "k", T0) is None
    later = T0 + timedelta(hours=1)
    assert await store.get_oauth_grant(OAuthGrantKind.ACCESS, "k", later) is None
    assert await store.take_oauth_grant(OAuthGrantKind.ACCESS, "k", later) is None


async def test_oauth_grant_is_taken_only_once(store: Store) -> None:
    await store.add_oauth_grant(OAuthGrantKind.CODE, "k", {"a": 1}, T0 + timedelta(hours=1))
    assert await store.take_oauth_grant(OAuthGrantKind.CODE, "k", T0) == {"a": 1}
    assert await store.take_oauth_grant(OAuthGrantKind.CODE, "k", T0) is None
    assert await store.get_oauth_grant(OAuthGrantKind.CODE, "k", T0) is None


async def test_expired_oauth_grants_are_deleted(store: Store) -> None:
    await store.add_oauth_grant(OAuthGrantKind.LOGIN, "vieux", {"a": 1}, T0)
    await store.add_oauth_grant(OAuthGrantKind.LOGIN, "neuf", {"a": 2}, T0 + timedelta(hours=1))
    await store.delete_expired_oauth_grants(T0)
    assert await store.get_oauth_grant(OAuthGrantKind.LOGIN, "neuf", T0) == {"a": 2}
    assert (
        await store.take_oauth_grant(OAuthGrantKind.LOGIN, "vieux", T0 - timedelta(hours=1)) is None
    )
