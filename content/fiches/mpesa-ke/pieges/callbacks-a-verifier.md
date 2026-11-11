---
title: "Un callback reçu ne prouve pas que le paiement a eu lieu"
severity: major
confidence: sourced
environments: [production]
api_version: null
error_codes: []
publication: published
verified_by: TechwithXalifa
last_confirmed_on: 2026-11-09
sources:
  - title: "Les pièges de l'API Daraja (M-Pesa)"
    url: https://ml.co.ke/posts/mpesa-daraja-api-pitfalls/
    published_on: 2026-09-03
    accessed_on: 2026-11-09
  - title: "Daraja (bibliothèque Elixir) : Daraja.Express.Callback"
    url: https://daraja.hexdocs.pm/Daraja.Express.Callback.html
    accessed_on: 2026-11-09
  - title: "McTaba : le STK Push expliqué"
    url: https://mctaba.com/learn/mpesa/stk-push-explained
    accessed_on: 2026-11-09
---

## Symptôme

Des commandes sont marquées payées alors qu'aucun argent n'est arrivé.

## Cause

L'adresse du [[callback]] est publique, et Daraja ne signe pas ses callbacks : n'importe qui peut y envoyer un faux résultat avec `ResultCode: 0` (succès). Un callback peut aussi ne jamais arriver.

## Solution

Ne livrez jamais sur la foi du callback seul :

1. vérifiez que son `CheckoutRequestID` correspond à une demande que vous avez vous-même envoyée, et pas encore traitée ;
2. confirmez le résultat en demandant le statut à Safaricom (requête STK Push Query, `/mpesa/stkpushquery/v1/query`, avec le `CheckoutRequestID`) ;
3. ajoutez un secret difficile à deviner dans l'URL du callback.

La même requête de statut règle aussi le cas du callback qui n'arrive jamais.
