---
title: "Les clés et l'adresse du Sénégal ne servent pas en Côte d'Ivoire"
severity: major
environments: [production]
api_version: v1
error_codes: []
publication: draft
verified_by: null
last_confirmed_on: 2026-11-03
sources:
  - title: "Kolonell : intégration Orange Money Sénégal pas à pas, questions fréquentes (blog, non officiel)"
    url: https://kolonell.com/fr/blog/orange-money-senegal-api-integration-pas-a-pas-2026
    accessed_on: 2026-11-03
  - title: "SDK PHP Orange Money (Foris-master) : un code pays par déploiement"
    url: https://github.com/Foris-master/orange-money-sdk
    accessed_on: 2026-11-03
---

## Symptôme

Un site qui encaisse déjà au Sénégal ouvre la Côte d'Ivoire avec les mêmes réglages : les paiements ivoiriens échouent.

## Cause

L'API Web Payment est la même d'un pays à l'autre, mais chaque pays a ses propres identifiants marchands et sa propre adresse (code pays `ci` au lieu de `sn`). Les bibliothèques consultées configurent donc un pays par intégration ; un guide sénégalais parle d'« un connecteur par pays ».

**À vérifier avant publication :** une passerelle open source (Bow Payment, code de sa passerelle Sénégal) affirme au contraire que les adresses et l'authentification sont les mêmes d'un pays à l'autre. Cette contradiction touche aussi les adresses de production des fiches Sénégal et Côte d'Ivoire : elle se lève avec un compte marchand ivoirien.

## Solution

Traitez chaque pays comme une intégration à part : son compte marchand, ses trois clés et son code pays, rangés dans des [[variable-environnement|variables d'environnement]] distinctes. Choisissez le pays d'après la commande, jamais par défaut :

```python
PAYS = {"SN": "sn", "CI": "ci"}
base = f"https://api.orange.com/orange-money-webpay/{PAYS[commande.pays]}/v1"
```
