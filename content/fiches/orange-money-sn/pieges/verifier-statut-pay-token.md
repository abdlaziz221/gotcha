---
title: "Le retour sur return_url ne prouve pas le paiement : gardez le pay_token"
severity: blocking
environments: [sandbox, production]
api_version: v1
error_codes: []
publication: published
verified_by: AliouLoum
last_confirmed_on: 2026-11-10
sources:
  - title: "SDK PHP Orange Money (Foris-master) : vérification du statut"
    url: https://github.com/Foris-master/orange-money-sdk
    accessed_on: 2026-11-10
  - title: "Bow Payment : vérification d'une transaction Orange Money"
    url: https://github.com/bowphp/payment/blob/main/src/Gateway/IvoryCost/Orange/OrangeGateway.php
    accessed_on: 2026-11-10
  - title: "Centipid Billing : passerelle Orange Money (documentation d'un intégrateur)"
    url: https://docs.centipidbilling.com/billing/payment-gateways/orange-money
    accessed_on: 2026-11-10
  - title: "Kolonell : guide technique Orange Money Web Payment (blog, non officiel)"
    url: https://kolonell.com/en/blog/orange-money-api-web-payment-integration-guide-2026
    accessed_on: 2026-11-10
---

## Symptôme

Une commande est livrée alors que le client n'a pas payé. Ou, à l'inverse, on ne peut plus vérifier un paiement parce qu'une des valeurs demandées n'a pas été enregistrée.

## Cause

Le retour du client sur `return_url` ne dit pas si le paiement a réussi. Les intégrations consultées relisent l'état du paiement auprès d'Orange avant de livrer.

Cette lecture (`…/v1/transactionstatus`) demande **trois** valeurs : l'`order_id` de la commande, le montant (`amount`) et le `pay_token`. Or le `pay_token` arrive dans la réponse à la création du paiement : il faut l'enregistrer à ce moment-là.

## Solution

1. Chaque paiement est une **tentative** rattachée à la commande, avec son propre `order_id` (voir le piège sur les statuts). À sa création, enregistrez cet `order_id`, le montant et le `pay_token`, et mettez l'`order_id` dans `return_url` (par exemple `…/paiement/retour?tentative=<order_id>`) : au retour du client, vous savez quelle tentative vérifier.
2. Au retour du client, et à chaque notification reçue, demandez le statut :

   ```python
   statut = post(
       f"{base}/transactionstatus",
       headers={"Authorization": f"Bearer {jeton}"},
       json={
           "order_id": tentative.order_id,
           "amount": tentative.montant,
           "pay_token": tentative.pay_token,
       },
   )["status"]
   ```

3. Ne livrez que si le statut vaut `SUCCESS`. `INITIATED` et `PENDING` ne sont pas des échecs : la tentative est encore ouverte, revérifiez plus tard.
4. Si le client ferme son navigateur et que la notification n'arrive pas, rien ne déclenche la vérification. Une tâche de rattrapage doit donc relire régulièrement le statut des tentatives encore ouvertes, jusqu'à `SUCCESS`, `FAILED` ou `EXPIRED`.
