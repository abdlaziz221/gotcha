"""Cherche des clés et jetons dans les fichiers suivis par git.

Mêmes règles que pour les contributions (app/security/secrets.py).
Usage : python scripts/scan_secrets.py   (code de sortie 1 si un secret est trouvé)

Faux positif assumé : ajouter « secret-scan: ignore » en commentaire sur la ligne,
ou « secret-scan: ignore-file » dans les premières lignes du fichier (tests seulement).
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.security.secrets import scan_text  # noqa: E402

IGNORE_LINE = "secret-scan: ignore"
IGNORE_FILE = "secret-scan: ignore-file"


def tracked_files() -> list[Path]:
    output = subprocess.run(
        ["git", "ls-files", "-z"],  # noqa: S607 (git doit être dans le PATH)
        cwd=ROOT,
        capture_output=True,
        check=True,
    ).stdout
    return [ROOT / name for name in output.decode("utf-8").split("\0") if name]


def main() -> int:
    in_ci = os.environ.get("GITHUB_ACTIONS") == "true"
    found = 0
    for path in tracked_files():
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, FileNotFoundError):
            continue  # fichier binaire ou supprimé
        if IGNORE_FILE in text[:2000]:
            continue
        lines = text.splitlines()
        for finding in scan_text(text):
            line_no = text.count("\n", 0, finding.start) + 1
            if IGNORE_LINE in lines[line_no - 1]:
                continue
            relative = path.relative_to(ROOT).as_posix()
            if in_ci:
                print(f"::error file={relative},line={line_no}::Secret probable : {finding.kind}")
            else:
                print(f"{relative}:{line_no} : secret probable ({finding.kind})")
            found += 1
    if found:
        print(f"\n{found} secret(s) probable(s). Retirez-les et révoquez toute vraie clé exposée.")
        return 1
    print("Aucun secret trouvé.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
