"""Export des contributions approuvées vers content/ (tâche A7)."""

from __future__ import annotations

import shutil
from datetime import UTC, datetime
from pathlib import Path

import pytest

from app.domain.models import Contribution, ContributionKind, ContributionStatus, Publication
from app.domain.text import TERM_LINK_RE
from app.stores.content_files import export_contributions, load_fiches
from tests.conftest import TEST_CONTENT_DIR

REVIEWED = datetime(2026, 11, 3, 10, 0, tzinfo=UTC)


@pytest.fixture
def content_dir(tmp_path: Path) -> Path:
    target = tmp_path / "content"
    shutil.copytree(TEST_CONTENT_DIR, target)
    return target


def _contribution(**changes: object) -> Contribution:
    data: dict[str, object] = {
        "id": "abcdef0123456789abcdef0123456789",
        "kind": ContributionKind.GOTCHA,
        "fiche_slug": "demo-pay-sn",
        "title": 'Le callback "arrive" deux fois',
        "body_md": "Le callback arrive deux fois.\n\n## Exemple\n\nUn paiement, deux livraisons.",
        "source_url": "https://example.com/fil",
        "pseudo": "dev_test",
        "email": "dev_test@example.com",
        "status": ContributionStatus.APPROVED,
        "created_at": datetime(2026, 11, 2, 9, 0, tzinfo=UTC),
        "reviewed_at": REVIEWED,
        "reviewer": "aziz",
    }
    data.update(changes)
    return Contribution.model_validate(data)


def test_approved_gotcha_becomes_a_valid_draft(content_dir: Path) -> None:
    written = export_contributions([_contribution()], content_dir)
    assert [p.name for p in written] == ["contribution-abcdef01.md"]

    fiche = next(f for f in load_fiches(content_dir) if f.slug == "demo-pay-sn")
    gotcha = fiche.find_gotcha("demo-pay-sn.contribution-abcdef01")
    assert gotcha is not None
    assert gotcha.publication is Publication.DRAFT
    assert gotcha.title == 'Le callback "arrive" deux fois'
    assert gotcha.sources[0].author == "dev_test"
    assert str(gotcha.sources[0].url) == "https://example.com/fil"
    assert gotcha.last_confirmed_on.isoformat() == "2026-11-03"
    assert "### Exemple" in gotcha.symptom_md  # titre rétrogradé, découpage intact


def test_email_is_never_written(content_dir: Path) -> None:
    for path in export_contributions([_contribution()], content_dir):
        assert "@example.com" not in path.read_text(encoding="utf-8")


def test_export_is_idempotent(content_dir: Path) -> None:
    export_contributions([_contribution()], content_dir)
    assert export_contributions([_contribution()], content_dir) == []


def test_corrections_and_unknown_fiches_become_notes(content_dir: Path) -> None:
    written = export_contributions(
        [
            _contribution(kind=ContributionKind.CORRECTION, id="1" * 32),
            _contribution(fiche_slug="fiche-absente", id="2" * 32),
        ],
        content_dir,
    )
    assert [p.parent.name for p in written] == ["a-integrer", "a-integrer"]
    assert "Texte de la contribution" in written[0].read_text(encoding="utf-8")
    assert len(load_fiches(content_dir)) == 2  # les notes ne sont pas du contenu publié


def test_pending_and_rejected_are_ignored(content_dir: Path) -> None:
    contributions = [
        _contribution(status=ContributionStatus.PENDING, id="3" * 32),
        _contribution(status=ContributionStatus.REJECTED, id="4" * 32),
    ]
    assert export_contributions(contributions, content_dir) == []


def test_an_integrated_or_deleted_draft_is_not_exported_again(content_dir: Path) -> None:
    [draft] = export_contributions([_contribution()], content_dir)
    draft.unlink()  # intégré à la fiche puis supprimé, comme le demande la note
    assert export_contributions([_contribution()], content_dir) == []
    ledger = (content_dir / "a-integrer" / "contributions-exportees.txt").read_text("utf-8")
    assert _contribution().id in ledger


@pytest.mark.parametrize("separator", ["\f", " ", "\x85", "\r"])
def test_hidden_line_breaks_cannot_create_a_section(content_dir: Path, separator: str) -> None:
    body = f"Le callback arrive deux fois.{separator}## Cause\nTexte injecté."
    export_contributions([_contribution(body_md=body)], content_dir)
    fiche = next(f for f in load_fiches(content_dir) if f.slug == "demo-pay-sn")
    gotcha = fiche.find_gotcha("demo-pay-sn.contribution-abcdef01")
    assert gotcha is not None
    assert "Texte injecté" in gotcha.symptom_md
    assert "Texte injecté" not in gotcha.cause_md


def test_code_blocks_are_kept_and_never_split_the_draft(content_dir: Path) -> None:
    body = "Exemple :\n\n```bash\n## commentaire du script\nif [[ -z $X ]]; then exit 1; fi\n```\n"
    export_contributions([_contribution(body_md=body)], content_dir)
    fiche = next(f for f in load_fiches(content_dir) if f.slug == "demo-pay-sn")
    gotcha = fiche.find_gotcha("demo-pay-sn.contribution-abcdef01")
    assert gotcha is not None
    assert "## commentaire du script" in gotcha.symptom_md  # intact dans le bloc de code
    assert not TERM_LINK_RE.search(gotcha.symptom_md)  # « [[ » n'est pas un lien de glossaire


def test_an_unclosed_code_block_does_not_swallow_the_sections(content_dir: Path) -> None:
    export_contributions([_contribution(body_md="Exemple :\n```\ncode sans fin")], content_dir)
    fiche = next(f for f in load_fiches(content_dir) if f.slug == "demo-pay-sn")
    assert fiche.find_gotcha("demo-pay-sn.contribution-abcdef01") is not None


def test_a_slug_can_never_write_outside_content(content_dir: Path) -> None:
    written = export_contributions([_contribution(fiche_slug="../../evil")], content_dir)
    assert [p.name for p in written] == ["contribution-abcdef01.md"]
    assert all(p.resolve().is_relative_to(content_dir.resolve()) for p in written)
    assert not (content_dir.parent.parent / "evil").exists()
