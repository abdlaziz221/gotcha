# `.circleci/` : la CI active (CircleCI)

**Responsable :** Abdoul Aziz. **Relecteur :** Khalifa.

GitHub Actions ne peut pas tourner tant que le compte GitHub propriétaire du dépôt est bloqué (voir [`../.github/workflows/README.md`](../.github/workflows/README.md)). La CI passe donc par **CircleCI**, plan gratuit : 30 000 crédits par mois, soit environ 3 000 minutes de build, largement assez pour l'équipe. CircleCI tourne sur ses propres serveurs et publie ses résultats sur chaque PR GitHub.

`config.yml` fait **exactement les mêmes contrôles** que les workflows GitHub :

| Job CircleCI | Ce qu'il vérifie |
| --- | --- |
| `pr-rules` | Titre de PR au format `type(zone): description` (bloquant) ; taille et nom de branche (avertissements). Script commun : `scripts/ci_pr_rules.py` |
| `lint` | `ruff check`, `ruff format`, `pyright`, `scripts/scan_secrets.py` |
| `tests-py3.11`, `tests-py3.12`, `tests-py3.13` | `pytest` sur trois versions de Python, au moins 85 % de couverture ; résultats visibles dans l'onglet *Tests* de CircleCI |
| `licences` | Licences des dépendances de `requirements.txt`, dans un environnement neuf |
| `docker` | L'image se construit et démarre en mode production ; accueil, pages cachées, en-têtes de sécurité, serveur MCP |
| `audit` | `pip-audit` : aucune faille connue dans les dépendances |

## Brancher CircleCI (une fois, par le propriétaire du dépôt)

1. Aller sur <https://circleci.com/signup> et choisir **Sign up with GitHub** (compte gratuit).
2. Autoriser CircleCI à accéder au dépôt `abdlaziz221/gotcha`.
3. Dans CircleCI : **Projects**, puis **Set up project** en face de `gotcha`. Choisir **utiliser le `.circleci/config.yml` du dépôt** et indiquer la branche qui le contient (`aziz/ci-qualite` tant que la PR n'est pas fusionnée, ensuite `main`).
4. Dans les réglages du projet (*Project Settings → Advanced*) : activer **Build forked pull requests** seulement si on accepte des contributions externes, et laisser **Pass secrets to builds from forked pull requests** désactivé.

Ensuite, chaque push sur une branche qui a une PR ouverte lance la CI, et les résultats apparaissent sur la PR.

## Contrôles obligatoires sur `main`

Les huit jobs publient sur chaque PR un statut `ci/circleci: <job>` (`ci/circleci: lint`, `ci/circleci: tests-py3.12`…). **Tous les huit sont obligatoires** pour fusionner dans `main` : ils sont listés dans [`../.github/rulesets/protection-main.json`](../.github/rulesets/protection-main.json), appliqué sur GitHub (commande dans `.github/workflows/README.md`).

Renommer ou ajouter un job demande donc de mettre à jour ce fichier **et** de réappliquer la règle dans la même PR, sinon plus rien ne peut être fusionné.

## Consommation

Les jobs légers tournent sur la petite machine (`small`, 5 crédits par minute), le job `docker` sur une machine Linux complète (10 crédits par minute). Un passage complet coûte environ 100 crédits : environ 300 passages par mois. Suivi dans CircleCI, *Plan → Usage*.

## Modifier la CI

Toute modification se fait **dans les deux fichiers** : `.circleci/config.yml` (actif) et `.github/workflows/ci.yml` (prêt pour le jour où GitHub Actions sera débloqué). La syntaxe `<< … >>` est réservée aux paramètres CircleCI : ne pas l'utiliser dans une commande (pas de heredoc), mettre le code dans un script de `scripts/`.
