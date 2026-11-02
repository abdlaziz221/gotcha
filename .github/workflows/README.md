# `.github/workflows/` : la CI et ses règles

**Responsable :** Abdoul Aziz. **Relecteur :** Khalifa.

Dépôt public : GitHub Actions est **gratuit et illimité**. Toute PR vers `main` passe par ces contrôles ; une PR qui échoue ne peut pas être fusionnée.

> **État au 2 novembre 2026 : la CI ne démarre pas.** GitHub refuse de lancer les jobs (« your account is locked due to a billing issue ») tant que la facturation du compte propriétaire du dépôt n'est pas réglée. En attendant :
>
> - chacun lance `python scripts/check.py` avant d'ouvrir une PR et **colle le résumé dans la PR** ;
> - la règle de `main` impose déjà la PR et l'approbation, mais **pas encore** les contrôles de la CI (sinon plus rien ne pourrait être fusionné).
>
> Dès que la CI tourne : relancer les jobs de la dernière PR, vérifier qu'ils passent, puis appliquer la règle complète (section « Les règles de `main` »).

## Les workflows

### `ci.yml` : à chaque PR et à chaque fusion dans `main` (obligatoire)

| Contrôle (nom affiché sur la PR) | Ce qu'il vérifie | Bloquant |
| --- | --- | --- |
| **Règles de PR** | Titre au format `type(zone): description` (il devient le message du commit fusionné) | Oui |
| | Taille de la PR (plus de 400 lignes) et nom de branche `prénom/tâche-sujet` | Avertissement |
| **Lint, types et secrets** | `ruff check` (22 familles de règles, dont sécurité et imports interdits), `ruff format`, `pyright` (types), `scripts/scan_secrets.py` (aucune clé dans le dépôt) | Oui |
| **Tests (Python 3.11, 3.12, 3.13)** | `pytest` sur trois versions de Python, avec **au moins 85 % de couverture** (branches comprises), dont les tests d'architecture, de contrat, de contenu, de sécurité et l'absence de liens morts | Oui |
| **Licences (dépendances livrées)** | Dans un environnement neuf contenant seulement `requirements.txt` : aucune licence GPL, LGPL, AGPL ni MPL | Oui |

### `livraison.yml` : sur `main`, sur les PR qui touchent au code, chaque lundi, et à la demande

| Contrôle | Ce qu'il vérifie |
| --- | --- |
| **Image Docker (construction et démarrage)** | L'image se construit, démarre en **mode production**, l'accueil répond, `/styleguide` et `/relecture` sont fermés, les en-têtes de sécurité sont présents, le serveur MCP répond |
| **Failles connues (pip-audit)** | Aucune dépendance de `requirements.txt` n'a de faille publiée |

Ces contrôles ne sont pas obligatoires pour fusionner (ils ne tournent pas sur toutes les PR), mais un échec sur `main` se corrige **en priorité**.

### `../dependabot.yml`

Chaque lundi, une PR groupée pour les mises à jour mineures des dépendances Python ; chaque mois, une pour les actions GitHub. Elles passent la même CI que les autres.

## Les règles de `main`

Imposées par GitHub (ensemble de règles « Protection de main ») :

- **pas de push direct** : tout passe par une PR ;
- **une approbation** d'un autre membre, et toutes les conversations résolues ;
- une nouvelle modification **annule** l'approbation précédente ;
- les contrôles obligatoires de `ci.yml` doivent être **verts**, sur une branche **à jour** avec `main` ;
- fusion en **squash** uniquement, historique linéaire ;
- pas de suppression ni de réécriture (`force push`) de `main`.

L'administrateur du dépôt peut contourner les règles **pour une PR** seulement, en cas d'urgence (CI en panne côté GitHub, par exemple). Ça ne doit pas arriver en temps normal.

La règle complète est décrite dans [`../rulesets/protection-main.json`](../rulesets/protection-main.json). Pour l'appliquer (ou la réappliquer après un changement), l'administrateur lance :

```bash
gh api repos/abdlaziz221/gotcha/rulesets --jq '.[] | select(.name == "Protection de main") | .id'
```

```bash
gh api -X PUT repos/abdlaziz221/gotcha/rulesets/<id> --input .github/rulesets/protection-main.json
```

## Avant d'ouvrir une PR

```bash
python scripts/check.py
```

Ce script lance exactement les contrôles de `ci.yml` (sans les autres versions de Python). `--fix` corrige d'abord le style, `--quick` saute les tests.

Les hooks pre-commit (voir `.pre-commit-config.yaml`) font les vérifications rapides à chaque commit, et lancent les tests avant chaque push :

```bash
python -m pre_commit install --hook-type pre-commit --hook-type pre-push
```

**Windows :** si un outil est bloqué (« Application Control policy » ou « Permission denied »), c'est Smart App Control qui refuse son lanceur `.exe`. Lancer l'outil avec `python -m` : `python -m pyright`, `python -m pre_commit`, `python -m pytest`.

## Lire un échec

1. Sur la PR, cliquer sur **Details** à côté du contrôle en rouge.
2. Les erreurs de lint et de secrets apparaissent aussi directement dans l'onglet **Files changed**, sur la ligne concernée.
3. Corriger en local, relancer `python scripts/check.py`, pousser : la CI repart toute seule.

## Modifier la CI

- Une PR qui touche à `.github/` est relue par Abdoul Aziz et Khalifa (CODEOWNERS).
- Renommer un contrôle obligatoire (`name:` d'un job) casse la règle de `main` : mettre à jour l'ensemble de règles dans **Settings → Rules** dans la même foulée.
- Les actions utilisées sont uniquement les actions officielles `actions/*`, en version majeure (`@v7`) ; Dependabot les met à jour.
