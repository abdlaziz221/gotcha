---
title: "Les clés et l'adresse du Sénégal ne servent pas en Côte d'Ivoire"
severity: major
confidence: sourced
environments: [production]
api_version: v1
error_codes: []
publication: published
verified_by: TechwithXalifa
last_confirmed_on: 2026-11-10
sources:
  - title: "Kolonell : intégration Orange Money Sénégal pas à pas, questions fréquentes (blog, non officiel)"
    url: https://kolonell.com/fr/blog/orange-money-senegal-api-integration-pas-a-pas-2026
    accessed_on: 2026-11-10
  - title: "SDK PHP Orange Money (Foris-master) : un code pays par déploiement"
    url: https://github.com/Foris-master/orange-money-sdk
    accessed_on: 2026-11-10
---

## Symptôme

Un site qui encaisse déjà au Sénégal ouvre la Côte d'Ivoire avec les mêmes réglages : les paiements ivoiriens échouent.

## Cause

L'API Web Payment est la même d'un pays à l'autre, mais chaque pays a ses propres identifiants marchands et sa propre adresse (code pays `ci` au lieu de `sn`). Les bibliothèques consultées configurent donc un pays par intégration ; un guide sénégalais parle d'« un connecteur par pays ».

Une passerelle open source (Bow Payment) affirme au contraire que les adresses et l'authentification sont les mêmes d'un pays à l'autre. Deux intégrations ivoiriennes open source utilisent pourtant le code `ci` dans l'adresse de production. Seul un compte marchand ivoirien permettra de trancher.

## Solution

Traitez chaque pays comme une intégration à part : son compte marchand, ses trois clés et son code pays, rangés dans des [[variable-environnement|variables d'environnement]] distinctes. Choisissez le pays d'après la commande, jamais par défaut :

```python
PAYS = {"SN": "sn", "CI": "ci"}
base = f"https://api.orange.com/orange-money-webpay/{PAYS[commande.pays]}/v1"
```
