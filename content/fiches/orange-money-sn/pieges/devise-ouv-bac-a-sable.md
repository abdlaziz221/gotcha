---
title: "Le bac à sable attend la devise fictive OUV, pas le XOF"
severity: major
environments: [sandbox, production]
api_version: v1
error_codes: []
publication: published
verified_by: AliouLoum
last_confirmed_on: 2026-11-10
sources:
  - title: "SDK PHP Orange Money (Foris-master) : exemple de paiement"
    url: https://github.com/Foris-master/orange-money-sdk
    accessed_on: 2026-11-10
  - title: "Bow Payment : passerelle Orange Money, devise par défaut"
    url: https://github.com/bowphp/payment/blob/main/src/Gateway/IvoryCost/Orange/OrangePayment.php
    accessed_on: 2026-11-10
  - title: "Kolonell : guide technique Orange Money Web Payment (blog, non officiel)"
    url: https://kolonell.com/en/blog/orange-money-api-web-payment-integration-guide-2026
    accessed_on: 2026-11-10
  - title: "Kolonell : intégration Orange Money Sénégal pas à pas, qui garde OUV (blog, non officiel)"
    url: https://kolonell.com/fr/blog/orange-money-senegal-api-integration-pas-a-pas-2026
    accessed_on: 2026-11-10
---

## Symptôme

La création du paiement est refusée dans le [[bac-a-sable]] alors que la devise envoyée, `XOF`, est bien celle du Sénégal. Ou l'inverse : tout marche en test, puis les paiements échouent le jour du passage en [[production]].

## Cause

Dans le bac à sable (adresse `…/orange-money-webpay/dev/v1/…`), les intégrations publiques envoient la devise fictive `OUV` : c'est la valeur par défaut de deux bibliothèques indépendantes.

En production, il faut la vraie devise. Un guide d'intégration de 2026 indique `XOF`, et il présente l'inversion des deux devises comme l'erreur la plus fréquente au lancement. D'autres exemples publics gardent pourtant `OUV` : la référence officielle n'est lisible qu'avec un compte connecté, donc ce point reste à confirmer.

## Solution

Ne codez jamais la devise en dur. Lisez-la dans une [[variable-environnement]], changée en même temps que l'adresse de l'API :

```python
OM_CURRENCY = os.environ["OM_CURRENCY"]  # "OUV" en bac à sable, "XOF" en production (à confirmer)
```

Au passage en production, faites un premier paiement réel de petit montant avant d'ouvrir le service.
