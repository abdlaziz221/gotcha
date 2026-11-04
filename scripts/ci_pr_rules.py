"""Règles de PR vérifiées par la CI : titre (bloquant), taille et nom de branche (avertissements).

Sur CircleCI, le script lit la PR sur l'API publique de GitHub (CIRCLE_PULL_REQUEST).
On peut aussi lui passer le titre, la taille et la branche par variables d'environnement
(PR_TITLE, PR_ADDITIONS, PR_DELETIONS, PR_BRANCH) : c'est ce que font les tests.
Usage local : PR_TITLE="feat(web): mode pas à pas" python scripts/ci_pr_rules.py
"""

from __future__ import annotations

import json
import os
import re
import sys
import urllib.request
from typing import Any

TYPES = "feat|fix|content|style|refactor|perf|test|docs|chore|ci|build|revert"
TITLE_RE = re.compile(rf"({TYPES})(\([a-z0-9][a-z0-9-]*\))?!?: \S.{{2,88}}")
BRANCH_RE = re.compile(r"(aziz|loum|khalifa)/[A-Za-z0-9]+-[a-z0-9-]+|dependabot/.+")
MAX_LINES = 400


def fetch_pull_request(pr_url: str) -> dict[str, Any] | None:
    """Lit une PR publique ; None si l'API ne répond pas (quota, réseau)."""
    repo, number = pr_url.split("github.com/", 1)[1].split("/pull/")
    api_url = f"https://api.github.com/repos/{repo}/pulls/{number}"
    try:
        with urllib.request.urlopen(api_url, timeout=10) as response:
            return json.load(response)
    except Exception as exc:
        print(f"PR illisible ({exc}) : contrôle sauté.")
        return None


def report(level: str, message: str) -> None:
    if os.environ.get("GITHUB_ACTIONS") == "true":
        print(f"::{level}::{message}")
    else:
        print(f"{'ÉCHEC' if level == 'error' else 'Avertissement'} : {message}")


def main() -> int:
    if "PR_TITLE" in os.environ:
        title = os.environ["PR_TITLE"]
        size = int(os.environ.get("PR_ADDITIONS") or 0) + int(os.environ.get("PR_DELETIONS") or 0)
        branch = os.environ.get("PR_BRANCH", "")
    elif os.environ.get("CIRCLE_PULL_REQUEST"):
        pr = fetch_pull_request(os.environ["CIRCLE_PULL_REQUEST"])
        if pr is None:
            return 0
        title = pr["title"]
        size = pr.get("additions", 0) + pr.get("deletions", 0)
        branch = os.environ.get("CIRCLE_BRANCH") or pr["head"]["ref"]
    else:
        print("Pas de PR pour cette branche : rien à vérifier.")
        return 0

    if size > MAX_LINES:
        report("warning", f"{size} lignes modifiées : découpez si possible (moins de {MAX_LINES}).")
    if branch and not BRANCH_RE.fullmatch(branch):
        report("warning", f"la branche « {branch} » ne suit pas prénom/tâche-sujet.")
    if not TITLE_RE.fullmatch(title):
        report(
            "error",
            f"le titre « {title} » ne suit pas le format type(zone): description, "
            "par exemple feat(web): mode pas à pas (voir CONTRIBUTING.md).",
        )
        return 1
    print(f"Titre conforme : {title}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
