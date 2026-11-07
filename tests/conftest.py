"""Fixtures partagées : horloge figée, application de test, client HTTP, jeton CSRF."""

from __future__ import annotations

import re
from collections.abc import Callable, Iterator
from datetime import UTC, datetime
from pathlib import Path

import pytest
from starlette.testclient import TestClient

from app.config import ROOT_DIR, Settings
from app.container import Services, build_services
from app.domain.ports import IdentityProvider
from app.main import create_app
from app.services.clock import FixedClock
from app.stores.memory.store import MemoryStore

NOW = datetime(2026, 11, 2, 12, 0, tzinfo=UTC)
TEST_CONTENT_DIR = Path(__file__).parent / "fixtures" / "content"
FIXTURES_DIR = ROOT_DIR / "fixtures"


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture
def clock() -> FixedClock:
    return FixedClock(NOW)


@pytest.fixture
def settings() -> Settings:
    """Comme en développement : vrai contenu, brouillons visibles, données fictives."""
    return Settings(env="test")


def make_client(
    settings: Settings,
    clock: FixedClock,
    *,
    identity: IdentityProvider | None = None,
    store: MemoryStore | None = None,
) -> TestClient:
    async def factory(s: Settings) -> Services:
        memory = store or MemoryStore.from_directories(
            s.content_dir, s.fixtures_dir if s.load_fixtures else None, now=clock.now()
        )
        return await build_services(s, clock=clock, store=memory, identity=identity)

    return TestClient(create_app(settings, services_factory=factory))


@pytest.fixture
def client(settings: Settings, clock: FixedClock) -> Iterator[TestClient]:
    with make_client(settings, clock) as test_client:
        yield test_client


@pytest.fixture
def prod_client(clock: FixedClock) -> Iterator[TestClient]:
    """Comme en production, mais avec le stockage mémoire et l'extrait du flux de pannes."""
    settings = Settings(
        env="prod",
        store="memory",
        show_drafts=False,
        load_fixtures=False,
        ingest_live=False,
        site_url="https://gotcha.test",
    )
    with make_client(settings, clock) as test_client:
        yield test_client


@pytest.fixture
def csrf(client: TestClient) -> Callable[[str], str]:
    """Charge une page et renvoie le jeton CSRF de son formulaire."""

    def get_token(path: str = "/contribuer") -> str:
        match = re.search(r'name="csrf_token" value="([^"]+)"', client.get(path).text)
        assert match, f"aucun jeton CSRF sur {path}"
        return match.group(1)

    return get_token
