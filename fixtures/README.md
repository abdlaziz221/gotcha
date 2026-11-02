# `fixtures/` : les fausses données de développement

**Responsables :** chacun pour ses données (Khalifa pour les pannes, Abdoul Aziz pour les contributions).

Chargées **uniquement** par le stockage mémoire, et seulement si `GOTCHA_LOAD_FIXTURES` est vrai (par défaut en développement, jamais en production). Elles permettent à chacun d'avancer sans base de données et de voir tous les états de l'interface.

| Fichier | Contenu | Utilisé par |
| --- | --- | --- |
| `flutterwave_incidents.json` | **Extrait réel** du flux d'incidents Flutterwave (9 incidents d'octobre 2026, réduits) | `FlutterwaveFeed` quand `GOTCHA_INGEST_LIVE` est faux ; tests de `tests/ingest/` |
| `incidents_communaute.json` | Une panne **fictive** signalée sur Wave Sénégal (rend la fiche « dégradée ») | `MemoryStore` |
| `contributions.json` | Deux contributions **fictives** en attente de relecture | `MemoryStore`, écran `/relecture` |

## Règles

- Toute donnée inventée est marquée **`[FICTIF]`** dans son titre.
- E-mails sur le domaine réservé `example.com`, jamais de vraie adresse ni de vrai numéro.
- Dans `incidents_communaute.json`, `minutes_ago` remplace `started_at` : la panne reste toujours récente (un signalement expire au bout de 6 heures).
- Le format suit le modèle de `app/domain/models.py` : si le contrat change, mettre ces fichiers à jour dans la même PR (les tests échouent sinon).

## Ajouter un cas

Besoin d'un état précis pour l'interface (une fiche « en panne », une longue liste de contributions) ? L'ajouter ici, avec `[FICTIF]` dans le titre, et vérifier qu'aucun test ne dépend de l'ancien contenu (`pytest`).
