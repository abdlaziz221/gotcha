"""Lance en local exactement les contrôles de la CI : python scripts/check.py

Options :
  --fix    corrige d'abord ce qui peut l'être (ruff check --fix, ruff format)
  --quick  saute les tests (pour une vérification rapide avant un commit)
"""

from __future__ import annotations

import subprocess
import sys
import time

PY = sys.executable


def steps(*, quick: bool) -> list[tuple[str, list[str]]]:
    checks = [
        ("Lint (ruff)", [PY, "-m", "ruff", "check", "."]),
        ("Format (ruff)", [PY, "-m", "ruff", "format", "--check", "."]),
        ("Types (pyright)", [PY, "-m", "pyright", "--pythonpath", PY]),
        ("Secrets", [PY, "scripts/scan_secrets.py"]),
        ("Licences", [PY, "scripts/check_licenses.py"]),
    ]
    if not quick:
        checks.append(("Tests et couverture", [PY, "-m", "pytest", "--cov"]))
    return checks


def main(argv: list[str]) -> int:
    if "--fix" in argv:
        subprocess.run([PY, "-m", "ruff", "check", "--fix", "."], check=False)
        subprocess.run([PY, "-m", "ruff", "format", "."], check=False)

    results = []
    for name, command in steps(quick="--quick" in argv):
        print(f"\n=== {name} ===", flush=True)
        start = time.monotonic()
        code = subprocess.run(command, check=False).returncode
        results.append((name, code == 0, time.monotonic() - start))

    print("\n=== Résumé ===")
    for name, ok, seconds in results:
        print(f"{'OK    ' if ok else 'ÉCHEC '} {name} ({seconds:.0f} s)")
    failed = [name for name, ok, _ in results if not ok]
    if failed:
        print(f"\nÀ corriger avant la PR : {', '.join(failed)}")
        return 1
    print("\nTout est vert : la CI devrait passer.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
