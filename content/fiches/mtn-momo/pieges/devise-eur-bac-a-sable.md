---
title: "Le bac à sable n'accepte que l'EUR"
severity: major
confidence: sourced
environments: [sandbox]
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
  - title: "momoapi-java : client Java de l'API MTN MoMo"
    url: https://github.com/regisbamba/momoapi-java
    accessed_on: 2026-11-10
  - title: "Forum MTN MoMo : configuration de production"
    url: https://momodevelopercommunity.mtn.com/how-to-59/momo-api-production-configuration-101
    published_on: 2023-08-02
    accessed_on: 2026-11-10
---

## Symptôme

Un paiement en XOF, GHS ou UGX échoue dans le bac à sable, alors que le même code est correct.

## Cause

Le [[bac-a-sable]] MTN MoMo n'accepte que la devise EUR. La [[production]] utilise la devise locale du pays : XOF en Côte d'Ivoire et au Bénin, GHS au Ghana, UGX en Ouganda, XAF au Cameroun.

## Solution

Rendez la devise configurable par [[variable-environnement]] : `EUR` dans le bac à sable, la devise du pays en production. Ne la codez jamais en dur.
