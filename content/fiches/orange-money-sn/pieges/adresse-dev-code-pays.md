---
title: "L'adresse de l'API change entre bac à sable et production : « dev » devient « sn »"
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
  - title: "WWmcp : client Orange Money, une adresse par pays"
    url: https://github.com/theYahia/WWmcp/blob/main/servers/orange-money/src/client.ts
    accessed_on: 2026-11-03
  - title: "Kolonell : guide technique Orange Money Web Payment (blog, non officiel)"
    url: https://kolonell.com/en/blog/orange-money-api-web-payment-integration-guide-2026
    accessed_on: 2026-11-03
---

## Symptôme

Avec les clés de [[production]], les appels échouent alors qu'ils marchaient en test. Ou bien les clients sont envoyés vers une page de paiement de test.

## Cause

Le chemin de l'API contient l'environnement :

- [[bac-a-sable]] : `https://api.orange.com/orange-money-webpay/dev/v1/webpayment`
- production au Sénégal : `https://api.orange.com/orange-money-webpay/sn/v1/webpayment`

Le même segment change pour la vérification du statut (`…/transactionstatus`). Le [[jeton-acces]], lui, se demande toujours à la même adresse : `https://api.orange.com/oauth/v3/token`. Un guide d'intégration le résume : ne mélangez jamais des clés de test et l'adresse de production.

## Solution

Lisez le code pays dans une [[variable-environnement]] et changez ensemble les clés, la devise et le code pays :

```python
OM_COUNTRY = os.environ["OM_COUNTRY"]  # "dev" en bac à sable, "sn" en production
base = f"https://api.orange.com/orange-money-webpay/{OM_COUNTRY}/v1"
```
