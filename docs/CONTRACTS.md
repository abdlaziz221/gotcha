# Les cinq contrats

Un contrat, c'est ce que deux parties du code se promettent. Tant qu'on le respecte, chacun peut avancer seul, sur des fausses données, et le branchement final se passe bien.

| # | Contrat | Fichier de référence | Entre qui |
| --- | --- | --- | --- |
| 1 | Modèle de données | `app/domain/models.py` | Les trois |
| 2 | Ports de stockage | `app/domain/ports.py` + `tests/contract/` | Abdoul Aziz et tout le code |
| 3 | Pages et contextes | `app/web/viewmodels.py` | Abdoul Aziz (routes) et Loum (gabarits) |
| 4 | Outils MCP | `app/mcp/schemas.py` | Khalifa et les agents IA |
| 5 | Format du contenu | `content/README.md` | Les trois (rédaction) |

**Le code fait foi.** Ce document résume ; en cas d'écart, on corrige ce document.

**Changer un contrat :** ajouter un champ optionnel ou une méthode demande une PR relue par les personnes concernées. Renommer, supprimer ou changer le sens d'un champ demande l'accord des trois **avant** d'écrire le code (voir [CONTRIBUTING.md](../CONTRIBUTING.md)).

---

## 1. Modèle de données

Objets immuables (Pydantic), champs inconnus refusés. Les valeurs des énumérations sont en anglais ; les libellés affichés sont dans `app/web/labels.py`.

| Objet | Rôle | Champs principaux |
| --- | --- | --- |
| `Service` | Un opérateur ou un hébergeur | `slug` (`mtn-momo`), `name`, `kind` (`payment` ou `hosting`), `operator`, `docs_url` |
| `Fiche` | Un service dans un pays | `slug` (`orange-money-sn`), `service`, `country` (code ISO ou vide = tous les pays), `title`, `summary`, `prerequisites`, `steps`, `gotchas`, `differences`, `error_codes`, `sources`, `publication`, `last_confirmed_on`, `confirmations` |
| `Gotcha` | Un piège | `id` (`<fiche>.<fichier>`), `title`, `symptom_md`, `cause_md`, `fix_md`, `severity` (`blocking`, `major`, `minor`), `confidence` (`sourced`, `reproduced`, `production`), `failed_attempts_md?`, `proof_md?` (obligatoire au-dessus de `sourced`), `environments` (`sandbox`, `production`), `api_version`, `error_codes`, `sources` (au moins une), `publication`, `verified_by`, `last_confirmed_on`, `confirmations` |
| `Source` | D'où vient une information | `title`, `url` ou `author`, `accessed_on` |
| `GlossaryTerm` | Un terme expliqué | `slug`, `term`, `definition` |
| `ContributionInput` / `Contribution` | Une proposition à relire | `kind` (`gotcha`, `step`, `correction`), `fiche_slug`, `title`, `body_md`, `source_url`, `api_version`, `pseudo`, `email` (**privé**), `status` (`pending`, `approved`, `rejected`) |
| `Confirmation` | Un clic « ça marche encore » | `target_kind` (`fiche` ou `gotcha`), `target_id`, `still_works`, `api_version`, `pseudo`, `created_at` |
| `Incident` | Une panne | `id`, `source` (`flutterwave`, `community`, `agent`), `service_slug` (vide = tout le Mobile Money du pays), `country`, `status` (`degraded`, `down`), `title`, `started_at`, `resolved_at` |
| `OutageReport` | Un signalement | `service_slug`, `country`, `description`, `reported_by`, `source` |
| `ServiceStatus` | État calculé | `status` (`normal`, `degraded`, `down`, `unknown`), `since`, `active_incidents`, `checked_at` |
| `SearchQuery` / `SearchHit` | Recherche | `text`, `service`, `country`, `limit` / `kind` (`fiche`, `gotcha`, `error_code`), `fiche_slug`, `title`, `snippet`, `anchor`, `score` |

Règles garanties par le modèle :

- un piège **publié** a forcément un `verified_by` ;
- l'`id` d'un piège commence par le slug de sa fiche ;
- les étapes sont numérotées 1, 2, 3… ;
- une source a une URL ou un auteur ;
- l'**e-mail d'un contributeur n'est jamais affiché ni renvoyé** par le serveur MCP.

## 2. Ports de stockage

`Store` réunit quatre interfaces : `FicheStore`, `IncidentStore`, `ContributionStore`, `AccountStore`. Deux implémentations : `MemoryStore` (référence, fichiers) et `PostgresStore` (production). Les tests de `tests/contract/` tournent sur les deux.

