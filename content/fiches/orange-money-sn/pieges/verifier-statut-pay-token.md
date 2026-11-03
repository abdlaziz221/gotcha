---
title: "Le retour sur return_url ne prouve pas le paiement : gardez le pay_token"
severity: blocking
environments: [sandbox, production]
api_version: v1
error_codes: []
publication: draft
verified_by: null
last_confirmed_on: 2026-11-03
sources:
  - title: "SDK PHP Orange Money (Foris-master) : vérification du statut"
    url: https://github.com/Foris-master/orange-money-sdk
    accessed_on: 2026-11-03
  - title: "Bow Payment : vérification d'une transaction Orange Money"
    url: https://github.com/bowphp/payment/blob/main/src/Gateway/IvoryCost/Orange/OrangeGateway.php
    accessed_on: 2026-11-03
  - title: "Centipid Billing : passerelle Orange Money (documentation d'un intégrateur)"
    url: https://docs.centipidbilling.com/billing/payment-gateways/orange-money
    accessed_on: 2026-11-03
  - title: "Kolonell : guide technique Orange Money Web Payment (blog, non officiel)"
    url: https://kolonell.com/en/blog/orange-money-api-web-payment-integration-guide-2026
    accessed_on: 2026-11-03
---

## Symptôme

Une commande est livrée alors que le client n'a pas payé. Ou, à l'inverse, on ne peut plus vérifier un paiement parce qu'une des valeurs demandées n'a pas été enregistrée.

## Cause

Le retour du client sur `return_url` ne dit pas si le paiement a réussi. Les intégrations consultées relisent l'état du paiement auprès d'Orange avant de livrer.

Cette lecture (`…/v1/transactionstatus`) demande **trois** valeurs : l'`order_id` de la commande, le montant (`amount`) et le `pay_token`. Or le `pay_token` arrive dans la réponse à la création du paiement : il faut l'enregistrer à ce moment-là.

## Solution

1. À la création du paiement, enregistrez l'`order_id`, le montant et le `pay_token`.
2. Au retour du client, et à chaque notification reçue, demandez le statut :

   ```python
   statut = post(
       f"{base}/transactionstatus",
       headers=auth,
       json={"order_id": commande.id, "amount": commande.montant, "pay_token": commande.pay_token},
   )
   ```

3. Ne livrez que si le statut vaut `SUCCESS`.
