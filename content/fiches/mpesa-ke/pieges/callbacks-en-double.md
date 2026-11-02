---
title: "Le même callback peut arriver plusieurs fois"
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
  - title: "Les erreurs courantes de l'API M-Pesa"
    url: https://sellio.co.ke/blog/common-mpesa-api-errors-and-solutions
    accessed_on: 2026-10-28
---

## Symptôme

Une commande est livrée deux fois, ou un solde est crédité deux fois pour un seul paiement.

## Cause

Le [[callback]] peut être renvoyé, par exemple quand votre serveur a répondu trop lentement.

## Solution

Rendez le traitement [[idempotence|idempotent]] : enregistrez l'identifiant de la transaction (CheckoutRequestID) avec une contrainte d'unicité, et ignorez un callback déjà traité.
