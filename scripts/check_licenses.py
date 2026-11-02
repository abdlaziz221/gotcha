"""Contrôle des licences de toutes les dépendances installées.

Règlement CADEV (article 6) : licences permissives seulement (MIT, BSD, Apache…).
Toute licence à réciprocité (GPL, LGPL, AGPL, MPL…) rend le projet irrecevable.

Usage : python scripts/check_licenses.py            (code de sortie 1 en cas de problème)
        python scripts/check_licenses.py --list     (affiche la licence de chaque paquet)
"""

from __future__ import annotations

import re
import sys
from importlib.metadata import Distribution, distributions

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

# Outils d'installation, jamais livrés avec l'application.
IGNORED = {"pip", "setuptools", "wheel"}


def license_text(dist: Distribution) -> str:
    meta = dist.metadata
    parts = [meta.get("License-Expression") or "", (meta.get("License") or "")[:300]]
    parts += [c for c in meta.get_all("Classifier") or [] if c.startswith("License ::")]
    return " | ".join(p.strip() for p in parts if p and p.strip())


def verdict(name: str, text: str) -> str:
    if name in OVERRIDES:
        return "ok (vérifié à la main)"
    if FORBIDDEN.search(text):
        return "INTERDITE"
    if ALLOWED.search(text):
        return "ok"
    return "INCONNUE"


def main(argv: list[str]) -> int:
    problems = []
    for dist in sorted(distributions(), key=lambda d: (d.metadata["Name"] or "").lower()):
        name = (dist.metadata["Name"] or "").lower()
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
