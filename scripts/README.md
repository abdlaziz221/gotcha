# `scripts/` : les outils en ligne de commande

**Responsable :** Abdoul Aziz.

| Script | Usage | Quand |
| --- | --- | --- |
| `check.py` | `python scripts/check.py` (`--fix`, `--quick`) | **Avant chaque PR** : lance exactement les contrôles de la CI |
| `ci_pr_rules.py` | lancé par la CI (`PR_TITLE=… python scripts/ci_pr_rules.py` en local) | Vérifie le titre de PR (bloquant), la taille et le nom de branche |
| `scan_secrets.py` | `python scripts/scan_secrets.py` | En CI, dans pre-commit ; cherche des clés dans les fichiers suivis par git |
| `check_licenses.py` | `python scripts/check_licenses.py` (`--list` pour tout afficher, `--markdown` pour écrire `docs/LICENCES.md`) | Après chaque ajout de dépendance ; en CI ; avant la soumission |
| `migrate.py` | `DATABASE_URL=… python scripts/migrate.py` | Avant le premier démarrage en production, puis à chaque nouvelle migration |
| `seed.py` | `DATABASE_URL=… python scripts/seed.py` | Après `migrate.py`, puis à chaque mise à jour de `content/` (demande A6) |
| `hash_password.py` | `python scripts/hash_password.py <pseudo>` | Pour créer un compte relecteur (`GOTCHA_REVIEWERS`) |

## Contrôle des licences

Le script lit les métadonnées de **tous les paquets installés** et refuse toute licence à réciprocité (GPL, LGPL, AGPL, MPL, EPL…) ou inconnue. En CI, il tourne dans un environnement neuf qui ne contient que `requirements.txt` : exactement ce qui est livré.

Un paquet dont les métadonnées sont ambiguës peut être vérifié à la main, puis ajouté au dictionnaire `OVERRIDES` avec la justification.

## Faux positif du scanner de secrets

Pour une valeur de test volontaire, ajouter `# secret-scan: ignore` en fin de ligne. Mieux encore : couper la fausse clé en morceaux (`"sk_live_" + "Ab12" * 6`), comme dans `tests/unit/test_security.py`.

## Règles

- Un script lit sa configuration dans les variables d'environnement, jamais en dur.
- Un script qui écrit en base demande `DATABASE_URL` explicitement et s'arrête proprement s'il manque.