| Méthode | Comportement promis |
| --- | --- |
| `list_fiches(include_drafts)` | Fiches triées par titre. Sans brouillons : seules les fiches publiées, avec leurs seuls pièges publiés |
| `get_fiche(slug, include_drafts)` | La fiche, ou `None` (y compris pour un brouillon quand `include_drafts` est faux) |
| `search(query, include_drafts)` (logique commune : `app/stores/search.py`) | Résultats triés par score décroissant, au plus `query.limit`, insensibles à la casse et aux accents, filtrés par service et pays ; un code d'erreur exact donne un résultat `error_code` |
| `list_glossary()` | Termes triés par terme |
| `upsert_fiche(fiche)` / `upsert_glossary(terms)` | Création ou remplacement (utilisés au chargement de `content/`, à chaque démarrage en production). Les pièges retirés disparaissent, leur ordre est conservé ; les **compteurs de confirmation déjà enregistrés sont gardés** et `last_confirmed_on` garde la date la plus récente |
| `list_incidents(service_slug, country, active_only, limit)` | Pannes de la plus récente à la plus ancienne |
| `upsert_incident(incident)` | Idempotent sur `incident.id` |
| `get_last_ingest(source)` / `set_last_ingest(source, at)` | Dernière lecture réussie d'un flux |
| `add_contribution`, `get_contribution`, `update_contribution` | Classiques |
| `list_contributions(status)` | De la plus ancienne à la plus récente (file de relecture) |
| `add_confirmation(c)` | Si `still_works` : le compteur de la cible augmente de 1 et sa date de dernière confirmation devient celle du jour |
| `has_recent_confirmation(account_id, target_id, since)` / `list_confirmations(limit)` | Évite qu'un compte recompte la même cible ; dernières confirmations d'abord |
| `save_account(account)` / `get_account(id)` | Création ou remplacement ; un blocage déjà posé est conservé |
| `save_oauth_client(id, data)` / `get_oauth_client(id)` | Outils MCP enregistrés |
| `add_oauth_grant`, `get_oauth_grant`, `take_oauth_grant`, `delete_expired_oauth_grants` | Autorisations retrouvées par l'empreinte de leur jeton. Expirée = absente. `take` renvoie et supprime en une seule opération : deux appels ne peuvent pas réussir |

## 3. Pages et contextes

Chaque gabarit de `app/web/templates/pages/` reçoit `page` (une classe de `app/web/viewmodels.py`), `csrf_token`, `site` et `request`. Les champs `*_html` sont déjà nettoyés : on les affiche tels quels, **jamais avec `|safe`**.

| URL | Méthode | Gabarit | Contexte `page` | Remarques |
| --- | --- | --- | --- | --- |
| `/` | GET | `home.html` | `HomePage` | Fiches, pannes en cours |
| `/recherche?q=&service=&pays=` | GET | `search.html` | `SearchPage` | |
| `/fiches/{slug}` | GET | `fiche.html` | `FichePage` | `?mode=pas-a-pas&etape=N` remplit `step_mode` |
| `/fiches/{slug}/confirmer` | POST | — | — | Champs `target_kind`, `target_id` ; redirige avec `?ok=confirmation` |
| `/contribuer?fiche=` | GET, POST | `contribute.html` | `ContributePage` | Erreurs dans `page.form.errors[champ]` ; succès vers `/contribuer/merci` |
| `/contribuer/merci` | GET | `message.html` | `MessagePage` | |
| `/pannes` | GET | `incidents.html` | `IncidentsPage` | |
| `/pannes/signaler?fiche=` | GET, POST | `report_outage.html` | `ReportOutagePage` | Succès : retour sur la fiche avec `?ok=signalement` |
| `/relecture` | GET | `review.html` | `ReviewPage` | Relecteurs seulement |
| `/relecture/{id}` | POST | — | — | `action` = `approve` ou `reject`, `note` |
| `/glossaire` | GET | `glossary.html` | `GlossaryPage` | Un `id` par terme (ancre) |
| `/ou-sont-vos-donnees` | GET | `data.html` | `StaticPage` | |
| `/styleguide` | GET | `styleguide.html` | `StyleguidePage` | Développement seulement |
| erreurs | — | `error.html` | `ErrorPage` | 400, 401, 403, 404, 429, 500 |
| `/healthz` | GET | JSON | — | `?db=1` teste PostgreSQL |
| `/mcp` | POST | JSON-RPC | — | Serveur MCP |

Chaque formulaire POST contient `<input type="hidden" name="csrf_token" value="{{ csrf_token }}">`. Les classes CSS d'état suivent la valeur de l'énumération : `badge--normal`, `badge--degraded`, `badge--down`, `badge--unknown`.

## 4. Outils MCP

Transport HTTP « streamable », sans état, réponses JSON, point d'entrée `POST /mcp`. En production, tout appel demande une connexion GitHub : sans jeton, le serveur répond 401 et l'outil MCP compatible ouvre le navigateur (D20). Réponses structurées décrites dans `app/mcp/schemas.py`.

| Outil | Entrées | Sortie | Notes |
| --- | --- | --- | --- |
| `list_services` | — | `list[ServiceOut]` | Services et leurs fiches par pays |
| `get_fiche` | `service`, `country?` | `FicheOut` | Étapes, pièges, écarts, codes d'erreur, état ; `warning` si des pièges ne sont pas vérifiés |
| `search_gotchas` | `query`, `service?`, `country?` | `list[SearchResultOut]` | 10 résultats au plus |
| `get_service_status` | `service`, `country?` | `StatusOut` | Avec un conseil (`advice`) pour l'agent |
| `report_outage` | `service`, `description`, `country?` | `OutageReportOut` | Seul outil qui écrit ; 10 signalements par heure et par compte. Absent en production sans connexion |

Erreurs : un service ou une fiche inconnus renvoient une erreur d'outil lisible (`isError: true`), jamais une exception brute. Les textes des pièges sont renvoyés sans la syntaxe `[[terme]]` du glossaire.

## 5. Format du contenu

Détaillé dans [content/README.md](../content/README.md). En bref :

```
content/
├── glossaire.yml
└── fiches/<slug>/
    ├── fiche.yml          métadonnées, prérequis, écarts, codes d'erreur, sources
    ├── etapes.md          une étape par titre « ## »
    └── pieges/<nom>.md    en-tête YAML + sections ## Symptôme, ## Cause, ## Solution
```

`pytest tests/content` vérifie que tout le contenu se charge et que chaque `[[terme]]` existe dans le glossaire.
