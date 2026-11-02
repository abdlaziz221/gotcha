# `app/` : le code de l'application

Une seule application FastAPI : le site web, le serveur MCP et l'import des pannes. Point d'entrée : `uvicorn app.main:app`.

## Carte des dossiers

| Dossier | Rôle | Responsable |
| --- | --- | --- |
| [`domain/`](domain/README.md) | **Contrats** : modèle de données, ports de stockage, erreurs | Les trois |
| [`services/`](services/README.md) | Logique métier | Abdoul Aziz ; Khalifa pour l'état des services |
| [`stores/`](stores/README.md) | Stockage memory et PostgreSQL | Abdoul Aziz |
| [`web/`](web/README.md) | Routes, contextes de pages, gabarits, CSS | Abdoul Aziz (routes) et Loum (interface) |
| [`mcp/`](mcp/README.md) | Serveur MCP pour les agents IA | Khalifa |
| [`ingest/`](ingest/README.md) | Import du flux de pannes Flutterwave | Khalifa |
| [`security/`](security/README.md) | En-têtes, CSRF, quotas, relecteurs, secrets | Abdoul Aziz ; Khalifa pour `secrets.py` |

Fichiers à la racine de `app/` (Abdoul Aziz) :

- `config.py` : lit les variables d'environnement (voir `.env.example`) ;
- `container.py` : choisit le stockage et construit les services, **seul endroit** qui connaît les implémentations concrètes ;
- `main.py` : assemble l'application (middlewares, routes, MCP, pages d'erreur).

## Règle de dépendance

```
web, mcp, ingest  ──►  services  ──►  domain  ◄──  stores
```

- `domain` n'importe rien d'autre de `app/`.
- `web`, `mcp` et `ingest` n'importent **jamais** `stores` : ils passent par les services.
- Besoin d'une donnée nouvelle ? On l'ajoute au contrat (`domain/`), puis au stockage, puis au service. Voir [docs/CONTRACTS.md](../docs/CONTRACTS.md).

## Conventions de code

- Python 3.11+, annotations de types partout, `from __future__ import annotations` en tête de module.
- Identifiants en anglais ; commentaires, docstrings et textes affichés en français. Textes destinés aux agents (MCP) en anglais.
- Formatage et lint : `ruff format .` puis `ruff check .` (configuration dans `pyproject.toml`).
- Pas de `print` dans `app/` : utiliser `logging`.
- Une erreur métier lève une exception de `domain/errors.py` ; le web et le MCP la traduisent.
