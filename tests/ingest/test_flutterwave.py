"""Import Flutterwave, testé sur l'extrait réel de fixtures/flutterwave_incidents.json."""

from __future__ import annotations

import json

import pytest

from app.config import ROOT_DIR
from app.domain.models import Status
from app.ingest.flutterwave import FlutterwaveFeed, map_incident, parse_incidents

FIXTURE = ROOT_DIR / "fixtures" / "flutterwave_incidents.json"


def _raw(incident_id: str) -> dict:
    data = json.loads(FIXTURE.read_text(encoding="utf-8"))
    return next(i for i in data["incidents"] if i["id"] == incident_id)


def _pairs(incident_id: str) -> list[tuple[str | None, str | None, bool]]:
    return [(i.service_slug, i.country, i.is_active) for i in map_incident(_raw(incident_id))]


def test_named_tracked_operator_and_country() -> None:
    assert _pairs("zt52rsf4m8n8") == [("orange-money", "CM", True)]


def test_resolved_incident_has_resolution_date() -> None:
    assert _pairs("vhmsn1nj70ns") == [("orange-money", "CM", False)]


def test_country_from_single_country_currency() -> None:
    assert _pairs("nq9gqhx3w78r") == [("mtn-momo", "GH", False)]


def test_generic_mobile_money_incident_covers_each_country() -> None:
    assert _pairs("56z7nwvdqwsg") == [
        (None, "BF", False),
        (None, "CI", False),
        (None, "CM", False),
        (None, "SN", False),
    ]
    assert {c for _, c, _ in _pairs("y3q30r48cl8h")} == {"GH", "KE", "UG"}


@pytest.mark.parametrize(
    "incident_id",
    [
        "hbrqtrccjgk4",  # Airtel : opérateur non suivi
        "rpcyndryh9hs",  # InTouch : agrégateur non suivi
        "lzb9sz2ckvd4",  # paiements KES sans mention du Mobile Money
        "ksmxk17qfcwy",  # cartes bancaires au Nigeria
    ],
)
def test_irrelevant_incidents_are_ignored(incident_id: str) -> None:
    assert map_incident(_raw(incident_id)) == []


def test_channel_list_gives_exact_pairs_instead_of_every_combination() -> None:
    # « Ivory Coast: Wave, Rwanda: MTN, Senegal: Orange, Wave, Uganda: Airtel » : ni Wave
    # au Ghana, ni MTN au Sénégal, ni Airtel, qui n'est pas suivi.
    assert _pairs("w97h9d231shx") == [
        ("mtn-momo", "RW", False),
        ("orange-money", "SN", False),
        ("wave", "CI", False),
        ("wave", "SN", False),
    ]


def test_mobile_money_only_mentioned_as_restored_is_not_an_outage() -> None:
    # Panne des virements : le Mobile Money n'y figure que parmi ce qui remarche.
    assert map_incident(_raw("25rf98nhjkt3")) == []


def test_generic_mobile_money_outage_without_country_applies_everywhere() -> None:
    assert _pairs("gk41xp6cq6k3") == [(None, None, False)]


def test_operator_from_a_later_message_and_country_from_the_text() -> None:
    assert _pairs("kh3twq54nxlt") == [("orange-money", "CM", False)]


def test_generic_outage_with_a_single_country_currency() -> None:
    assert _pairs("9xz0j20zkvvb") == [(None, "GH", False)]


@pytest.mark.parametrize(
    "incident_id",
    [
        "dks5gdjbfbfs",  # Telecel : opérateur non suivi
        "0lpptrsynwl6",  # « selected payment rails » : aucun canal précisé
    ],
)
def test_more_real_incidents_are_ignored(incident_id: str) -> None:
    assert map_incident(_raw(incident_id)) == []


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        # Cas construits : un pays non suivi ne doit pas s'afficher sur le Sénégal.
        ("Orange Guinea Collections Disruption", [("orange-money", "GN")]),
        ("Orange Money disruption in Côte d’Ivoire", [("orange-money", "CI")]),
        ("[ZAR] Mobile Money Payments Affected", [(None, "ZA")]),
    ],
)
def test_country_is_recognised(name: str, expected: list[tuple[str | None, str]]) -> None:
    raw = {"id": "x", "name": name, "created_at": "2026-11-04T10:00:00Z"}
    assert [(i.service_slug, i.country) for i in map_incident(raw)] == expected


def test_ids_are_stable_and_unique() -> None:
    payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
    ids = [i.id for i in parse_incidents(payload)]
    assert len(ids) == len(set(ids))
    assert ids == [i.id for i in parse_incidents(payload)]


def test_impact_maps_to_status() -> None:
    raw = dict(_raw("zt52rsf4m8n8"), impact="critical")
    assert map_incident(raw)[0].status is Status.DOWN


@pytest.mark.anyio
async def test_feed_reads_fixture_when_not_live() -> None:
    feed = FlutterwaveFeed(url="https://exemple.invalid", live=False, fixture_path=FIXTURE)
    incidents = await feed.fetch()
    assert any(i.service_slug == "orange-money" for i in incidents)
