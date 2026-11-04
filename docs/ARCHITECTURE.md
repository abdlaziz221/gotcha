# Architecture

Une seule application Python (FastAPI) sert le site web et le serveur MCP. Pages rendues côté serveur avec Jinja2, sans framework JavaScript : légères, lisibles en 3G.

## Couches et règle de dépendance

```
                ┌──────────────┐   ┌──────────────┐   ┌──────────────┐
  entrées       │  app/web     │   │  app/mcp     │   │  app/ingest  │
                │ (pages)      │   │ (agents IA)  │   │ (Flutterwave)│
                └──────┬───────┘   └──────┬───────┘   └──────┬───────┘
                       │                  │                  │
                       ▼                  ▼                  │
                ┌─────────────────────────────────────┐      │
  métier        │  app/services                       │◄─────┘
                │  fiches · contributions · incidents │
                │  status (règles d'état, pur)        │
                └──────────────────┬──────────────────┘
                                   │ ne connaît que les ports
                                   ▼
                ┌─────────────────────────────────────┐
  contrats      │  app/domain                         │
                │  models · ports · errors            │
                └──────────────────▲──────────────────┘
                                   │ implémentent les ports
                ┌──────────────────┴──────────────────┐
  stockage      │  app/stores                         │
                │  memory (content/, fixtures/)       │
                │  postgres (asyncpg)                 │
                └─────────────────────────────────────┘
```

- `app/domain` ne dépend de rien d'autre dans `app/`.
- `app/services` dépend de `app/domain` (et reçoit le stockage par injection).
- `app/web`, `app/mcp` et `app/ingest` dépendent de `app/services` et de `app/domain`, **jamais** de `app/stores`.
- `app/container.py` est le seul endroit qui choisit les implémentations concrètes.
- Ces règles sont vérifiées à chaque PR par `tests/unit/test_architecture.py`.
- `app/security` est transverse : middlewares et dépendances FastAPI, détection des secrets.

## Flux principaux

**Afficher une fiche (`GET /fiches/orange-money-sn`)**

1. La route appelle `FicheService.get(slug)`, puis `IncidentService.status_for(fiche)`.
2. `presenters.py` transforme la fiche en `FichePage` : Markdown rendu et nettoyé, libellés français.
3. Le gabarit `pages/fiche.html` affiche la page.
4. Après la réponse, une tâche de fond relit le flux Flutterwave si la dernière lecture date de plus de 10 minutes.

**Contribuer (`POST /contribuer`)**

1. Vérification du jeton CSRF, puis du quota (5 par heure et par IP).
2. Validation par `ContributionInput`, puis `ContributionService.submit` : fiche existante, e-mail plausible, **aucun secret** (sinon refus, rien n'est enregistré).
3. La contribution est enregistrée « en attente » et apparaît dans `/relecture`.

**Un agent demande une fiche (`POST /mcp`, outil `get_fiche`)**

1. Le SDK MCP décode l'appel et appelle `app/mcp/tools.get_fiche`.
2. Rafraîchissement des pannes si besoin, recherche de la fiche du pays (ou de la fiche valable partout), calcul de l'état.
3. Réponse structurée `FicheOut`, avec un avertissement si des pièges ne sont pas encore vérifiés.

**Pannes**

1. `FlutterwaveFeed.fetch()` lit le flux (ou l'extrait enregistré en développement) ; `map_incident` déduit l'opérateur et le pays du texte.
2. Les pannes sont enregistrées de façon idempotente.
3. `status.compute_status` calcule l'état d'un service dans un pays : la panne active la plus grave l'emporte ; un signalement non confirmé expire au bout de 6 heures.

## Configuration et environnements

| Variable | dev (défaut) | test | prod |
| --- | --- | --- | --- |
| `GOTCHA_STORE` | `memory` | `memory` | `postgres` |
| `GOTCHA_SHOW_DRAFTS` | vrai | vrai | **faux, imposé** |
| `GOTCHA_LOAD_FIXTURES` | vrai | vrai | faux |
| `GOTCHA_INGEST_LIVE` | faux (extrait enregistré) | faux | vrai |
| `/styleguide` | visible | visible | 404 |
| `/relecture` sans relecteur configuré | ouvert (« dev ») | ouvert | 404 |
| HSTS, cookie `Secure` | non | non | oui |

Toutes les variables sont décrites dans `.env.example`.

## Sécurité

- **CSP stricte** : aucun script ni style en ligne ; tout vient du site.
- **CSRF** par double soumission : cookie `gotcha_csrf` (HttpOnly, SameSite=Lax) recopié dans chaque formulaire.
- **Quotas** en mémoire par IP (5 contributions, 30 confirmations, 5 signalements par heure ; 10 signalements MCP).
- **Markdown** sans HTML brut, nettoyé par nh3 avec une liste blanche de balises.
- **Secrets** refusés dans les contributions, jamais stockés ni journalisés.
- **Relecteurs** authentifiés en HTTP Basic, mots de passe hachés avec scrypt.
- **Serveur MCP** : en lecture seule, sauf `report_outage` limité par quota ; protection contre le DNS rebinding (`GOTCHA_ALLOWED_HOSTS`).

## Pourquoi ces choix

Voir [DECISIONS.md](DECISIONS.md).
