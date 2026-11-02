# Comment on travaille

Ce guide vaut pour les trois membres de l'équipe. Il tient en une règle : **des petites PR, relues vite, qui laissent `main` toujours déployable.**

## Installer son poste (une fois)

```bash
pip install -r requirements-dev.txt
```

```bash
python -m pre_commit install --hook-type pre-commit --hook-type pre-push
```

Les hooks vérifient le style, le format et l'absence de secrets à chaque commit, et lancent les tests avant chaque push. Avant d'ouvrir une PR, `python scripts/check.py` lance exactement les contrôles de la CI.

## Organisation générale

- `main` est la branche de production. Datacloud la déploie à chaque fusion. **Push direct sur `main` impossible** : GitHub l'interdit.
- Une tâche du plan ([docs/PLAN.md](docs/PLAN.md)) correspond à une issue GitHub, une branche et une PR.
- Chacun travaille dans ses dossiers (voir le tableau du [README](README.md)). Pour modifier le dossier d'un autre, on le prévient d'abord, ou on lui laisse la PR.

## Branches

Nom : `<prénom>/<tâche>-<sujet-court>`, par exemple :

```
loum/L3-page-fiche
khalifa/K4-flutterwave-pays
aziz/A3-postgres-fiches
```

Une branche vit **moins d'une journée**. Si la tâche est plus longue, on la découpe et on fusionne les morceaux au fil de l'eau, en masquant ce qui n'est pas fini.

Chaque matin, on récupère `main` :

```bash
git switch main && git pull && git switch - && git rebase main
```

## Commits

Format court, en français, inspiré de Conventional Commits :

```
<type>(<zone>): <ce que fait le commit>
```

- **Types** : `feat` (fonction), `fix` (correction), `content` (fiche, piège, glossaire), `style` (CSS, gabarits sans changement de comportement), `refactor`, `perf`, `test`, `docs`, `chore` (outillage, dépendances), `ci`, `build`, `revert`.
- **Zones** : `domain`, `web`, `ui`, `mcp`, `ingest`, `stores`, `security`, `deploy`, ou le slug d'une fiche.

Exemples : `feat(mcp): outil get_service_status`, `content(mpesa-ke): piège du jeton expiré`, `fix(web): lien mort dans le pied de page`.

Le **titre de la PR** suit le même format (la CI le vérifie) : c'est lui qui devient le message du commit fusionné dans `main`.

## Pull requests

1. Ouvrir la PR **tôt**, en brouillon si besoin, avec le modèle proposé.
2. Une PR fait **moins de 400 lignes** modifiées (hors contenu et fichiers générés).
3. La CI doit être verte (détail dans [.github/workflows/README.md](.github/workflows/README.md)) :
   - **Règles de PR** : titre au bon format ;
   - **Lint, types et secrets** : ruff, pyright, aucune clé dans le dépôt ;
   - **Tests** sur Python 3.11, 3.12 et 3.13, avec au moins 85 % de couverture ;
   - **Licences** des dépendances livrées.
4. **Une approbation** d'un autre membre est obligatoire, faite **dans les 2 heures**. GitHub demande automatiquement la relecture aux responsables du dossier (`.github/CODEOWNERS`) :

   | Auteur | Relecteur |
   | --- | --- |
   | Loum | Abdoul Aziz |
   | Khalifa | Abdoul Aziz |
   | Abdoul Aziz | Khalifa (backend) ou Loum (interface) |
   | Contrats (`app/domain/`, `app/web/viewmodels.py`, `app/mcp/schemas.py`, `docs/CONTRACTS.md`) | **les trois** |

5. La branche doit être **à jour avec `main`** (bouton « Update branch » sur la PR), toutes les conversations **résolues**.
6. Fusion en **squash**, puis suppression de la branche.

Ces règles sont **imposées par GitHub** sur `main` : le bouton de fusion reste grisé tant qu'elles ne sont pas remplies. Seule la règle des trois relecteurs pour les contrats reste une convention d'équipe.

**Tant que GitHub Actions est bloqué** (voir [.github/workflows/README.md](.github/workflows/README.md)), la CI ne tourne pas : l'auteur lance `python scripts/check.py` et colle le résumé dans la PR, et le relecteur n'approuve pas sans ce résumé tout vert.

## Changer un contrat

Les contrats sont décrits dans [docs/CONTRACTS.md](docs/CONTRACTS.md).

- **Ajouter** un champ optionnel ou une méthode : PR relue par les personnes concernées.
- **Renommer, supprimer ou changer le sens** d'un champ : accord des trois **avant** d'écrire le code, puis une PR qui met à jour en même temps le contrat, ses implémentations et les tests.

## Définition de « terminé »

Une tâche est terminée quand :

- [ ] elle marche **en ligne sur Datacloud** (en local tant que le déploiement n'est pas prêt) ;
- [ ] elle est **testée** : test automatisé, ou vérification manuelle décrite dans la PR ;
- [ ] elle a été **vérifiée sur mobile** si l'interface change ;
- [ ] il n'y a **aucun bouton mort** ni page « bientôt disponible » ;
- [ ] le **README du dossier** est à jour si la façon de travailler a changé.

## Rituels

- **Chaque matin** : trois lignes dans le groupe de l'équipe (fait hier, à faire aujourd'hui, bloqué ?).
- **Chaque soir** : 15 minutes d'appel pour **montrer** ce qui est fusionné, pas pour en parler.
- **Bloqué depuis plus de 2 heures** : on le dit tout de suite, on remplace le morceau manquant par une fausse donnée, et on continue.
- **Décision importante** : une ligne dans [docs/DECISIONS.md](docs/DECISIONS.md).

## Secrets

- Les clés et mots de passe vont dans `.env` (jamais commité) ou dans les variables d'environnement de Datacloud. Modèle : `.env.example`.
- Une clé commitée par erreur est considérée comme **compromise** : on la révoque et on la remplace immédiatement, puis on prévient l'équipe.

## Dépendances

Avant d'ajouter une bibliothèque :

1. vérifier sa licence et celles de ses dépendances (MIT, BSD, Apache, ISC ou PSF uniquement) ;
2. l'ajouter à `requirements.txt` avec sa version figée et sa licence en commentaire ;
3. lancer `python scripts/check_licenses.py`.

## Outils d'IA

Leur usage est libre, mais il doit être **déclaré à la soumission** (outils et parties concernées, voir [docs/SUBMISSION.md](docs/SUBMISSION.md)). Le jury évalue la maîtrise de l'équipe : chacun doit pouvoir **expliquer tout le code qu'il fusionne**.
