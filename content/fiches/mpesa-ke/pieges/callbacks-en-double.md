---
title: "Le même callback peut arriver plusieurs fois"
severity: major
confidence: sourced
environments: [sandbox, production]
api_version: null
error_codes: []
publication: published
verified_by: TechwithXalifa
last_confirmed_on: 2026-11-09
sources:
  - title: "McTaba : paiements échoués et en double avec M-Pesa"
    url: https://mctaba.com/learn/mpesa/failed-and-duplicate-payments
    accessed_on: 2026-11-09
  - title: "django-mpesa (Mainfinity) : callbacks"
    url: https://mainfinity-django-mpesa.readthedocs.io/en/latest/callbacks/
    accessed_on: 2026-11-09
---

## Symptôme

Une commande est livrée deux fois, ou un solde est crédité deux fois pour un seul paiement.

## Cause

Si votre serveur répond trop lentement au [[callback]], ou plante avant de répondre, Safaricom considère l'envoi comme raté et le renvoie.

## Solution

Répondez tout de suite avec un statut HTTP 200, puis faites le traitement long (SMS, mise à jour du solde) ensuite. Rendez ce traitement [[idempotence|idempotent]] : enregistrez le `CheckoutRequestID` avec une contrainte d'unicité en base, et ignorez un callback déjà traité.
