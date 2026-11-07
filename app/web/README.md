# `app/web/` : le site

Pages rendues côté serveur (FastAPI et Jinja2), sans framework JavaScript. Le site marche entièrement sans JavaScript ; `static/js/app.js` n'ajoute que du confort.

## Qui fait quoi

| Partie | Responsable | Fichiers |
| --- | --- | --- |
| Routes (URL, formulaires, redirections) | Abdoul Aziz | `routes/` |
| **Contextes de pages (contrat avec Loum)** | Abdoul Aziz et Loum | `viewmodels.py` |
| Traduction domaine → contexte | Abdoul Aziz | `presenters.py`, `labels.py`, `markdown.py`, `forms.py`, `deps.py`, `errors.py`, `templating.py` |
| Gabarits HTML | Loum | [`templates/`](templates/README.md) |
| CSS, JavaScript, images | Loum | [`static/`](static/README.md) |

## Le contrat entre routes et gabarits

Chaque route appelle les services, construit **un** objet de `viewmodels.py` et le passe au gabarit sous le nom `page`. Le gabarit reçoit aussi `csrf_token`, `site` et `request`. Tableau complet des URL et des contextes : [docs/CONTRACTS.md](../../docs/CONTRACTS.md), section 3.

- Loum a besoin d'une donnée de plus dans une page ? Il l'ajoute au contexte dans `viewmodels.py` (champ avec valeur par défaut) et demande à Abdoul Aziz de la remplir dans la route, ou la remplit lui-même dans `presenters.py` si c'est simple.
- Les champs `*_html` sont déjà nettoyés : jamais de `|safe` dans un gabarit.

## Routes

| Module | URL |
| --- | --- |
| `routes/pages.py` | `/`, `/recherche`, `/glossaire`, `/ou-sont-vos-donnees` |
| `routes/fiches.py` | `/fiches/{slug}` (et mode pas à pas), `POST /fiches/{slug}/confirmer` |
| `routes/contributions.py` | `/contribuer`, `/contribuer/merci` |
| `routes/incidents.py` | `/pannes`, `/pannes/signaler` |
| `routes/review.py` | `/relecture` (relecteurs) |
| `routes/dev.py` | `/styleguide` (développement seulement) |
| `routes/health.py` | `/healthz` |
| `routes/probe.py` | `/_sonde/…` : mesures de l'hébergeur, seulement avec `GOTCHA_PROBE=1` (tâche A2) |

## Ajouter une page

1. Ajouter sa classe de contexte dans `viewmodels.py`.
2. Écrire la route dans le module concerné : services → `presenters` → `render(request, "pages/x.html", page)`.
3. Loum écrit `templates/pages/x.html` en étendant `base.html`.
4. Ajouter l'URL à `PAGES` dans `tests/web/test_pages.py` ; le test des liens morts vérifie le reste.

Une route POST déclare toujours `Depends(verify_csrf)` et un quota (`rate_limit`), et répond par une redirection 303 en cas de succès.

## Tester

```bash
pytest tests/web
```

Ces tests vérifient : toutes les pages répondent, aucun lien interne mort, moins de 200 Ko par page, mode production sûr, formulaires, CSRF, en-têtes de sécurité.

## À ne pas faire

- Appeler le stockage depuis une route : passer par les services.
- Mettre du texte affiché en dur dans une route quand il existe un libellé dans `labels.py`.
- Ajouter un lien vers une page qui n'existe pas encore (« bientôt disponible ») : le test des liens morts échouera, et c'est voulu.
