---
title: "Le jeton OAuth expire au bout d'une heure"
severity: major
environments: [sandbox, production]
api_version: null
error_codes: []
publication: draft
verified_by: null
last_confirmed_on: 2026-10-28
sources:
  - title: "Les pièges de l'API Daraja (M-Pesa)"
    url: https://ml.co.ke/posts/mpesa-daraja-api-pitfalls/
    accessed_on: 2026-10-28
---

## Symptôme

Tout marche pendant les tests, puis les appels échouent en erreur d'authentification au bout d'environ une heure.

## Cause

Le [[jeton-acces|jeton d'accès]] Daraja n'est valable qu'une heure (3 600 secondes).

## Solution

Gardez le jeton en cache avec sa date d'expiration et renouvelez-le un peu avant, par exemple au bout de 55 minutes. Ne demandez pas un nouveau jeton à chaque appel.
