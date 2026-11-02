# `scripts/` : les outils en ligne de commande

**Responsable :** Abdoul Aziz.

| Script | Usage | Quand |
| --- | --- | --- |
| `check_licenses.py` | `python scripts/check_licenses.py` (`--list` pour tout afficher) | Après chaque ajout de dépendance ; en CI ; avant la soumission |
| `migrate.py` | `DATABASE_URL=… python scripts/migrate.py` | Avant le premier démarrage en production, puis à chaque nouvelle migration |
| `seed.py` | `DATABASE_URL=… python scripts/seed.py` | Après `migrate.py`, puis à chaque mise à jour de `content/` (demande A6) |
| `hash_password.py` | `python scripts/hash_password.py <pseudo>` | Pour créer un compte relecteur (`GOTCHA_REVIEWERS`) |

## Contrôle des licences

Le script lit les métadonnées de **tous les paquets installés** et refuse toute licence à réciprocité (GPL, LGPL, AGPL, MPL, EPL…) ou inconnue. En CI, il tourne dans un environnement neuf qui ne contient que `requirements.txt` : exactement ce qui est livré.

Un paquet dont les métadonnées sont ambiguës peut être vérifié à la main, puis ajouté au dictionnaire `OVERRIDES` avec la justification.

## Règles

- Un script lit sa configuration dans les variables d'environnement, jamais en dur.
- Un script qui écrit en base demande `DATABASE_URL` explicitement et s'arrête proprement s'il manque.
