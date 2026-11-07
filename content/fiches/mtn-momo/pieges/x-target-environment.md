---
title: "L'en-tête X-Target-Environment est obligatoire, même dans le bac à sable"
severity: blocking
environments: [sandbox, production]
api_version: v1_0
error_codes: ["400", "500"]
publication: draft
verified_by: null
last_confirmed_on: 2026-10-28
sources:
  - title: "Forum MTN MoMo : X-Target-Environment et erreur 400"
    url: https://momodevelopercommunity.mtn.com/momo-api-sand-box-q-a-6/x-target-environment-251
    published_on: 2024-07-24
    accessed_on: 2026-10-28
  - title: "Forum MTN MoMo : clés, bac à sable et production"
    url: https://momodevelopercommunity.mtn.com/how-to-59/understanding-momo-open-api-keys-sandbox-and-production-455
    published_on: 2026-01-07
    accessed_on: 2026-10-28
---

## Symptôme

L'appel `requesttopay` échoue sans message clair : erreur 400 ou 500 selon les témoignages.

## Cause

L'[[en-tete-http|en-tête]] `X-Target-Environment` manque ou n'a pas la bonne valeur. Il est obligatoire sur les appels de l'API Collections.

## Solution

Envoyez `X-Target-Environment: sandbox` dans le [[bac-a-sable]]. En production, utilisez la valeur propre à votre pays, fournie par MTN.

> À vérifier (tâche K3) : le code d'erreur exact renvoyé quand l'en-tête manque.
