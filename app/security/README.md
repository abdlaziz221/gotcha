# `app/security/` : la sécurité transverse

**Responsables :** Abdoul Aziz (tout le dossier sauf `secrets.py`) et Khalifa (`secrets.py`). **Relecteur :** l'autre.

## Ce que contient ce dossier

| Fichier | Rôle |
| --- | --- |
| `headers.py` | Middleware qui ajoute les en-têtes de sécurité : CSP stricte, `nosniff`, `X-Frame-Options`, `Referrer-Policy`, `Permissions-Policy`, HSTS en production |
| `csrf.py` | Jeton CSRF par double soumission : cookie `gotcha_csrf` + champ caché ; dépendance `verify_csrf` sur chaque POST |
| `ratelimit.py` | Quotas par IP, en mémoire ; dépendance `rate_limit(nom, limit=…, window_seconds=…)` |
| `auth.py` | Relecteurs : HTTP Basic, mots de passe hachés avec scrypt, dépendance `require_reviewer` |
| `secrets.py` | Détection des clés et jetons dans les contributions (règles maison) |

## Tâches

| Id | Tâche | Qui | Échéance |
| --- | --- | --- | --- |
| K7 | `secrets.py` : vrais formats de clés Wave, Orange Money, MTN MoMo, Daraja ; chaque règle avec un vrai positif et un faux positif dans `tests/unit/test_security.py` | Khalifa | mer. 4 |
| A11 | Revue en production : en-têtes présents, cookie `Secure`, quotas corrects derrière le proxy de Datacloud (`GOTCHA_TRUST_PROXY`), CSP sans erreur dans la console | Abdoul Aziz | mer. 11 |

## Comment faire

- **Nouvelle route POST** : `dependencies=[Depends(verify_csrf), Depends(rate_limit("nom", limit=…, window_seconds=…))]`.
- **Ajouter un relecteur** : `python scripts/hash_password.py <pseudo>`, puis ajouter la ligne obtenue à `GOTCHA_REVIEWERS` sur Datacloud (séparateur `;`).
- **Nouvelle règle de secret** : l'ajouter à `RULES` avec un libellé français, puis deux tests (une clé fictive au bon format, un texte normal qui ne doit pas déclencher). Ne jamais mettre une vraie clé dans un test.
- **Assouplir la CSP** (par exemple pour une image externe) : à éviter ; si c'est indispensable, en discuter et noter la décision dans `docs/DECISIONS.md`.

## Limites connues

- Les quotas sont **par instance** : sur le Serverless, plusieurs instances ont chacune leurs compteurs. Suffisant pour le MVP ; à déplacer dans PostgreSQL en cas d'abus.
- La détection des secrets attrape les formats connus, pas tout : la relecture humaine reste obligatoire.

## Tester

```bash
pytest tests/unit/test_security.py tests/web/test_forms.py
```

## À ne pas faire

- Journaliser un secret détecté, un mot de passe ou une URL de base de données.
- Désactiver `verify_csrf` « pour tester » : utiliser la fixture `csrf` des tests.
