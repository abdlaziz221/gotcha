---
title: "Aucun bac à sable public : on teste avec un vrai compte"
severity: major
environments: [sandbox, production]
api_version: null
error_codes: []
publication: published
verified_by: AliouLoum
last_confirmed_on: 2026-11-10
sources:
  - title: "Documentation officielle de l'API Wave Business"
    url: https://docs.wave.com/business
    accessed_on: 2026-11-10
  - title: "Documentation officielle de l'API Wave Checkout"
    url: https://docs.wave.com/checkout
    accessed_on: 2026-11-10
  - title: "Documentation officielle des webhooks Wave"
    url: https://docs.wave.com/webhook
    accessed_on: 2026-11-10
---

## Symptôme

On cherche un [[bac-a-sable]] Wave pour développer, et on n'en trouve pas.

## Cause

La documentation officielle ne mentionne aucun bac à sable, ni pour l'API Business ni pour l'API Checkout. La [[cle-api|clé d'API]] se crée dans le portail Wave Business, et seuls ses administrateurs y ont accès. Elle est liée à un seul compte marchand réel.

## Solution

Ouvrez le compte Wave Business tôt. En attendant, isolez l'appel à Wave derrière une interface de votre code pour le simuler dans vos tests, puis testez en production avec de petits montants.

Votre [[webhook]] peut tout de même être testé sans payer : le portail Wave Business envoie un événement de test (`test.test_event`) à l'adresse enregistrée.
