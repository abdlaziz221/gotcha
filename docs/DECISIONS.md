# Journal des décisions

Une ligne par décision qui engage l'équipe : la date, le choix, la raison. On ne supprime pas une décision dépassée : on en ajoute une nouvelle qui la remplace.

| # | Date | Décision | Pourquoi |
| --- | --- | --- | --- |
| D1 | 2 nov. | **FastAPI et pages rendues côté serveur (Jinja2)**, sans framework JavaScript | Pages de moins de 200 Ko, lisibles en 3G ; une seule application pour le site et le MCP |
| D2 | 2 nov. | **PostgreSQL avec asyncpg** (Apache 2.0), jamais psycopg (LGPL) | Règlement : licences à réciprocité interdites |
| D3 | 2 nov. | **Aucune bibliothèque qui dépend de certifi** (MPL) : ni requests, ni httpx, ni detect-secrets. Lecture HTTP avec urllib ; détection des secrets par règles maison | Même raison. Le SDK MCP 2.x passe par httpx2 et truststore, sans certifi |
| D4 | 2 nov. | **Deux stockages derrière les mêmes ports** : memory (fichiers) pour développer, postgres pour la production ; tests de contrat communs | Personne n'attend la base ; branchement en changeant une variable |
| D5 | 2 nov. | **Le contenu vit dans `content/` (Markdown et YAML, versionné dans Git)** et est chargé en base par `scripts/seed.py` | Un fichier par piège : on écrit à plusieurs sans conflit ; historique et relecture par PR |
| D6 | 2 nov. | **Fiches et pièges en JSONB** dans PostgreSQL, avec des colonnes extraites pour filtrer et chercher | Le modèle Pydantic se sérialise tel quel ; schéma simple à faire évoluer |
| D7 | 2 nov. | **Lecture du flux de pannes à l'ouverture d'une fiche** si la dernière date de plus de 10 minutes ; tâche planifiée seulement sur VPS | Le Serverless ne garantit pas les tâches planifiées (à vérifier en A2) |
| D8 | 2 nov. | **Serveur MCP sans état, réponses JSON**, monté dans la même application sur `/mcp` | Compatible avec le Serverless, aucune connexion longue |
| D9 | 2 nov. | **Une contribution approuvée est intégrée au contenu par une PR** sur `content/` | Garde une trace et une relecture ; à automatiser plus tard si le temps le permet (A7) |
| D10 | 2 nov. | **Les brouillons ne sont jamais affichés en production** ; un piège publié exige `verified_by` | Exigence d'exactitude : rien n'est publié sans relecture humaine |
| D11 | 2 nov. | ~~Dépôt privé jusqu'à la soumission~~ (remplacée par D13) | Un concurrent direct publie déjà des recettes Mobile Money |
| D12 | 2 nov. | **Contributions publiées sous licence CC BY 4.0**, données personnelles limitées au pseudo et à l'e-mail | Réutilisation libre en citant la source ; loi sénégalaise 2008-12 |
| D13 | 2 nov. | **Dépôt public**, code toujours sous droits réservés (aucun fichier de licence) | Sur un compte gratuit, les règles de `main` ne sont disponibles que pour un dépôt public, et GitHub Actions y est gratuit et illimité (le blocage du compte, découvert ensuite, touche aussi le public : voir D16). Le plagiat reste une fraude au sens du règlement (article 10) |
| D14 | 2 nov. | **Outils de qualité** : ruff (22 familles de règles), pyright pour les types, pytest avec 85 % de couverture minimale, tests d'architecture, scanner de secrets maison, pip-audit, pre-commit | Tous sous licence permissive. mypy écarté : il dépend de pathspec (MPL). pip-audit dépend de certifi : il ne tourne qu'en CI, isolé, et n'est jamais livré |
| D15 | 2 nov. | **Règles imposées sur `main`** : PR obligatoire, une approbation, CI verte sur une branche à jour, squash uniquement, pas de push forcé | `main` est déployée telle quelle sur Datacloud : elle doit toujours marcher |
| D16 | 2 nov. | **CI sur CircleCI (plan gratuit)** tant que GitHub Actions est bloqué ; workflows GitHub Actions retirés (ils échouaient sans tourner et envoyaient des notifications ; récupérables dans l'historique git, commit 3fc9c27) ; Dependabot retiré | Le compte propriétaire est verrouillé « pour un problème de facturation » sans aucun usage ni paiement : seul le support GitHub peut le lever. CircleCI tourne sur ses propres serveurs et publie ses résultats sur les PR. Même contrôles dans les deux configurations |
| D17 | 2 nov. | **Recherche faite dans l'application, pas en SQL** : PostgresStore lit les fiches visibles puis applique la même fonction que le stockage mémoire (`app/stores/search.py`) ; recharger le contenu garde les compteurs de confirmation | Résultats identiques par construction ; aucune dépendance à l'extension `unaccent`, peut-être absente sur la base managée ; volume faible (une centaine de fiches au plus). À revoir avec la recherche plein texte si le volume grandit |
| D18 | 3 nov. | **Le conteneur prépare sa base à chaque démarrage** : migrations, puis chargement de `content/` (`scripts/release.py`), sous un verrou PostgreSQL | La base managée n'est peut-être pas joignable depuis nos postes ; la base suit toujours le contenu livré dans l'image ; des instances qui démarrent ensemble passent l'une après l'autre. Recharger le contenu ne perd rien : les confirmations sont gardées (D17) |

## À trancher

| Sujet | Qui | Échéance |
| --- | --- | --- |
| Serverless ou VPS à Dakar | Abdoul Aziz (A2) | mer. 4 nov. |
| Nom définitif et domaine | Les trois (T3) | mar. 3 nov. |
| Licence du code après le concours | Les trois, après la réponse de Systalink (A1) | avant le 14 nov. |
