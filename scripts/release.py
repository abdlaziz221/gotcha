"""Prépare la base avant le démarrage du site : migrations, puis chargement de content/.

Usage : python scripts/release.py (lancé par le Dockerfile avant uvicorn).
Avec le stockage mémoire (GOTCHA_STORE=memory), il n'y a rien à préparer.
Sans danger si plusieurs instances démarrent ensemble : un verrou PostgreSQL les met en file.
Le fichier BUILD_TIME (écrit dans l'image par le Dockerfile) empêche une image plus
ancienne de remettre son contenu en ligne.
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.config import Settings  # noqa: E402
from app.stores.postgres.release import release  # noqa: E402


def build_time(path: Path = ROOT / "BUILD_TIME") -> int | None:
    """Date de construction de l'image (secondes Unix), ou None hors image Docker."""
    try:
        return int(path.read_text(encoding="utf-8").strip())
    except (OSError, ValueError):
        return None


async def main() -> None:
    settings = Settings.from_env()
    if settings.store != "postgres" or not settings.database_url:
        print("Stockage mémoire : aucune base à préparer.")
        return
    report = await release(
        settings.database_url,
        migrations_dir=ROOT / "migrations",
        content_dir=settings.content_dir,
        built_at=build_time(),
    )
    migrations = ", ".join(report.migrations) if report.migrations else "aucune, la base est à jour"
    print(f"Migrations appliquées : {migrations}")
    seed = report.seed
    if seed is None:
        print(
            "Contenu non rechargé : une image plus récente est déjà en service"
            f" (construite le {report.newer_build}, celle-ci le {build_time()})."
        )
        return
    print(f"{seed.fiches} fiche(s), {seed.gotchas} piège(s), {seed.terms} terme(s) chargés.")
    if seed.retired:
        print("Repassées en brouillon (absentes de content/) : " + ", ".join(seed.retired))


if __name__ == "__main__":
    asyncio.run(main())
