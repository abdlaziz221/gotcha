## Créer un compte et s'abonner au produit Collections

Sur le portail développeur MTN MoMo, créez un compte puis abonnez-vous au produit **Collections**. Vous obtenez une [[cle-api|clé d'abonnement]], envoyée dans l'en-tête `Ocp-Apim-Subscription-Key`.

## Créer un utilisateur et une clé d'API dans le bac à sable

Dans le [[bac-a-sable]], l'utilisateur d'API et sa clé se créent soi-même, par l'API de provisionnement : `POST /v1_0/apiuser`, puis `POST /v1_0/apiuser/{id}/apikey`.

## Obtenir un jeton d'accès

Appelez `POST /collection/token/` avec l'utilisateur et la clé d'API en authentification Basic. Le [[jeton-acces|jeton]] expire : prévoyez de le renouveler.

## Demander le paiement

Appelez `POST /collection/v1_0/requesttopay` avec les en-têtes `Authorization`, `X-Reference-Id` (un UUID que vous générez), `X-Target-Environment` et `Ocp-Apim-Subscription-Key`.

## Vérifier le résultat

Le paiement est asynchrone : interrogez `GET /collection/v1_0/requesttopay/{X-Reference-Id}`, ou attendez le [[callback]].
