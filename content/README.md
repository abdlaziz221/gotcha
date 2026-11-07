# `content/` : les fiches, les pièges et le glossaire

**Responsables :** les trois membres. Chaque service a un rédacteur principal :

| Service | Fiche(s) | Rédacteur | Tâche |
| --- | --- | --- | --- |
| MTN MoMo | `mtn-momo` | Khalifa | K3, K10 |
| M-Pesa | `mpesa-ke` | Khalifa | K10 |
| Wave | `wave-sn` | Loum | L11 |
| Orange Money | `orange-money-sn` (et `orange-money-ci` à créer) | Abdoul Aziz | A9 |
| Datacloud | `datacloud-sn` | Abdoul Aziz | A10 |

Objectif : **au moins 15 pièges bien documentés le dimanche 8 novembre**, avec un niveau de confiance honnête, sur MTN MoMo, M-Pesa, Wave et Orange Money, plus la fiche Datacloud (D21). Mieux vaut 15 pièges vérifiés que 30 présentés à tort comme testés. Un piège n'est marqué « confirmé en production » qu'avec une preuve de production.

**Fiches ouvertes sans compte :** `datacloud-sn` et, pendant la compétition, `wave-sn` (D27, tâche A18). Elles doivent d'abord être publiées, car un brouillon n'est jamais affiché en production.

**Audio en wolof, si le socle est en ligne le 8 novembre (D26) :** 3 à 5 explications de 30 à 45 secondes, avec les noms techniques conservés. Un second locuteur écoute chaque enregistrement et relit chaque transcription. Le piège en français reste la référence.

## Le contenu de départ est en brouillon

Les fiches présentes au départ sont des **brouillons de démonstration** (`publication: draft`), construits à partir des sources de nos recherches pour que le développement avance. **Chaque élément doit être vérifié, réécrit si besoin et sourcé** par son rédacteur avant de passer en `published`. Les brouillons ne sont jamais affichés en production.

## Structure

```
content/
├── glossaire.yml
└── fiches/
    └── <slug>/                  ex. orange-money-sn (service + pays), mtn-momo (tous pays)
        ├── fiche.yml            métadonnées de la fiche
        ├── etapes.md            les étapes, une par titre « ## »
        └── pieges/
            └── <nom>.md         un piège par fichier (le nom devient l'ancre : #piege-<nom>)
```

### `fiche.yml`

```yaml
service:
  slug: orange-money          # minuscules et tirets
  name: Orange Money
  kind: payment               # payment ou hosting
  operator: Orange
  docs_url: https://developer.orange.com
country: SN                   # code ISO, ou null pour « tous les pays »
title: Orange Money Sénégal
summary: Une phrase qui dit ce que la fiche permet de faire.
api_version: null
publication: draft            # draft, puis published après vérification
last_confirmed_on: 2026-11-02
prerequisites:
  - Un compte sur developer.orange.com.
differences:                  # écarts entre bac à sable et production
  - topic: Devise
    sandbox: EUR uniquement
    production: XOF
error_codes:
  - code: "400"
    meaning: Requête invalide
    action: Vérifier les en-têtes obligatoires
sources:
  - title: Documentation officielle
    url: https://…
    accessed_on: 2026-11-02
```

### `pieges/<nom>.md`

```markdown
---
title: "Le bac à sable n'accepte que l'EUR"
severity: major                     # blocking, major ou minor
environments: [sandbox]             # sandbox, production, ou les deux
api_version: v1_0
error_codes: ["400"]
confidence: sourced                 # sourced, reproduced ou production (voir plus bas)
publication: draft
verified_by: null                   # pseudo de la personne qui a vérifié (obligatoire pour published)
last_confirmed_on: 2026-11-02
sources:
  - title: "Forum MTN MoMo : …"
    url: https://…
    published_on: 2026-01-07        # date de publication, si la page la donne
    accessed_on: 2026-11-02          # le jour où vous l'avez lue
  - title: Retour de terrain           # ou un témoignage
    author: pseudo_du_dev
    accessed_on: 2026-11-02
---

## Symptôme

Ce qu'on observe, avec le message d'erreur exact si possible.

## Cause

Pourquoi ça arrive.

## Solution

Comment l'éviter, avec un exemple de code court si utile.

## Pistes qui ont échoué

Ce qui a été essayé sans succès. C'est souvent ce qui fait gagner le plus de temps.

## Preuve

Les versions, la configuration sans secret, les étapes, le résultat attendu et le résultat obtenu.
```

Les trois sections **Symptôme**, **Cause** et **Solution** sont obligatoires. **Pistes qui ont échoué** et **Preuve** sont facultatives, sauf la preuve dès que le niveau dépasse `sourced`.

### Niveaux de confiance

| `confidence` | Sens | Ce qu'il faut |
| --- | --- | --- |
| `sourced` | Lu, sans test de notre part | Une source officielle, ou au moins deux sources recoupées |
| `reproduced` | Reproduit dans un bac à sable | Une section **Preuve**, avec la date et la version |
| `production` | Confirmé par un développeur en production | Une section **Preuve** |

Une capture d'écran seule n'est pas une preuve, et un test en bac à sable ne vaut jamais confirmation en production.

Une date récente ne rend pas une source plus sûre : un blog ou un dépôt récent a pu être écrit par un agent. Ne publiez pas sur la seule foi d'une telle source.

### Glossaire

Dans le texte d'une étape ou d'un piège, `[[webhook]]` ou `[[jeton-acces|jeton]]` devient un lien vers la définition. Le terme doit exister dans `glossaire.yml` (le test le vérifie).

## Règles de rédaction

1. **Chaque piège a au moins une source** : une page publique (URL) ou un retour de terrain (auteur).
2. **Un piège tiré d'un blog non officiel n'est publié que s'il est recoupé** par une deuxième source ou par notre propre test.
3. **Réécrire, ne jamais copier** une source : on résume avec nos mots et on cite.
4. **Aucun piège inventé** : chaque piège vient d'une source citée ou d'un problème réellement rencontré. Un agent peut préparer un brouillon, mais son développeur l'approuve et un relecteur le vérifie.
5. Phrases courtes, vocabulaire expliqué (glossaire), un exemple concret par piège quand c'est possible.
6. **Aucune vraie clé, aucun vrai numéro de téléphone** dans les exemples : `<VOTRE_CLE>`, `+221 77 000 00 00`.
7. Pour publier : mettre `publication: published` et `verified_by: <votre pseudo>` après avoir **reproduit** le piège ou **recoupé** deux sources ; mettre à jour `last_confirmed_on` et `confidence`.

## Tester

```bash
pytest tests/content
```

Puis ouvrir la fiche dans le navigateur : `/fiches/<slug>`.
