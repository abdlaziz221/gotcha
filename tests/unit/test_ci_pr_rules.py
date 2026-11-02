"""Règles de PR de la CI (scripts/ci_pr_rules.py), lancées comme le fait la CI."""

from __future__ import annotations

import os
import subprocess
import sys

import pytest

from app.config import ROOT_DIR

SCRIPT = ROOT_DIR / "scripts" / "ci_pr_rules.py"


def run(title: str, *, branch: str = "aziz/A3-postgres", lines: int = 10) -> tuple[int, str]:
    env = {
        **{
            k: v
            for k, v in os.environ.items()
            if k not in {"GITHUB_ACTIONS", "CIRCLE_PULL_REQUEST"}
        },
        "PR_TITLE": title,
        "PR_ADDITIONS": str(lines),
        "PR_DELETIONS": "0",
        "PR_BRANCH": branch,
        "PYTHONIOENCODING": "utf-8",
    }
    result = subprocess.run(
        [sys.executable, str(SCRIPT)], env=env, capture_output=True, text=True, encoding="utf-8"
    )
    return result.returncode, result.stdout


@pytest.mark.parametrize(
    "title",
    [
        "feat(web): mode pas à pas",
        "content(mpesa-ke): piège du jeton expiré",
        "fix: lien mort dans le pied de page",
        "chore(deps): bump fastapi from 0.162.0 to 0.163.0",
        "feat(mcp)!: nouveau format de réponse",
    ],
)
def test_valid_titles_pass(title: str) -> None:
    code, _ = run(title)
    assert code == 0


@pytest.mark.parametrize(
    "title",
    [
        "Mise à jour",
        "feat:sans espace",
        "Feat(web): majuscule",
        "feat(Web): zone en majuscules",
        "wip(web): type inconnu",
        "feat(web): ",
    ],
)
def test_invalid_titles_fail(title: str) -> None:
    code, output = run(title)
    assert code == 1
    assert "ne suit pas le format" in output


def test_size_and_branch_are_only_warnings() -> None:
    code, output = run("feat(web): grosse PR", branch="ma-branche", lines=900)
    assert code == 0
    assert "900 lignes" in output
    assert "ma-branche" in output
