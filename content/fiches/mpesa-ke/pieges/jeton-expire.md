---
title: "Le jeton OAuth expire au bout d'une heure"
severity: major
confidence: sourced
environments: [sandbox, production]
api_version: null
error_codes: []
publication: published
verified_by: TechwithXalifa
last_confirmed_on: 2026-11-09
sources:
  - title: "django-daraja : API OAuth"
    url: https://django-daraja.readthedocs.io/en/latest/pages/apis/oauth.html
    accessed_on: 2026-11-09
  - title: "Safaricom Daraja API : obtenir un jeton d'accès (Authorization API)"
    url: https://dev.to/msnmongare/safaricom-daraja-api-authorization-api-guide-for-access-tokens-2kg1
    published_on: 2024-10-31
    accessed_on: 2026-11-09
---

## Symptôme

Tout marche pendant les tests, puis les appels échouent en erreur d'authentification au bout d'environ une heure.

## Cause

Le [[jeton-acces|jeton d'accès]] Daraja n'est valable qu'une heure : le champ `expires_in` de la réponse indique sa durée en secondes (environ 3 600).

## Solution

Gardez le jeton en cache avec sa date d'expiration, et renouvelez-le avant la fin, par exemple au bout de 50 minutes. Ne demandez pas un nouveau jeton à chaque appel.
