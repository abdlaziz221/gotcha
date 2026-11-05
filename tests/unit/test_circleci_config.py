"""La configuration CircleCI doit rester valide : sinon aucun job ne se lance après un push.

Une configuration que CircleCI refuse ne donne ni échec ni statut sur la PR : la CI
semble simplement absente, et la PR reste bloquée sans explication. Ces tests attrapent
ce cas avant le push, et vérifient que chaque push relance bien les 8 contrôles exigés
sur main.
"""

from __future__ import annotations

import json
import re
from typing import Any

import yaml

from app.config import ROOT_DIR

CONFIG = ROOT_DIR / ".circleci" / "config.yml"
RULESET = ROOT_DIR / ".github" / "rulesets" / "protection-main.json"
# Seules formes de « << … >> » que CircleCI accepte dans notre configuration.
PARAMETER_RE = re.compile(r"<<\s*(?:parameters|pipeline\.parameters|pipeline|matrix)\.[\w.-]+\s*>>")


def _config() -> dict[str, Any]:
    return yaml.safe_load(CONFIG.read_text("utf-8"))


def test_config_is_valid_yaml_with_workflows_and_jobs() -> None:
    config = _config()
    assert config["version"] == 2.1
    for workflow in config["workflows"].values():
        for entry in workflow["jobs"]:
            name = entry if isinstance(entry, str) else next(iter(entry))
            assert name in config["jobs"], f"le workflow appelle un job inconnu : {name}"


def test_no_stray_parameter_markers() -> None:
    """« << » ouvre un paramètre CircleCI : un here-string bash (<<<) invalide tout le fichier."""
    for number, line in enumerate(CONFIG.read_text("utf-8").splitlines(), start=1):
        rest = PARAMETER_RE.sub("", line)
        assert "<<" not in rest, (
            f".circleci/config.yml:{number} : « << » hors d'un paramètre CircleCI. "
            "Pas de here-string (<<<) ni de heredoc : écrire dans un fichier, puis le lire."
        )


def test_every_push_runs_the_whole_workflow() -> None:
    """Aucun filtre de branche : chaque commit poussé, sur n'importe quelle PR, relance tout."""
    for workflow in _config()["workflows"].values():
        assert "triggers" not in workflow, "un déclencheur limite le workflow : à retirer"
        for entry in workflow["jobs"]:
            if isinstance(entry, dict):
                options = next(iter(entry.values())) or {}
                assert "filters" not in options, f"filtre de branche sur {next(iter(entry))}"


def test_jobs_match_the_checks_required_on_main() -> None:
    """Un job renommé laisserait un contrôle exigé en attente pour toujours."""
    workflow_names: set[str] = set()
    for workflow in _config()["workflows"].values():
        for entry in workflow["jobs"]:
            if isinstance(entry, str):
                workflow_names.add(entry)
                continue
            job, options = next(iter(entry.items()))
            name = options.get("name", job)
            versions = options.get("matrix", {}).get("parameters", {}).get("python", [])
            if versions:
                workflow_names |= {re.sub(r"<<[^>]*>>", v, name) for v in versions}
            else:
                workflow_names.add(name)
    ruleset = json.loads(RULESET.read_text("utf-8"))
    required = {
        check["context"].removeprefix("ci/circleci: ")
        for rule in ruleset["rules"]
        if rule["type"] == "required_status_checks"
        for check in rule["parameters"]["required_status_checks"]
    }
    assert required == workflow_names
