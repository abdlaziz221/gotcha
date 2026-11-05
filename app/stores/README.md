# `app/stores/` : le stockage

**Responsable :** Abdoul Aziz. **Relecteur :** Khalifa.

Deux implémentations des mêmes ports (`app/domain/ports.py`), choisies au démarrage par `GOTCHA_STORE`.

| Implémentation | Quand | Données |
| --- | --- | --- |
| `memory/store.py` (`MemoryStore`) | Développement, tests, démo hors ligne | `content/` (fiches) et `fixtures/` (pannes et contributions fictives) ; tout est perdu au redémarrage |
| `postgres/store.py` (`PostgresStore`) | Production sur Datacloud | Base PostgreSQL managée, schéma dans `migrations/` |

`content_files.py` lit le dossier `content/` ; il sert au stockage mémoire **et** à `scripts/seed.py`.

**`MemoryStore` est la référence de comportement.** `PostgresStore` doit faire exactement pareil : c'est ce que vérifient les tests de `tests/contract/`.

## Tâches

| Id | Tâche | État |
| --- | --- | --- |
| A3 | `PostgresStore` : `list_fiches`, `get_fiche`, `search`, `list_glossary` | Fait |
| A4 | `PostgresStore` : `list_incidents`, `upsert_incident`, `get_last_ingest`, `set_last_ingest` | Fait |
| A5 | `PostgresStore` : contributions et confirmations ; PostgreSQL dans la CI | Fait |
| A6 | `upsert_fiche` et `upsert_glossary`, pour que `scripts/seed.py` marche | Fait |

`search.py` contient la logique **commune aux deux stockages** : visibilité des brouillons, tri, recherche, conservation des compteurs au rechargement du contenu. PostgresStore lit les fiches en base puis leur applique ces fonctions : les résultats sont identiques par construction (décision D17).

## Comment ça marche (PostgreSQL)

- Fiches et pièges en **JSONB** (le modèle Pydantic sérialisé, D6) ; les compteurs de confirmation sont dans des colonnes à part, que `add_confirmation` incrémente **dans la même transaction** que l'insertion de la confirmation.
- Sans brouillons : `WHERE publication = 'published'` sur les fiches **et** sur les pièges.
- `upsert_fiche` historise chaque changement de contenu dans `fiche_revisions` (jamais les simples compteurs). Il ne relit pas l'ancienne fiche : les compteurs ne sont pas dans le `DO UPDATE` et la date passe par `GREATEST`, donc une confirmation reçue pendant le rechargement n'est jamais écrasée.
- Les champs que le modèle ne connaît plus sont ignorés à la lecture du JSONB, puis effacés par le prochain chargement.
- `retire_fiches` repasse en brouillon les fiches retirées de `content/` (l'historique reste) ; `upsert_glossary` remplace tout le glossaire.
- `update_contribution` ne touche qu'une contribution encore `pending` (`WHERE status = 'pending'`) : de deux relecteurs simultanés, seul le premier l'emporte.
- Toujours des requêtes paramétrées (`$1`, `$2`) : jamais de f-string dans du SQL.

## Lancer les tests PostgreSQL en local

Il faut une base **jetable** : les tests vident les tables. Le plus simple, avec Docker :

```bash
docker run -d --name gotcha-pg -e POSTGRES_HOST_AUTH_METHOD=trust -e POSTGRES_DB=gotcha_test -p 127.0.0.1:55432:5432 postgres:17-alpine
```

```bash
GOTCHA_TEST_DATABASE_URL=postgresql://postgres@localhost:55432/gotcha_test pytest tests/contract
```

Sans Docker, avec un PostgreSQL installé : créer une instance de test à part (`initdb` dans un dossier temporaire, puis `pg_ctl start -o "-p 55432"`), jamais la base d'un vrai projet. La CI (CircleCI) lance ces tests à chaque PR, sur sa propre base.

## Travailler sans attendre les autres

Tout le reste de l'équipe développe avec `MemoryStore`, sans base. En production, `GOTCHA_STORE=postgres` : les tests de contrat garantissent le même comportement.

## Tester

```bash
pytest tests/contract
```

Sans `GOTCHA_TEST_DATABASE_URL`, seuls les tests du stockage mémoire tournent (ceux de PostgreSQL sont ignorés en local, jamais en CI).

## À ne pas faire

- Installer psycopg (LGPL) : asyncpg uniquement.
- Modifier une migration déjà appliquée : en ajouter une nouvelle (voir `migrations/README.md`).
- Ajouter une méthode à `PostgresStore` sans l'ajouter au port, à `MemoryStore` et aux tests de contrat.
