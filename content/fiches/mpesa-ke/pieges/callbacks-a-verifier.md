---
title: "Un callback reçu ne prouve pas que le paiement a eu lieu"
severity: major
environments: [production]
api_version: null
error_codes: []
publication: draft
verified_by: null
last_confirmed_on: 2026-10-28
sources:
  - title: "Les pièges de l'API Daraja (M-Pesa)"
    url: https://ml.co.ke/posts/mpesa-daraja-api-pitfalls/
    published_on: 2026-09-03
    accessed_on: 2026-10-28
---

## Symptôme

Des commandes sont marquées payées alors qu'aucun argent n'est arrivé.

## Cause

L'adresse du [[callback]] est publique : sans vérification, n'importe qui peut y envoyer un faux résultat de paiement.

## Solution

Avant de livrer, confirmez chaque paiement par une requête de statut auprès de Safaricom, et comparez le montant et la référence avec la commande. Utilisez une URL de callback difficile à deviner.
