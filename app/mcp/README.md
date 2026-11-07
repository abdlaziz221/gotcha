# `app/mcp/` : le serveur MCP pour les agents IA

**Responsable :** Khalifa. **Relecteur :** Abdoul Aziz.

Les agents de code (assistants compatibles MCP) consultent Gotcha **avant** d'écrire une intégration de paiement ou un déploiement. SDK MCP officiel pour Python, version 2.x (licence MIT), transport HTTP « streamable », **sans état**, réponses JSON : compatible avec le Serverless.

## Ce que contient ce dossier

| Fichier | Rôle |
| --- | --- |
| `schemas.py` | **Contrat** : la forme des réponses renvoyées aux agents |
| `tools.py` | La logique de chaque outil, **sans dépendance au SDK** : testable avec de simples appels |
| `oauth.py` | Fournisseur OAuth du SDK : traduit ses appels vers `app/services/oauth.py` |
| `server.py` | Enregistre les outils auprès du SDK (`MCPServer`), traduit les erreurs, monte la route `POST /mcp` |

## Outils

| Outil | Rôle |
| --- | --- |
| `list_services` | Services couverts et leurs fiches par pays |
| `get_fiche(service, country?)` | Fiche complète : étapes, pièges, écarts bac à sable et production, codes d'erreur, état |
| `search_gotchas(query, service?, country?)` | Recherche par mot-clé, en-tête, code d'erreur, symptôme |
| `get_service_status(service, country?)` | État actuel et conseil pour l'agent |
| `report_outage(service, description, country?)` | Signaler une panne (10 par heure et par compte), sous le pseudo du compte |

Détails des entrées et sorties : [docs/CONTRACTS.md](../../docs/CONTRACTS.md), section 4.

## Connexion

En production, chaque appel demande une connexion GitHub (D20). L'utilisateur ajoute l'adresse de `/mcp` à son outil une seule fois. Au premier appel, le serveur répond 401, l'outil ouvre le navigateur, et l'utilisateur se connecte. Il ne copie aucun jeton. Certains outils demandent une commande séparée dans un vrai terminal, par exemple `codex mcp login gotcha`. Un agent sans interface ne peut pas ouvrir cette connexion seul.

`oauth.py` traduit les appels du SDK vers `app/services/oauth.py`. En développement, la connexion est coupée par défaut : tout marche sans compte. Pour l'essayer, voir `deploy/README.md`.

Sans connexion en production (`GOTCHA_MCP_AUTH=false`), le serveur est en lecture libre et `report_outage` disparaît : aucune écriture anonyme, même en secours.

## Tâches

| Id | Tâche | Échéance |
| --- | --- | --- |
| K2 | Brancher un vrai agent sur le serveur local ; affiner les descriptions et les réponses (ce que l'agent comprend vraiment) | mar. 3 |
| K6 | `report_outage` : quotas, abus, messages | ven. 6 |
| K8 | Scénario de démo et test automatisé reproductible (voir `docs/DEMO.md`) | ven. 6 |
| K9 | Serveur en ligne sur Datacloud, testé depuis un vrai agent | sam. 7 |

## Comment faire

1. Lancer le site : `uvicorn app.main:app --reload`. Le serveur MCP répond sur `http://localhost:8000/mcp`.
2. Déclarer ce serveur dans le client MCP de l'agent (transport HTTP, URL ci-dessus), puis lui demander d'intégrer MTN MoMo.
3. Essai à la main, sans agent :

   ```bash
   curl -s http://localhost:8000/mcp -H "Content-Type: application/json" -H "Accept: application/json, text/event-stream" -d '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"get_fiche","arguments":{"service":"mtn-momo"}}}'
   ```

4. Ajouter un outil : la logique dans `tools.py`, la forme de la réponse dans `schemas.py`, l'enregistrement dans `server.py` (avec `@_tool_errors` et des annotations), un test dans `tests/mcp/test_mcp.py`, une ligne dans `docs/CONTRACTS.md`.
5. Les descriptions d'outils sont en anglais, concises, avec un exemple d'argument : c'est ce que lit l'agent pour choisir l'outil.

En production, définir `GOTCHA_SITE_URL` (liens renvoyés aux agents) et `GOTCHA_ALLOWED_HOSTS` (le domaine public), sinon le SDK refuse les requêtes (protection contre le DNS rebinding).

## Travailler sans attendre les autres

Les outils lisent les services, eux-mêmes branchés sur le stockage mémoire : tout marche dès maintenant avec les fiches de `content/` et les pannes fictives. Le passage à PostgreSQL ne change rien ici.

## Tester

```bash
pytest tests/mcp
```

Les tests appellent `POST /mcp` en JSON-RPC, comme un agent.

## À ne pas faire

- Renvoyer l'e-mail d'un contributeur ou tout autre champ privé.
- Ajouter un outil qui écrit sans quota.
- Laisser une exception brute remonter à l'agent : lever une erreur métier, `@_tool_errors` la traduit.
