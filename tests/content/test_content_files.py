"""Le contenu de content/ est valide : à lancer après chaque modification d'une fiche."""

from __future__ import annotations

import re
import shutil
from pathlib import Path

import pytest

from app.config import ROOT_DIR
from app.domain.models import Publication
from app.domain.text import TERM_LINK_RE
from app.stores.content_files import ContentError, load_fiches, load_glossary
from tests.conftest import TEST_CONTENT_DIR

CONTENT_DIR = ROOT_DIR / "content"


def test_all_fiches_load() -> None:
    fiches = load_fiches(CONTENT_DIR)
    assert fiches, "aucune fiche dans content/fiches"
    slugs = [f.slug for f in fiches]
    assert len(slugs) == len(set(slugs))


def test_every_gotcha_has_a_source_and_published_ones_a_verifier() -> None:
    for fiche in load_fiches(CONTENT_DIR):
        for gotcha in fiche.gotchas:
            assert gotcha.sources, f"{gotcha.id} : aucune source"
            if gotcha.publication is Publication.PUBLISHED:
                assert gotcha.verified_by, f"{gotcha.id} : publié sans verified_by"


def test_a_confirmation_date_in_the_future_is_refused(tmp_path: Path) -> None:
    # La base garde la date la plus récente : une date future ne se corrigerait plus.
    content = tmp_path / "content"
    shutil.copytree(TEST_CONTENT_DIR, content)
    gotcha = content / "fiches" / "demo-pay-sn" / "pieges" / "jeton-expire.md"
    text = gotcha.read_text(encoding="utf-8")
    gotcha.write_text(
        re.sub(r"last_confirmed_on: .*", "last_confirmed_on: 2062-10-28", text), encoding="utf-8"
    )
    with pytest.raises(ContentError, match=r"jeton-expire\.md : last_confirmed_on 2062-10-28"):
        load_fiches(content)

    fiche = content / "fiches" / "demo-host" / "fiche.yml"
    shutil.copy(TEST_CONTENT_DIR / "fiches" / "demo-pay-sn" / "pieges" / "jeton-expire.md", gotcha)
    text = fiche.read_text(encoding="utf-8")
    fiche.write_text(
        re.sub(r"last_confirmed_on: .*", "last_confirmed_on: 2062-10-28", text), encoding="utf-8"
    )
    with pytest.raises(ContentError, match=r"fiche\.yml : last_confirmed_on 2062-10-28"):
        load_fiches(content)


def test_glossary_links_point_to_existing_terms() -> None:
    known = {t.slug for t in load_glossary(CONTENT_DIR)}
    for fiche in load_fiches(CONTENT_DIR):
        texts = [s.body_md for s in fiche.steps] + [
            part for g in fiche.gotchas for part in (g.symptom_md, g.cause_md, g.fix_md)
        ]
        for text in texts:
            for match in TERM_LINK_RE.finditer(text):
                term = match.group(1).strip()
                assert term in known, f"{fiche.slug} : terme [[{term}]] absent de glossaire.yml"
