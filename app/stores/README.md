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

| Id | Tâche | Échéance |
| --- | --- | --- |
| A3 | `PostgresStore` : `list_fiches`, `get_fiche`, `search` (plein texte), `list_glossary` | jeu. 5 |
| A4 | `PostgresStore` : `list_incidents`, `upsert_incident`, `get_last_ingest`, `set_last_ingest` | jeu. 5 |
| A5 | `PostgresStore` : contributions et confirmations ; activer PostgreSQL dans la CI | ven. 6 |
| A6 | `upsert_fiche` et `upsert_glossary`, pour que `scripts/seed.py` marche | mer. 4 |

La connexion, `ping()` et `close()` marchent déjà ; les autres méthodes lèvent `NotImplementedError("TODO(A…)")`.

## Comment faire (PostgreSQL)

1. Créer une base **jetable** en local ou sur Datacloud, puis :

   ```bash
   export GOTCHA_TEST_DATABASE_URL=postgresql://utilisateur:motdepasse@hote:5432/gotcha_test
   pytest tests/contract -m postgres
   ```

   Les tests appliquent les migrations, **vident les tables**, chargent le contenu de test, puis vérifient chaque méthode.
2. Écrire les méthodes une par une jusqu'à ce que tous les tests passent.
3. Indications :
   - fiches et pièges en **JSONB** (`fiche.model_dump(mode="json", exclude={"gotchas"})`, `Fiche.model_validate(...)`), voir D6 ;
   - sans brouillons : `WHERE publication = 'published'` sur les fiches **et** sur les pièges ;
   - recherche : remplir `search` à l'écriture (`setweight(to_tsvector('french', titre), 'A') || …`) et trier par `ts_rank` ; vérifier que les accents et la casse sont ignorés (contrat), quitte à normaliser le texte côté Python ;
   - `upsert_incident` : `INSERT … ON CONFLICT (id) DO UPDATE` ;
   - `add_confirmation` : insérer, puis mettre à jour `confirmations` et `last_confirmed_on` de la cible **dans la même transaction**, et le JSONB s'il contient ces champs.
4. Toujours des requêtes paramétrées (`$1`, `$2`) : jamais de f-string dans du SQL.

## Travailler sans attendre les autres

Tout le reste de l'équipe utilise `MemoryStore`. Tant que `PostgresStore` n'est pas fini, rien n'est bloqué ; le jour du branchement, on passe `GOTCHA_STORE=postgres` et les tests de contrat garantissent le même comportement.

## Tester

```bash
pytest tests/contract
```

Sans `GOTCHA_TEST_DATABASE_URL`, seuls les tests du stockage mémoire tournent (ceux de PostgreSQL sont ignorés).

## À ne pas faire

- Installer psycopg (LGPL) : asyncpg uniquement.
- Modifier une migration déjà appliquée : en ajouter une nouvelle (voir `migrations/README.md`).
- Ajouter une méthode à `PostgresStore` sans l'ajouter au port, à `MemoryStore` et aux tests de contrat.
