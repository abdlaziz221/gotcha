# `app/services/` : la logique métier

**Responsables :** Abdoul Aziz (`fiches.py`, `contributions.py`, `freshness.py`, `clock.py`) et Khalifa (`status.py`, `incidents.py`). **Relecteur :** l'autre.

Les services reçoivent le stockage par injection (voir `app/container.py`) et ne connaissent que les ports de `app/domain/ports.py`. Le web et le MCP n'appellent que les services.

## Ce que contient ce dossier

| Fichier | Rôle | Responsable |
| --- | --- | --- |
| `fiches.py` | Lire les fiches, chercher, trouver la fiche d'un service dans un pays, glossaire, fraîcheur | Abdoul Aziz |
| `contributions.py` | Soumettre (avec refus des secrets), relire, confirmer « ça marche encore » | Abdoul Aziz |
| `freshness.py` | Règle des 90 jours (« à revérifier ») | Abdoul Aziz |
| `oauth.py` | Connexion au serveur MCP : comptes, codes et jetons opaques, dont seule l'empreinte est stockée | Abdoul Aziz |
| `clock.py` | Horloge système et horloge figée pour les tests | Abdoul Aziz |
| `status.py` | **Fonctions pures** : calcul de l'état normal, dégradé ou en panne | Khalifa |
| `incidents.py` | État des fiches, signalements, rafraîchissement des flux de pannes | Khalifa |

## Tâches

| Id | Tâche | Qui |
| --- | --- | --- |
| A7 | Circuit de relecture en production : une contribution approuvée doit être intégrée au contenu (aujourd'hui par une PR sur `content/`, voir D9) ; automatiser si le temps le permet | Abdoul Aziz |
| K5 | Ajuster et documenter les règles d'état ci-dessous (seuils, expiration, plusieurs signalements) | Khalifa |

## Règles d'état actuelles (`status.py`)

- Une panne compte tant qu'elle n'est pas résolue.
- Un signalement de la communauté ou d'un agent **expire au bout de 6 heures** s'il n'est pas confirmé (`REPORT_TTL`).
- Une panne **sans service** (Mobile Money en général) concerne tous les services de paiement du pays, pas les hébergeurs.
- Une panne sans pays, ou une fiche sans pays, s'appliquent partout.
- L'état est celui de la panne active **la plus grave** (`down` l'emporte sur `degraded`).

Toute nouvelle règle : un test dans `tests/unit/test_domain.py`, puis une ligne ici.

## Comment faire

- Une méthode de service est `async`, reçoit des objets du domaine et renvoie des objets du domaine (jamais de HTML, jamais de dictionnaire brut).
- Une erreur prévue lève une exception de `app/domain/errors.py`, avec un message affichable en français.
- L'heure vient toujours de l'horloge injectée (`self._clock.now()`), jamais de `datetime.now()` : les tests utilisent une horloge figée.

## Tester

```bash
pytest tests/services tests/unit
```

`tests/services/test_services.py` montre comment construire les services avec un stockage mémoire, une horloge figée et un faux flux de pannes.

## À ne pas faire

- Importer `app.stores` : passer par le port reçu.
- Faire un appel réseau ici : c'est le rôle de `app/ingest/`.
