---
title: "Le bac à sable n'accepte que l'EUR"
severity: major
environments: [sandbox]
api_version: v1_0
error_codes: []
publication: draft
verified_by: null
last_confirmed_on: 2026-10-28
sources:
  - title: "Forum MTN MoMo : clés, bac à sable et production"
    url: https://momodevelopercommunity.mtn.com/how-to-59/understanding-momo-open-api-keys-sandbox-and-production-455
    accessed_on: 2026-10-28
  - title: "McTaba : tutoriel de l'API MTN MoMo pour débutants"
    url: https://mctaba.com/learn/uganda/mtn-momo-api-tutorial-beginners-uganda
    accessed_on: 2026-10-28
---

## Symptôme

Un paiement en XOF, GHS ou UGX échoue dans le bac à sable, alors que le même code est correct.

## Cause

Le [[bac-a-sable]] MTN MoMo n'accepte que la devise EUR. La [[production]] utilise la devise locale du pays.

## Solution

Rendez la devise configurable par [[variable-environnement]] : `EUR` dans le bac à sable, la devise du pays en production. Ne la codez jamais en dur.
