"""Contrôle des licences de toutes les dépendances installées.

Règlement CADEV (article 6) : licences permissives seulement (MIT, BSD, Apache…).
Toute licence à réciprocité (GPL, LGPL, AGPL, MPL…) rend le projet irrecevable.

Usage : python scripts/check_licenses.py            (code de sortie 1 en cas de problème)
        python scripts/check_licenses.py --list     (affiche la licence de chaque paquet)
        python scripts/check_licenses.py --markdown (écrit docs/LICENCES.md, la liste à déclarer)
"""

from __future__ import annotations

import re
import sys
from importlib.metadata import Distribution, PackageNotFoundError, distributions, requires
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MARKDOWN_FILE = ROOT / "docs" / "LICENCES.md"

FORBIDDEN = re.compile(
    r"\b(?:A|L)?GPL|\bGNU\b|General Public License|\bMPL\b|Mozilla Public|\bEPL\b|"
    r"\bEUPL\b|\bCDDL\b|\bSSPL\b|\bOSL\b|Commons Clause|Business Source",
    re.IGNORECASE,
)
ALLOWED = re.compile(
    r"\bMIT\b|\bBSD\b|Apache|\bISC\b|\bPSF\b|Python Software Foundation|"
    r"Unlicense|\b0BSD\b|\bZlib\b|CC0",
    re.IGNORECASE,
)

# Paquets vérifiés à la main dont les métadonnées sont ambiguës : nom -> justification.
OVERRIDES: dict[str, str] = {}

# Outils d'installation : le Dockerfile les retire de l'image après l'installation (pip
# embarque certifi, sous MPL-2.0), ils ne sont donc jamais livrés.
IGNORED = {"pip", "setuptools", "wheel"}


def _field(dist: Distribution, key: str) -> list[str]:
    """Valeur(s) d'un champ de métadonnées (clés de PackageMetadata.json : license, classifier…)."""
    value = dist.metadata.json.get(key, [])
    return [value] if isinstance(value, str) else list(value)


def dist_name(dist: Distribution) -> str:
    names = _field(dist, "name")
    return names[0].lower() if names else ""


def canonical(name: str) -> str:
    """Nom normalisé (PEP 503) : « Pre_Commit » et « pre-commit » désignent le même paquet."""
    return re.sub(r"[-_.]+", "-", name).lower()


def license_text(dist: Distribution) -> str:
    parts = _field(dist, "license_expression") + [v[:300] for v in _field(dist, "license")]
    parts += [c for c in _field(dist, "classifier") if c.startswith("License ::")]
    return " | ".join(p.strip() for p in parts if p.strip())


def short_license(dist: Distribution) -> str:
    """Licence en quelques mots, pour un tableau : expression SPDX, sinon classifieurs."""
    expression = _field(dist, "license_expression")
    if expression:
        return expression[0].strip()
    classifiers = [
        c.split("::")[-1].strip() for c in _field(dist, "classifier") if c.startswith("License ::")
    ]
    if classifiers:
        return ", ".join(classifiers)
    declared = [v.strip().splitlines()[0] for v in _field(dist, "license") if v.strip()]
    return declared[0][:80] if declared else "aucune information"


def verdict(name: str, text: str) -> str:
    if name in OVERRIDES:
        return "ok (vérifié à la main)"
    if FORBIDDEN.search(text):
        return "INTERDITE"
    if ALLOWED.search(text):
        return "ok"
    return "INCONNUE"


def production_environment() -> dict[str, str]:
    """Environnement de l'image de production (Dockerfile) : Linux et sa version de Python.

    Une dépendance réservée à Windows ou à une autre version de Python n'y est pas installée.
    """
    match = re.search(r"^FROM python:(\d+\.\d+)", (ROOT / "Dockerfile").read_text("utf-8"), re.M)
    version = match.group(1) if match else f"{sys.version_info[0]}.{sys.version_info[1]}"
    return {
        "python_version": version,
        "python_full_version": f"{version}.0",
        "sys_platform": "linux",
        "platform_system": "Linux",
        "os_name": "posix",
        "extra": "",
    }


def shipped() -> set[str]:
    """Paquets que l'image installe : requirements.txt et toutes leurs dépendances."""
    return _closure(ROOT / "requirements.txt", production_environment())


def dev_tools() -> set[str]:
    """Outils de requirements-dev.txt et leurs dépendances, sur ce système, hors livrés."""
    # packaging : outil de développement (requirements-dev.txt), jamais livré.
    from packaging.markers import default_environment

    environment = {key: str(value) for key, value in default_environment().items()}
    return _closure(ROOT / "requirements-dev.txt", environment) - shipped()


