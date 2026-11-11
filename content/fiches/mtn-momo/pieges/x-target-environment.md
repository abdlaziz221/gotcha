---
title: "L'en-tête X-Target-Environment est obligatoire, même dans le bac à sable"
severity: blocking
confidence: sourced
environments: [sandbox, production]
api_version: v1_0
error_codes: []
publication: published
verified_by: TechwithXalifa
last_confirmed_on: 2026-11-10
sources:
  - title: "Tester l'API Collection de MTN MoMo dans le bac à sable avec Postman (gist)"
    url: https://gist.github.com/chaiwa-berian/5294fdf1360247cf4561c95c8fa740d4
    accessed_on: 2026-11-10
  - title: "Bedigit : guide du module de paiement MTN MoMo"
    url: https://bedigit.com/support/larapen/add-on-guides/larapen-momo-add-on-guide
    accessed_on: 2026-11-10
  - title: "Forum MTN MoMo : configuration de production"
    url: https://momodevelopercommunity.mtn.com/how-to-59/momo-api-production-configuration-101
    published_on: 2023-08-02
    accessed_on: 2026-11-10
---

## Symptôme

L'appel `requesttopay` n'aboutit pas, alors que le jeton et la clé d'abonnement sont bons.

## Cause

L'[[en-tete-http|en-tête]] `X-Target-Environment` manque ou n'a pas la bonne valeur. Il fait partie des en-têtes à envoyer sur les appels de l'API Collections, et sa valeur change avec l'environnement.

## Solution

Lisez la valeur dans une [[variable-environnement]] :

- dans le [[bac-a-sable]] : `sandbox` ;
- en production : la valeur du pays, par exemple `mtnivorycoast` (Côte d'Ivoire), `mtnghana`, `mtnuganda`, `mtncameroon` ou `mtnbenin`.
