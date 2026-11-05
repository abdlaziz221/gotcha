---
title: "Trois clés différentes : la merchant key n'est pas la consumer key"
severity: major
environments: [sandbox, production]
api_version: v1
error_codes: []
publication: draft
verified_by: null
last_confirmed_on: 2026-11-03
sources:
  - title: "Centipid Billing : passerelle Orange Money, identifiants (documentation d'un intégrateur)"
    url: https://docs.centipidbilling.com/billing/payment-gateways/orange-money
    accessed_on: 2026-11-03
  - title: "SDK PHP Orange Money (Foris-master) : configuration"
    url: https://github.com/Foris-master/orange-money-sdk
    accessed_on: 2026-11-03
  - title: "Kolonell : intégration Orange Money Sénégal pas à pas (blog, non officiel)"
    url: https://kolonell.com/fr/blog/orange-money-senegal-api-integration-pas-a-pas-2026
    accessed_on: 2026-11-03
---

## Symptôme

Le [[jeton-acces]] est bien obtenu, mais la création du paiement est refusée.

## Cause

Web Payment demande trois secrets, qui viennent de l'application créée sur le portail développeur d'Orange :

- la **consumer key** et le **consumer secret** servent seulement à obtenir le jeton d'accès ;
- la **merchant key**, propre à Web Payment, part dans le corps de chaque paiement (champ `merchant_key`).

Une documentation d'intégrateur cite comme cause fréquente de refus une merchant key qui n'est pas la clé Web Payment.

Même API Web Payment qu'au Sénégal (voir « Les clés et l'adresse du Sénégal ne servent pas en Côte d'Ivoire ») : ce piège reprend celui de la fiche Sénégal, avec les mêmes sources, à confirmer sur le bac à sable ivoirien.

## Solution

Gardez les trois valeurs dans trois [[variable-environnement|variables d'environnement]] distinctes, côté serveur uniquement :

```python
auth = base64.b64encode(f"{CONSUMER_KEY}:{CONSUMER_SECRET}".encode()).decode()
jeton = post(
    "https://api.orange.com/oauth/v3/token",
    headers={"Authorization": f"Basic {auth}"},
    data={"grant_type": "client_credentials"},
)["access_token"]
paiement = post(
    f"{base}/webpayment",
    headers={"Authorization": f"Bearer {jeton}"},
    json={
        "merchant_key": MERCHANT_KEY,
        "order_id": "<VOTRE_TENTATIVE>",
        # puis les autres champs du paiement : montant, devise, adresses de retour
    },
)
```
