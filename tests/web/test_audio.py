"""Explication audio en wolof d'un piège (D26) : modèle, contenu, route protégée, recherche."""

from __future__ import annotations

import re
import shutil
from collections.abc import Iterator
from dataclasses import replace
from pathlib import Path

import pytest
from pydantic import ValidationError
from starlette.testclient import TestClient

from app.config import Settings
from app.domain.models import AudioExplanation, SearchQuery
from app.services.clock import FixedClock
from app.stores.content_files import ContentError, load_fiches
from app.stores.search import search_fiches
from tests.conftest import TEST_CONTENT_DIR, FakeIdentity, make_client

GOTCHA = "jeton-expire"
AUDIO_URL = f"/fiches/demo-pay-sn/audio/{GOTCHA}"
SOUND = b"ID3" + bytes(64)  # un faux MP3 : seul l'envoi est testé
AUDIO_HEADER = "audio:\n  file: jeton-expire.mp3\n  recorded_by: awa\n  reviewed_by: moussa\n"
TRANSCRIPT = "\n## Transcription en wolof\n\nJeton bi dafa jeex ci benn waxtu, mobile bi.\n"


def _with_audio(root: Path, *, header: str = AUDIO_HEADER, transcript: str = TRANSCRIPT) -> Path:
    content = root / "content"
    shutil.copytree(TEST_CONTENT_DIR, content)
    path = content / "fiches" / "demo-pay-sn" / "pieges" / f"{GOTCHA}.md"
    text = path.read_text("utf-8").replace("---\n\n", f"{header}---\n\n", 1) + transcript
    path.write_text(text, "utf-8")
    audio_dir = content / "fiches" / "demo-pay-sn" / "audio"
    audio_dir.mkdir()
    (audio_dir / "jeton-expire.mp3").write_bytes(SOUND)
    return content


# --- Modèle et contenu -----------------------------------------------------------------


def test_audio_needs_a_second_speaker() -> None:
    data = {"file": "x.mp3", "transcript_md": "Une transcription.", "recorded_by": "awa"}
    assert AudioExplanation.model_validate(data).reviewed_by is None
    with pytest.raises(ValidationError, match="autre locuteur"):
        AudioExplanation.model_validate({**data, "reviewed_by": "awa"})
    with pytest.raises(ValidationError):
        AudioExplanation.model_validate({**data, "file": "../secret.mp3"})


def test_a_published_gotcha_cannot_carry_an_unreviewed_audio(tmp_path: Path) -> None:
    header = AUDIO_HEADER.replace("  reviewed_by: moussa\n", "")
    with pytest.raises(ContentError, match="audio non relu"):
        load_fiches(_with_audio(tmp_path, header=header))


def test_audio_and_transcript_go_together(tmp_path: Path) -> None:
    with pytest.raises(ContentError, match="vont ensemble"):
        load_fiches(_with_audio(tmp_path, transcript=""))


def test_a_missing_audio_file_stops_the_loading(tmp_path: Path) -> None:
    content = _with_audio(tmp_path)
    (content / "fiches" / "demo-pay-sn" / "audio" / "jeton-expire.mp3").unlink()
    with pytest.raises(ContentError, match="fichier audio introuvable"):
        load_fiches(content)


def test_the_transcript_is_loaded_and_searchable(tmp_path: Path) -> None:
    fiches = load_fiches(_with_audio(tmp_path))
    gotcha = next(f for f in fiches if f.slug == "demo-pay-sn").find_gotcha(f"demo-pay-sn.{GOTCHA}")
    assert gotcha is not None
    assert gotcha.audio is not None
    assert "waxtu" in gotcha.audio.transcript_md
    assert search_fiches(fiches, SearchQuery(text="waxtu"))


# --- Recherche : mots courts entiers (D26) ---------------------------------------------


def test_short_words_only_match_whole_words(tmp_path: Path) -> None:
    fiches = load_fiches(_with_audio(tmp_path))
    hits = {h.title for h in search_fiches(fiches, SearchQuery(text="bi"))}
    assert hits  # « bi » est un mot entier de la transcription
    others = load_fiches(TEST_CONTENT_DIR)
    # Sans transcription, « bi » ne doit pas trouver « mobile » ni « débit ».
    assert not search_fiches(others, SearchQuery(text="bi"))


def test_longer_words_still_match_inside_words() -> None:
    fiches = load_fiches(TEST_CONTENT_DIR)
    assert search_fiches(fiches, SearchQuery(text="expir"))  # trouve « expire »


# --- Route protégée et page ------------------------------------------------------------


@pytest.fixture
def audio_settings(tmp_path: Path) -> Settings:
    return Settings(
        env="test",
        content_dir=_with_audio(tmp_path),
        site_auth=True,
        github_client_id="identifiant",
        github_client_secret="secret",
    )


@pytest.fixture
def site(audio_settings: Settings, clock: FixedClock) -> Iterator[TestClient]:
    with make_client(audio_settings, clock, identity=FakeIdentity()) as client:
        yield client


def _log_in(client: TestClient) -> None:
    start = client.get("/connexion/github", follow_redirects=False)
    state = re.search(r"state=([^&]+)", start.headers["location"])
    assert state
    back = client.get(
        "/github/callback", params={"state": state.group(1), "code": "bon"}, follow_redirects=False
    )
    assert back.status_code == 302


def test_audio_is_reserved_like_the_solution(site: TestClient) -> None:
    assert site.get(AUDIO_URL).status_code == 403
    page = site.get("/fiches/demo-pay-sn").text
    assert AUDIO_URL not in page  # l'aperçu public ne donne ni l'adresse ni la transcription
    assert "waxtu" not in page
    _log_in(site)
    sound = site.get(AUDIO_URL)
    assert sound.status_code == 200
    assert sound.headers["content-type"] == "audio/mpeg"
    assert sound.content == SOUND
    assert sound.headers["cache-control"] == "private, no-store"


def test_audio_of_an_open_fiche_plays_without_an_account(
    audio_settings: Settings, clock: FixedClock
) -> None:
    content = audio_settings.content_dir
    fiche_file = content / "fiches" / "demo-pay-sn" / "fiche.yml"
    fiche_file.write_text(fiche_file.read_text("utf-8") + "open_access: true\n", "utf-8")
    with make_client(audio_settings, clock, identity=FakeIdentity()) as client:
        assert client.get(AUDIO_URL).status_code == 200


def test_audio_is_never_served_from_static(site: TestClient) -> None:
    assert site.get("/static/audio/jeton-expire.mp3").status_code == 404
    assert site.get("/fiches/demo-pay-sn/audio/inconnu").status_code == 404
    assert site.get("/fiches/demo-pay-sn/audio/..%2F..%2Ffiche").status_code == 404


def test_a_draft_audio_is_hidden_in_production(audio_settings: Settings, clock: FixedClock) -> None:
    prod = replace(
        audio_settings, env="prod", show_drafts=False, load_fixtures=False, site_auth=False
    )
    with make_client(prod, clock) as client:
        assert client.get("/fiches/demo-pay-sn/audio/brouillon").status_code == 404


def test_mcp_never_returns_the_audio_or_its_transcript(site: TestClient) -> None:
    from app.mcp import tools

    services = site.app.state.services  # type: ignore[attr-defined]
    fiche = site.portal.call(tools.get_fiche, services, "demo-pay", "SN")  # type: ignore[union-attr]
    dumped = fiche.model_dump_json()
    assert "waxtu" not in dumped
    assert "audio" not in dumped