def _closure(requirements_file: Path, environment: dict[str, str]) -> set[str]:
    """Les paquets d'un fichier requirements et toutes leurs dépendances, pour un système."""
    from packaging.requirements import Requirement

    lines = requirements_file.read_text("utf-8").splitlines()
    specs = [line.split("#")[0].strip() for line in lines]
    todo = [Requirement(spec) for spec in specs if spec and not spec.startswith("-")]
    # « -r requirements.txt » : les dépendances de l'application sur ce système (pywin32
    # sous Windows, par exemple) font partie de l'environnement de développement.
    for spec in specs:
        if spec.startswith("-r "):
            included = requirements_file.parent / spec[3:].strip()
            todo += [Requirement(name) for name in _closure(included, environment)]
    # Paquet -> options demandées (« pyjwt[crypto] » ajoute cryptography aux dépendances).
    seen: dict[str, set[str]] = {}
    while todo:
        wanted = todo.pop()
        name = canonical(wanted.name)
        extras = {""} | wanted.extras
        if extras <= seen.get(name, set()):
            continue
        seen.setdefault(name, set()).update(extras)
        try:
            dependencies = requires(name) or []
        except PackageNotFoundError:
            continue
        for spec in dependencies:
            requirement = Requirement(spec)
            marker = requirement.marker
            if marker is None or any(
                marker.evaluate({**environment, "extra": extra}) for extra in extras
            ):
                todo.append(requirement)
    return set(seen)


def _table(rows: list[tuple[str, str, str]]) -> list[str]:
    lines = ["| Composant | Version | Licence |", "| --- | --- | --- |"]
    lines += [f"| {name} | {version} | {licence} |" for name, version, licence in rows]
    return lines


def markdown() -> str:
    """Liste des composants à déclarer, livrés d'un côté, outils de développement de l'autre."""
    delivered = shipped()
    tools = dev_tools()
    groups: dict[bool, list[tuple[str, str, str]]] = {True: [], False: []}
    installed: set[str] = set()
    strangers: list[str] = []
    for dist in sorted(distributions(), key=dist_name):
        name = dist_name(dist)
        if not name or name in IGNORED or canonical(name) in installed:
            continue
        installed.add(canonical(name))
        licence = short_license(dist).replace("|", "/")
        if canonical(name) in delivered:
            groups[True].append((name, dist.version, licence))
        elif canonical(name) in tools:
            groups[False].append((name, dist.version, licence))
        else:
            strangers.append(name)  # oublié dans le venv ou installé à part : hors du projet
    if strangers:
        print(
            "Non listés (ni livrés ni dans requirements-dev.txt) : " + ", ".join(strangers),
            file=sys.stderr,
        )
    missing = sorted(delivered - installed)
    python = production_environment()["python_version"]
    lines = [
        "# Composants tiers et licences",
        "",
        "Liste à déclarer lors de la soumission (règlement, article 6). Fichier généré par "
        "`python scripts/check_licenses.py --markdown` : ne pas le modifier à la main. "
        "**La liste de référence est celle du job `licences` de la CI** (artefact "
        "`LICENCES.md`, générée dans une installation Linux neuve) : seules les dépendances "
        "directes ont une version figée, et une génération depuis un poste peut donner "
        "d'autres versions de dépendances indirectes. Avant la soumission, recopier "
        "l'artefact du dernier passage sur `main`.",
        "",
        "Les composants qui ne sont pas des paquets Python (image Docker, base de données, "
        "services de CI) sont dans [SUBMISSION.md](SUBMISSION.md).",
        "",
        f"## Livrés avec l'application ({len(groups[True])})",
        "",
        f"Installés dans l'image de production (Python {python} sous Linux) par "
        "`requirements.txt`, avec leurs dépendances. pip, setuptools et wheel en sont retirés "
        "après l'installation (Dockerfile).",
        "",
        *_table(groups[True]),
    ]
    if missing:
        lines += [
            "",
            "Non installés sur le poste qui a généré ce fichier, licence à vérifier : "
            + ", ".join(f"`{name}`" for name in missing)
            + ".",
        ]
    lines += [
        "",
        f"## Outils de développement et de CI, jamais livrés ({len(groups[False])})",
        "",
        "Outils de `requirements-dev.txt` (tests, lint, types, crochets Git) et leurs "
        f"dépendances, sur le système qui a généré ce fichier ({sys.platform}).",
        "",
        *_table(groups[False]),
        "",
    ]
    return "\n".join(lines)


def main(argv: list[str]) -> int:
    if "--markdown" in argv:
        MARKDOWN_FILE.write_text(markdown(), encoding="utf-8", newline="\n")
        print(f"Liste écrite dans {MARKDOWN_FILE.relative_to(ROOT).as_posix()}.")
    problems = []
    for dist in sorted(distributions(), key=dist_name):
        name = dist_name(dist)
        if not name or name in IGNORED:
            continue
        text = license_text(dist)
        result = verdict(name, text)
        if "--list" in argv or not result.startswith("ok"):
            print(f"{result:<24} {name} {dist.version} : {text or 'aucune information'}")
        if not result.startswith("ok"):
            problems.append(name)
    if problems:
        print(f"\n{len(problems)} paquet(s) à corriger : {', '.join(problems)}")
        print("Remplacez-les, ou vérifiez la licence à la main et ajoutez-les à OVERRIDES.")
        return 1
    print("Toutes les licences sont permissives.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
