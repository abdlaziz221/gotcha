# Gotcha

[![CircleCI](https://dl.circleci.com/status-badge/img/gh/abdlaziz221/gotcha/tree/main.svg?style=shield)](https://dl.circleci.com/status-badge/redirect/gh/abdlaziz221/gotcha/tree/main)

> Les pièges du paiement et du déploiement en Afrique que personne ne documente.

Gotcha est le carnet de terrain partagé des intégrations **Wave, Orange Money, MTN MoMo, M-Pesa** et du déploiement sur **Datacloud** : ce que la documentation ne dit pas, confirmé par les devs qui l'ont vécu, et lisible par leurs agents IA grâce à un serveur MCP.

Projet de l'équipe pour le concours **CADEV 2026** (Systalink). Gel des fonctions le **10 novembre**, soumission le **14 novembre**.

---

## Démarrer en deux minutes

Prérequis : Python 3.11 ou plus récent, et Git.

```bash
python -m venv .venv
```

Activer l'environnement : `source .venv/bin/activate` (Linux, macOS), `source .venv/Scripts/activate` (Git Bash), `.venv\Scripts\Activate.ps1` (PowerShell).

```bash
pip install -r requirements-dev.txt
```

```bash
python -m pre_commit install --hook-type pre-commit --hook-type pre-push
```

```bash
python -m uvicorn app.main:app --reload
```

Ouvrir <http://localhost:8000>. **Aucune base de données à installer** : en développement, l'application lit les fiches dans `content/` et les fausses données dans `fixtures/` (stockage « memory »).

Pages utiles en développement : `/styleguide` (tous les composants), `/relecture` (file de relecture), `/healthz` (santé).

Avant chaque PR, lancer les mêmes contrôles que la CI (lint, types, secrets, licences, tests et couverture) :

```bash
python scripts/check.py
```

---

## Qui fait quoi

| Qui | Rôle déclaré | Dossiers dont il est responsable |
| --- | --- | --- |
| **Abdoul Aziz** | Full-Stack : backend, DevOps, intégration | `app/stores/`, `app/services/` (fiches, contributions), `app/web/routes/`, `app/security/`, `migrations/`, `deploy/`, `scripts/` |
| **Loum** | Frontend et design | `app/web/templates/`, `app/web/static/` |
| **Khalifa** | Ingénieur IA | `app/mcp/`, `app/ingest/`, `app/services/status.py` et `incidents.py`, `app/security/secrets.py` |
| **Les trois** | Contenu et contrats | `content/`, `app/domain/`, `docs/` |

Le détail des tâches, jour par jour, est dans [docs/PLAN.md](docs/PLAN.md). Chaque dossier a son `README.md` : ce qu'il contient, les tâches, comment les faire et comment avancer sans attendre les autres.

---

## Plan du dépôt

```
app/
├── domain/        CONTRATS : modèle de données, ports de stockage, erreurs (les trois)
├── services/      Logique métier : fiches, contributions, état des services
├── stores/        Stockage : memory (fichiers, pour développer) et postgres (production)
├── web/           Site : routes, contextes de pages, gabarits Jinja2, CSS
├── mcp/           Serveur MCP pour les agents IA
├── ingest/        Import du flux de pannes Flutterwave
├── security/      En-têtes, CSRF, quotas, relecteurs, détection des secrets
├── config.py      Variables d'environnement
├── container.py   Assemblage : choisit le stockage, construit les services
└── main.py        Point d'entrée (uvicorn app.main:app)
content/           Fiches, pièges et glossaire, en Markdown et YAML
fixtures/          Fausses données de développement (pannes, contributions)
migrations/        Schéma PostgreSQL versionné
scripts/           Licences, migrations, chargement du contenu, mots de passe
tests/             Tests automatisés (pytest)
deploy/            Déploiement sur Datacloud
docs/              Plan, contrats, architecture, décisions, démo, soumission
```

---

## Comment on travaille

1. **Contrats d'abord.** Le modèle de données, les ports de stockage, les contextes de pages et les outils MCP sont fixés dans [docs/CONTRACTS.md](docs/CONTRACTS.md). On les respecte ; on les change seulement à trois.
2. **Fausses données ensuite.** Tout le monde travaille sur le stockage « memory » : personne n'attend la base, le backend ni le design des autres.
3. **Branchements à la fin.** Le passage à PostgreSQL se fait en changeant une variable : `GOTCHA_STORE=postgres`. Les tests de contrat garantissent que les deux stockages se comportent pareil.

Branches, commits, relectures et définition de « terminé » : [CONTRIBUTING.md](CONTRIBUTING.md).

---

## Règles non négociables

- **Licences permissives uniquement** (MIT, BSD, Apache, ISC, PSF). Jamais GPL, LGPL, AGPL ni MPL : le projet serait irrecevable. Ni `requests`, ni `httpx`, ni `psycopg`. Vérifier avec `python scripts/check_licenses.py`.
- **Aucun secret dans le dépôt** : ni clé, ni jeton, ni fichier `.env`.
- **Aucun piège publié sans source et sans relecture humaine.** Pas de fiche inventée ni générée automatiquement.
- **Rien de « bientôt disponible »** : ce qui n'est pas fini est retiré de l'interface.
- **Données hébergées à Dakar**, sur Datacloud.

---

## Documentation

| Document | Contenu |
| --- | --- |
| [docs/PLAN.md](docs/PLAN.md) | Calendrier, jalons, tâches de chacun |
| [docs/CONTRACTS.md](docs/CONTRACTS.md) | Les cinq contrats entre les membres |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | Couches, flux, configuration |
| [docs/DECISIONS.md](docs/DECISIONS.md) | Journal des décisions techniques |
| [docs/DEMO.md](docs/DEMO.md) | Scénario de la démo du jury |
| [docs/SUBMISSION.md](docs/SUBMISSION.md) | Liste de contrôle de la soumission |
| [deploy/README.md](deploy/README.md) | Déploiement sur Datacloud |

**Licence** : code sous droits réservés à l'équipe en attendant la décision (voir [docs/DECISIONS.md](docs/DECISIONS.md)). Contributions publiées sur le site : CC BY 4.0.
