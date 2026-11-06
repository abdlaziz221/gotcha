# `migrations/` : le schéma PostgreSQL

**Responsable :** Abdoul Aziz. **Relecteur :** Khalifa.

Fichiers SQL appliqués dans l'ordre de leur nom, **une seule fois chacun**, par `scripts/migrate.py` (et par les tests de contrat PostgreSQL). La table `schema_migrations` garde la liste des migrations appliquées.

| Fichier | Contenu |
| --- | --- |
| `001_init.sql` | Schéma initial : fiches et pièges (JSONB, ordre des pièges, compteurs de confirmation), historique du contenu, glossaire, confirmations, contributions, pannes, lectures des flux |

## Comment faire

- **Appliquer** : `DATABASE_URL=postgresql://… python scripts/migrate.py`
- **Changer le schéma** : créer `002_<sujet>.sql`, `003_<sujet>.sql`… **Ne jamais modifier une migration déjà appliquée** en production.
- Tant que la production n'existe pas (avant A8), on peut encore corriger `001_init.sql` : prévenir l'équipe et recréer la base de test.
- Chaque migration doit passer sur une base vide **et** sur une base à jour : la tester avec `pytest tests/contract -m postgres`.

## À ne pas faire

- Mettre des données de contenu ici : le contenu se charge avec `scripts/seed.py`.
- Utiliser une extension PostgreSQL sans vérifier qu'elle existe sur la base managée de Datacloud (`unaccent`, par exemple).
