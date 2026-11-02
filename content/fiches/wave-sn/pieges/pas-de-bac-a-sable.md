---
title: "Aucun bac à sable public : on teste avec un vrai compte"
severity: major
environments: [sandbox, production]
api_version: null
error_codes: []
publication: draft
verified_by: null
last_confirmed_on: 2026-10-28
sources:
  - title: "Documentation officielle de l'API Wave Business"
    url: https://docs.wave.com/business
    accessed_on: 2026-10-28
---

## Symptôme

On cherche un [[bac-a-sable]] Wave pour développer, et on n'en trouve pas.

## Cause

La documentation officielle ne mentionne aucun bac à sable : la clé d'API est réservée à un compte Wave Business, côté administrateur.

## Solution

Ouvrez le compte Wave Business tôt. En attendant, isolez l'appel à Wave derrière une interface de votre code pour le simuler dans vos tests, puis testez en production avec de petits montants.
