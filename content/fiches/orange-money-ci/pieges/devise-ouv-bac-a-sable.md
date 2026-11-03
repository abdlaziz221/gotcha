---
title: "Le bac à sable attend la devise fictive OUV, pas le XOF"
severity: major
environments: [sandbox, production]
api_version: v1
error_codes: []
publication: draft
verified_by: null
last_confirmed_on: 2026-11-03
sources:
  - title: "SDK PHP Orange Money (Foris-master) : exemple de paiement"
    url: https://github.com/Foris-master/orange-money-sdk
    accessed_on: 2026-11-03
  - title: "Bow Payment : passerelle Orange Money Côte d'Ivoire, devise par défaut"
    url: https://github.com/bowphp/payment/blob/main/src/Gateway/IvoryCost/Orange/OrangePayment.php
    accessed_on: 2026-11-03
  - title: "Intégration open source en Côte d'Ivoire : paiement en XOF"
    url: https://github.com/ouattaraibd/moncaisson/blob/master/location/payments/orange_money_ci.py
    accessed_on: 2026-11-03
  - title: "Intégration open source en Côte d'Ivoire : paiement en OUV"
    url: https://github.com/refontiq-dotcom/Sejoura/blob/main/src/lib/payments/orange-money.ts
    accessed_on: 2026-11-03
---

## Symptôme

La création du paiement est refusée dans le [[bac-a-sable]] alors que la devise envoyée, `XOF`, est bien celle de la Côte d'Ivoire. Ou l'inverse : tout marche en test, puis les paiements échouent le jour du passage en [[production]].

## Cause

Dans le bac à sable (adresse `…/orange-money-webpay/dev/v1/…`), les bibliothèques consultées envoient par défaut la devise fictive `OUV`, y compris une passerelle écrite pour la Côte d'Ivoire. Une intégration ivoirienne open source envoie `XOF` à l'adresse de production `…/ci/v1/…`, mais une autre garde `OUV` à cette même adresse. La référence officielle n'est lisible qu'avec un compte connecté : la devise de production reste à confirmer.

## Solution

Lisez la devise dans une [[variable-environnement]], changée en même temps que l'adresse :

```python
OM_CURRENCY = os.environ["OM_CURRENCY"]  # "OUV" en bac à sable, "XOF" en production (à confirmer)
```

Au passage en production, faites un premier paiement réel de petit montant avant d'ouvrir le service.
