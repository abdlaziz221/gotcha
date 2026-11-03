# Composants tiers et licences

Liste à déclarer lors de la soumission (règlement, article 6). Fichier généré par `python scripts/check_licenses.py --markdown` : ne pas le modifier à la main, le regénérer après tout changement de `requirements*.txt`.

Les composants qui ne sont pas des paquets Python (image Docker, base de données, services de CI) sont dans [SUBMISSION.md](SUBMISSION.md).

## Livrés avec l'application (37)

Installés dans l'image de production (Python 3.12 sous Linux) par `requirements.txt`, avec leurs dépendances. Seules les dépendances directes ont une version figée : la CI vérifie à chaque PR les licences d'une installation neuve.

| Composant | Version | Licence |
| --- | --- | --- |
| annotated-doc | 0.0.5 | MIT |
| annotated-types | 0.8.0 | MIT |
| anyio | 4.16.0 | MIT |
| asyncpg | 0.32.0 | Apache-2.0 |
| attrs | 26.1.0 | MIT |
| cffi | 2.1.1 | MIT-0 |
| click | 8.5.0 | BSD-3-Clause |
| cryptography | 50.0.2 | Apache-2.0 OR BSD-3-Clause |
| fastapi | 0.162.0 | MIT |
| h11 | 0.16.0 | MIT License |
| httpcore2 | 2.16.0 | BSD-3-Clause |
| httpx2 | 2.16.0 | BSD-3-Clause |
| idna | 3.20 | BSD-3-Clause |
| jinja2 | 3.1.6 | BSD License |
| jsonschema | 4.26.0 | MIT |
| jsonschema-specifications | 2025.9.1 | MIT |
| markdown-it-py | 4.2.0 | MIT License |
| markupsafe | 3.0.4 | BSD-3-Clause |
| mcp | 2.3.0 | MIT License |
| mcp-types | 2.3.0 | MIT License |
| mdurl | 0.1.2 | MIT License |
| nh3 | 0.3.7 | MIT |
| opentelemetry-api | 1.45.2 | Apache-2.0 |
| pycparser | 3.12 | BSD-3-Clause |
| pydantic | 2.14.2 | MIT |
| pydantic_core | 2.50.2 | MIT |
| pyjwt | 2.15.1 | MIT |
| python-multipart | 0.0.33 | Apache-2.0 |
| pyyaml | 6.0.3 | MIT License |
| referencing | 0.37.0 | MIT |
| rpds-py | 2026.9.1 | MIT |
| sse-starlette | 3.6.0 | BSD-3-Clause |
| starlette | 1.10.0 | BSD-3-Clause |
| truststore | 0.10.5 | MIT |
| typing-inspection | 0.4.4 | MIT |
| typing_extensions | 4.16.0 | PSF-2.0 |
| uvicorn | 0.54.0 | BSD-3-Clause |

## Outils de développement et de CI, jamais livrés (20)

Autres paquets du poste qui a généré ce fichier : outils de `requirements-dev.txt` (tests, lint, types, crochets Git) et dépendances propres à Windows.

| Composant | Version | Licence |
| --- | --- | --- |
| cfgv | 3.5.0 | MIT |
| colorama | 0.4.6 | BSD License |
| coverage | 7.17.0 | Apache-2.0 |
| distlib | 0.4.4 | Python Software Foundation License |
| filelock | 4.2.6 | MIT |
| identify | 2.6.20 | MIT |
| iniconfig | 2.3.1 | MIT |
| nodeenv | 1.12.0 | BSD License |
| packaging | 26.3 | Apache-2.0 OR BSD-2-Clause |
| platformdirs | 4.14.3 | MIT |
| pluggy | 1.7.0 | MIT License |
| pre_commit | 4.7.0 | MIT |
| pygments | 2.21.0 | BSD-2-Clause |
| pyright | 1.1.414 | MIT |
| pytest | 9.2.0 | MIT |
| pytest-cov | 7.1.0 | MIT |
| python-discovery | 1.9.0 | MIT |
| pywin32 | 312 | Python Software Foundation License |
| ruff | 0.17.3 | MIT |
| virtualenv | 21.15.2 | MIT |
