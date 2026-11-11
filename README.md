# Gotcha

[![CircleCI](https://dl.circleci.com/status-badge/img/gh/abdlaziz221/gotcha/tree/main.svg?style=shield)](https://dl.circleci.com/status-badge/redirect/gh/abdlaziz221/gotcha/tree/main)

> Ce que les devs ont déjà résolu sur le paiement et le déploiement en Afrique, sourcé, avec son niveau de confiance, et lisible par leurs agents.

Gotcha est la mémoire opérationnelle du paiement mobile (**Wave, Orange Money, MTN MoMo, M-Pesa**) et du déploiement sur **Datacloud**. Quand un développeur résout un problème difficile avec son agent, celui-ci prépare un résumé. Le développeur l'approuve, un relecteur le vérifie et le publie, puis les agents suivants le retrouvent par un serveur MCP et confirment, preuve à l'appui, s'il marche encore. Gotcha ne prétend pas avoir toutes les réponses : il permet de ne plus perdre les solutions que les développeurs découvrent.

**Les développeurs partagent. Les agents retrouvent. L'expérience reste.**

Projet de l'équipe pour le concours **CADEV 2026** (Systalink). Gel des fonctions le **10 novembre**, soumission le **14 novembre**, date limite le **15 novembre à 17 h GMT**.

---

## Priorités jusqu'à la soumission

Le positionnement et l'architecture ne changent plus ([D29](docs/DECISIONS.md)). Ce qui compte maintenant, c'est la qualité de la livraison.

| Ordre | Priorité | Ce qu'il faut faire | Niveau |
| --- | --- | --- | --- |
| 1 | Relectures et fusion des PR | Dans l'ordre : 43, 45, 47, 49 à 54, puis 44, 46 et 48 | Bloquant |
| 2 | Recevabilité | Droits, origine du code, licences, comptes Datacloud, inscription de l'équipe | Bloquant |
| 3 | Déploiement | HTTPS, PostgreSQL, persistance, accès public | Bloquant |
| 4 | Contenu | Au moins 15 pièges relus et publiés, avec leur vrai niveau de confiance | Important |
| 5 | Démonstration | Wave sans puis avec Gotcha, panne en direct, courte séquence en wolof | Important |
| 6 | Audio en wolof | 3 à 5 explications audio, seulement si le socle est en ligne le 8 novembre | Conditionnel |

Le détail est dans [docs/PLAN.md](docs/PLAN.md).

## Comment le projet est jugé

1. **Vote des pairs, éliminatoire (15 et 16 novembre) :** chaque membre reçoit jusqu'à 10 projets de son pays et vote pour un seul. Les 3 projets les plus votés de chaque pays sont retenus. Si un seul d'entre nous ne vote pas, le projet est exclu.
2. **Note finale (annexe 1 du règlement) :**

| Critère | Évaluateur | Poids |
| --- | --- | --- |
| Qualité technique : architecture, robustesse, sécurité, code, maîtrise par l'équipe, licences | Jury | 30 % |
| Pertinence et utilité au regard du sujet | Jury | 25 % |
| Expérience utilisateur et ergonomie | Jury | 20 % |
| Innovation et originalité | Jury | 15 % |
| Vote du public | Public | 10 % au plus |

Datacloud est une condition de recevabilité, pas un critère de notation. Le jury note aussi notre capacité à expliquer toute la solution, y compris les parties produites à l'aide de l'IA. La liste de contrôle est dans [docs/SUBMISSION.md](docs/SUBMISSION.md).

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

| Qui | Responsabilité | Dossiers dont il est responsable |
| --- | --- | --- |
| **Abdoul Aziz** | Full-Stack : backend, DevOps, intégration | `app/stores/`, `app/services/` (fiches, contributions), `app/web/routes/`, `app/security/`, `migrations/`, `deploy/`, `scripts/` |
| **Loum** | Frontend et design | `app/web/templates/`, `app/web/static/` |
| **Khalifa** | Ingénieur IA | `app/mcp/`, `app/ingest/`, `app/services/status.py` et `incidents.py`, `app/security/secrets.py` |
| **Les trois** | Contenu et contrats | `content/`, `app/domain/`, `docs/` |

Le détail des tâches, jour par jour, est dans [docs/PLAN.md](docs/PLAN.md). Chaque dossier a son `README.md` : ce qu'il contient, les tâches, comment les faire et comment avancer sans attendre les autres.

**Chacun pousse son travail sous son propre compte** et participe aux relectures et aux tests. On garde aussi la trace de ce qui n'est pas du code : maquettes, tests, documentation, enregistrements, relectures. Les rôles déclarés dans le formulaire sont écrits d'après le travail réellement fait ([D28](docs/DECISIONS.md)).

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

## Ce qui est public

| Quoi | Accès |
| --- | --- |
| Fiche Datacloud | Entière, sans compte |
| Fiche Wave | Entière, sans compte et en lecture seule, pendant la compétition ([D27](docs/DECISIONS.md), tâche A18) |
| Autres fiches | Aperçu public |
| Serveur MCP | Connexion GitHub obligatoire |
| Contributions, confirmations, signalements | Connexion GitHub obligatoire |

---

## Règles non négociables

- **Licences permissives uniquement** (MIT, BSD, Apache, ISC, PSF). Jamais GPL, LGPL, AGPL ni MPL : le projet serait irrecevable. Ni `requests`, ni `httpx`, ni `psycopg`. Vérifier avec `python scripts/check_licenses.py`.
- **Déclarations exactes** : rôles, titularité, composants et usage des outils d'IA. Une déclaration inexacte entraîne la disqualification (article 10 du règlement).
- **Origine du code** : tout élément antérieur au concours est identifié et déclaré (article 6). Un projet existant avant le concours ne peut pas être présenté.
- **Aucun secret dans le dépôt** : ni clé, ni jeton, ni fichier `.env`.
- **Aucun piège inventé, aucune publication sans relecture humaine.** Chaque piège vient d'une source citée ou d'un problème réellement rencontré, et affiche son niveau de confiance. Un agent peut préparer un brouillon, mais son développeur l'approuve et un relecteur le vérifie.
- **Rien de « bientôt disponible »** : ce qui n'est pas fini est retiré de l'interface.
- **Application hébergée à Dakar**, sur Datacloud ; base PostgreSQL chez Render (Francfort), l'offre Datacloud Free n'en ayant pas.

---

## Documentation

| Document | Contenu |
| --- | --- |
| [docs/PLAN.md](docs/PLAN.md) | Calendrier, jalons, tâches de chacun |
| [docs/CONTRACTS.md](docs/CONTRACTS.md) | Les cinq contrats entre les membres |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | Couches, flux, configuration |
| [docs/DECISIONS.md](docs/DECISIONS.md) | Journal des décisions techniques |
| [docs/DEMO.md](docs/DEMO.md) | Scénario de la démo du jury |
| [docs/SUBMISSION.md](docs/SUBMISSION.md) | Dossier de soumission : recevabilité, textes du formulaire, déclarations, jour J |
| [docs/LICENCES.md](docs/LICENCES.md) | Composants et licences à déclarer (généré par `scripts/check_licenses.py --markdown`) |
| [deploy/README.md](deploy/README.md) | Déploiement sur Datacloud |

**Licence** : code sous droits réservés à l'équipe en attendant la décision (voir [docs/DECISIONS.md](docs/DECISIONS.md)). Contributions publiées sur le site : CC BY 4.0.
