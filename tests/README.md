# `tests/` : les tests automatisés

**Responsables :** chacun teste ce qu'il écrit, dans le sous-dossier correspondant.

```bash
pytest                      # tout
pytest tests/web -x         # un dossier, arrêt au premier échec
pytest -k pas_a_pas         # par nom
pytest --cov                # avec la couverture (85 % minimum, comme la CI)
```

| Dossier | Ce qu'il vérifie | Responsable |
| --- | --- | --- |
| `contract/` | MemoryStore et PostgresStore se comportent pareil | Abdoul Aziz |
| `unit/` | Modèle, règles d'état, fraîcheur, Markdown sûr, secrets, quotas, configuration | Chacun pour son code |
| `unit/test_architecture.py` | **Règle de dépendance entre couches** : chaque dossier de `app/` n'importe que ce qu'il a le droit d'importer | Les trois |
| `services/` | Services métier (contributions, signalements, rafraîchissement des flux) | Abdoul Aziz, Khalifa |
| `ingest/` | Import Flutterwave sur l'extrait réel | Khalifa |
| `mcp/` | Outils MCP appelés en JSON-RPC, comme un agent | Khalifa |
| `web/` | Pages, liens morts, poids des pages, formulaires, CSRF, en-têtes, mode production | Abdoul Aziz, Loum |
| `content/` | Le contenu de `content/` se charge, sources présentes, termes du glossaire existants | Les trois |
| `fixtures/content/` | Petit contenu **figé** utilisé par les tests de contrat et de services | — |

## Fixtures utiles (`conftest.py`)

- `client` : application de test (comme en développement) avec une horloge figée au 2 novembre 2026 ;
- `prod_client` : même chose avec les réglages de production (brouillons cachés, pages de développement absentes) ;
- `csrf` : charge une page et renvoie son jeton CSRF, pour tester un formulaire.

## PostgreSQL

Les tests de contrat PostgreSQL tournent **à chaque PR** dans la CI, sur sa propre base. En local, ils sont ignorés sans base de test ; pour les lancer, sur une base **jetable** (elle est vidée, voir `app/stores/README.md`) :

```bash
GOTCHA_TEST_DATABASE_URL=postgresql://utilisateur:motdepasse@hote:5432/gotcha_test pytest tests/contract -m postgres
```

## Règles

- Un bogue corrigé = un test qui l'aurait attrapé.
- Pas d'appel réseau dans les tests : utiliser les extraits de `fixtures/`.
- Pas de dépendance à l'heure réelle : utiliser l'horloge figée.
- Ne pas modifier `fixtures/content/` sans adapter les tests de contrat.
