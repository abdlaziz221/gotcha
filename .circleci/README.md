# `.circleci/` : la CI (CircleCI)

**Responsable :** Abdoul Aziz. **Relecteur :** Khalifa.

La CI du projet tourne sur **CircleCI**, plan gratuit : 30 000 crédits par mois, soit environ 3 000 minutes de build, largement assez pour l'équipe. CircleCI tourne sur ses propres serveurs et publie ses résultats sur chaque PR GitHub. GitHub Actions n'est pas utilisé : le compte propriétaire du dépôt est bloqué par GitHub (voir la décision D16 dans [`../docs/DECISIONS.md`](../docs/DECISIONS.md)).

## Les contrôles

`config.yml` lance huit jobs à chaque push. Chacun publie sur la PR un statut `ci/circleci: <job>`, et **tous sont obligatoires** pour fusionner dans `main` ([`../.github/rulesets/`](../.github/rulesets/README.md)).

| Job CircleCI | Ce qu'il vérifie |
| --- | --- |
| `pr-rules` | Titre de PR au format `type(zone): description` (bloquant : il devient le message du commit fusionné) ; taille et nom de branche (avertissements). Script : `scripts/ci_pr_rules.py` |
| `lint` | `ruff check` (22 familles de règles, dont sécurité et imports interdits pour raison de licence), `ruff format`, `pyright` (types), `scripts/scan_secrets.py` (aucune clé dans le dépôt) |
| `tests-py3.11`, `tests-py3.12`, `tests-py3.13` | `pytest` sur trois versions de Python, avec **au moins 85 % de couverture** (branches comprises) : tests d'architecture, de contrat **sur les deux stockages** (une base PostgreSQL 17 jetable par job), de contenu, de sécurité, liens morts… Résultats détaillés dans l'onglet *Tests* de CircleCI |
| `licences` | Dans un environnement neuf contenant seulement `requirements.txt` : aucune licence GPL, LGPL, AGPL ni MPL |
| `docker` | L'image se construit et démarre en **mode production** ; l'accueil répond, `/styleguide` et `/relecture` sont fermés, les en-têtes de sécurité sont présents, le serveur MCP répond |
| `audit` | `pip-audit` : aucune faille connue dans les dépendances |

## Avant d'ouvrir une PR

```bash
python scripts/check.py
```

Ce script lance les mêmes contrôles en local (sur votre version de Python, sans Docker). `--fix` corrige d'abord le style, `--quick` saute les tests.

Les hooks pre-commit (`.pre-commit-config.yaml`) font les vérifications rapides à chaque commit, et lancent les tests avant chaque push :

```bash
python -m pre_commit install --hook-type pre-commit --hook-type pre-push
```

**Windows :** si un outil est bloqué (« Application Control policy » ou « Permission denied »), c'est Smart App Control qui refuse son lanceur `.exe`. Lancer l'outil avec `python -m` : `python -m pyright`, `python -m pre_commit`, `python -m pytest`.

## Lire un échec

1. Sur la PR, cliquer sur **Details** à côté du statut `ci/circleci: …` en rouge : la page du job s'ouvre sur CircleCI.
2. Déplier l'étape en échec ; pour les tests, l'onglet *Tests* liste les tests cassés.
3. Corriger en local, relancer `python scripts/check.py`, pousser : la CI repart toute seule.

## Modifier la CI

- Une PR qui touche à `.circleci/` est relue par Abdoul Aziz et Khalifa.
- Ajouter, renommer ou supprimer un job change la liste des statuts : mettre à jour `../.github/rulesets/protection-main.json` et réappliquer la règle dans la même PR, sinon plus rien ne peut être fusionné.
- La syntaxe `<< … >>` est réservée aux paramètres CircleCI : ne pas l'utiliser dans une commande (pas de heredoc), mettre le code dans un script de `scripts/`.
- Les anciens workflows GitHub Actions ont été retirés le 2 novembre 2026. Pour les retrouver, si le compte GitHub est un jour débloqué : `git show 3fc9c27:.github/workflows/ci.yml`.

## Brancher CircleCI sur un nouveau dépôt (déjà fait pour celui-ci)

1. <https://circleci.com/signup>, **Sign up with GitHub**, autoriser l'accès au dépôt.
2. **Projects**, puis **Create Project** : choisir le dépôt et le fichier existant `.circleci/config.yml` (pas l'option « Faster », qui crée une configuration générique).
3. *Project Settings → Advanced* : laisser **Pass secrets to builds from forked pull requests** désactivé.

## Consommation

Les jobs légers tournent sur la petite machine (`small`, 5 crédits par minute), le job `docker` sur une machine Linux complète (10 crédits par minute). Un passage complet coûte environ 100 crédits : environ 300 passages par mois. Suivi dans CircleCI, *Plan → Usage*.
