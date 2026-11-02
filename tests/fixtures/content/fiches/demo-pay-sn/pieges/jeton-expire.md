---
title: "Le jeton expire au bout d'une heure"
severity: major
environments: [sandbox, production]
api_version: v1
error_codes: ["E42"]
publication: published
verified_by: testeur
last_confirmed_on: 2026-10-01
sources:
  - title: Source de test
    url: https://example.com/jeton
    accessed_on: 2026-10-01
---

## Symptôme

Les appels échouent après une heure.

## Cause

Le [[jeton-acces|jeton]] expire.

## Solution

Le renouveler avant expiration.
