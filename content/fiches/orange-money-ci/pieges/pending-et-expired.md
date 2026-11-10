---
title: "PENDING n'est pas un échec : relancer le paiement peut débiter deux fois"
severity: major
confidence: sourced
environments: [sandbox, production]
api_version: v1
error_codes: []
publication: published
verified_by: TechwithXalifa
last_confirmed_on: 2026-11-10
sources:
  - title: "SDK PHP Orange Money (Foris-master) : signification des statuts"
    url: https://github.com/Foris-master/orange-money-sdk
    accessed_on: 2026-11-10
  - title: "Centipid Billing : passerelle Orange Money, dépannage (documentation d'un intégrateur)"
    url: https://docs.centipidbilling.com/billing/payment-gateways/orange-money
    accessed_on: 2026-11-10
---

## Symptôme

Un client est débité deux fois pour la même commande. Ou un paiement reste « en attente » et le site ne sait pas quoi en faire.

## Cause

Le statut d'un paiement prend l'une de ces valeurs :

- `INITIATED` : le client n'a encore rien saisi ;
- `PENDING` : le client a confirmé, Orange traite le paiement ;
- `SUCCESS` : le paiement est fait ;
- `FAILED` : le paiement a échoué ;
- `EXPIRED` : le client a confirmé trop tard, après la fin de validité du paiement.

`PENDING` veut donc dire « en cours », pas « raté ». Proposer de payer à nouveau à ce moment-là peut débiter le client deux fois. Les sources consultées ne donnent pas la durée de validité d'un paiement.

Même API Web Payment qu'au Sénégal (voir « Les clés et l'adresse du Sénégal ne servent pas en Côte d'Ivoire ») : ce piège reprend celui de la fiche Sénégal, avec les mêmes sources, à confirmer sur le bac à sable ivoirien.

## Solution

- `INITIATED` ou `PENDING` : revérifiez le statut un peu plus tard ; ne proposez pas de repayer.
- `EXPIRED` ou `FAILED` : créez une **nouvelle tentative**, avec un nouvel `order_id` et son propre `pay_token`, rattachée à la même commande. Ne réutilisez pas l'`order_id` de la tentative précédente, et gardez son `pay_token` : il sert encore à vérifier cette tentative-là.
- Rendez la livraison [[idempotence|idempotente]] : un même paiement réussi ne doit livrer qu'une fois, même s'il est vérifié plusieurs fois.
