---
title: "L'adresse de l'API change entre bac à sable et production : « dev » devient « ci »"
severity: major
environments: [sandbox, production]
api_version: v1
error_codes: []
publication: draft
verified_by: null
last_confirmed_on: 2026-11-03
sources:
  - title: "SDK PHP Orange Money (Foris-master) : adresses de l'API"
    url: https://github.com/Foris-master/orange-money-sdk/blob/master/src/Api.php
    accessed_on: 2026-11-03
  - title: "Bow Payment : adresse du bac à sable Orange Money"
    url: https://github.com/bowphp/payment/blob/main/src/Gateway/IvoryCost/Orange/OrangePayment.php
    accessed_on: 2026-11-03
  - title: "Intégration open source en Côte d'Ivoire : création du paiement"
    url: https://github.com/ouattaraibd/moncaisson/blob/master/location/payments/orange_money_ci.py
    accessed_on: 2026-11-03
  - title: "Intégration open source en Côte d'Ivoire : vérification du statut"
    url: https://github.com/kolo01/testPhillipe/blob/main/app/Http/Traits/Orange/check_status.php
    accessed_on: 2026-11-03
---

## Symptôme

Avec les clés de [[production]], les appels échouent alors qu'ils marchaient en test. Ou bien les clients sont envoyés vers une page de paiement de test.

## Cause

Le chemin de l'API contient l'environnement :

- [[bac-a-sable]] : `https://api.orange.com/orange-money-webpay/dev/v1/webpayment`
- production en Côte d'Ivoire : `https://api.orange.com/orange-money-webpay/ci/v1/webpayment`

Le même segment change pour la vérification du statut (`…/transactionstatus`). Le [[jeton-acces]] se demande toujours à `https://api.orange.com/oauth/v3/token`.

## Solution

Lisez le code pays dans une [[variable-environnement]] et changez ensemble les clés, la devise et le code pays :

```python
OM_COUNTRY = os.environ["OM_COUNTRY"]  # "dev" en bac à sable, "ci" en production
base = f"https://api.orange.com/orange-money-webpay/{OM_COUNTRY}/v1"
```
