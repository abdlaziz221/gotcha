"""Génère l'empreinte du mot de passe d'un relecteur, pour GOTCHA_REVIEWERS.

Usage : python scripts/hash_password.py aziz
        (le mot de passe est demandé sans être affiché)
Résultat à ajouter à GOTCHA_REVIEWERS, séparé des autres relecteurs par « ; ».
"""

from __future__ import annotations

import getpass
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.security.auth import hash_password


def main() -> None:
    if len(sys.argv) != 2:
        sys.exit("Usage : python scripts/hash_password.py <pseudo>")
    pseudo = sys.argv[1]
    password = getpass.getpass(f"Mot de passe de {pseudo} (12 caractères au moins) : ")
    if len(password) < 12:
        sys.exit("Mot de passe trop court.")
    if getpass.getpass("Confirmez : ") != password:
        sys.exit("Les deux saisies diffèrent.")
    print(f"{pseudo}:{hash_password(password)}")


if __name__ == "__main__":
    main()
