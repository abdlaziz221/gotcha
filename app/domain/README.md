# `app/domain/` : les contrats partagés

**Responsables :** les trois membres. **Toute modification est relue par les trois.**

C'est le vocabulaire commun de tout le code. Rien ici ne fait d'entrée/sortie : pas de base, pas de réseau, pas de fichier.

## Ce que contient ce dossier

| Fichier | Contenu |
| --- | --- |
| `models.py` | Le modèle de données (Pydantic, objets immuables) : `Fiche`, `Gotcha`, `Incident`, `Contribution`… |
| `ports.py` | Ce que le code attend du stockage (`Store`), de l'horloge (`Clock`) et des flux de pannes (`IncidentFeed`) |
| `errors.py` | Les erreurs métier : `NotFoundError`, `InvalidInputError`, `SecretDetectedError` |
| `countries.py` | Les pays suivis et leurs noms en français |
| `text.py` | Outils liés au format du contenu (syntaxe `[[terme]]` du glossaire) |

Résumé lisible : [docs/CONTRACTS.md](../../docs/CONTRACTS.md), sections 1 et 2.

## Tâches

- **T1 (lundi 2)** : relire `models.py` et `ports.py` à trois. Ce qui manque ou gêne se règle aujourd'hui, pas jeudi.

## Comment modifier

1. **Ajouter** un champ : toujours **optionnel** (avec une valeur par défaut), pour ne casser ni le contenu existant ni les fausses données.
2. **Renommer ou supprimer** : accord des trois d'abord, puis une seule PR qui met à jour le modèle, les deux stockages, les fixtures, le contenu, les tests et `docs/CONTRACTS.md`.
3. **Ajouter une méthode au stockage** (`ports.py`) : l'écrire d'abord dans `MemoryStore`, ajouter son test dans `tests/contract/`, puis prévenir Abdoul Aziz pour `PostgresStore`.
4. Une règle métier simple qui porte sur un seul objet (ex. « un piège publié a un `verified_by` ») va dans un validateur du modèle ; une règle qui demande le stockage ou l'horloge va dans `app/services/`.

## Tester

```bash
pytest tests/unit tests/contract
```

## À ne pas faire

- Importer `app.stores`, `app.web`, FastAPI ou asyncpg ici.
- Mettre un texte d'interface dans le modèle : les libellés sont dans `app/web/labels.py`.
- Exposer `Contribution.email` ailleurs que dans le stockage : c'est une donnée personnelle.
