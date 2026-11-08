## Devenir marchand Orange Money

Web Payment est réservé aux marchands Orange Money. Inscrivez l'entreprise dans une agence Orange du Sénégal, avec ses documents officiels (registre du commerce notamment). Commencez dès le premier jour : c'est l'étape la plus longue.

## Créer l'application sur le portail développeur

Créez un compte sur developer.orange.com, puis une application abonnée à Web Payment. Notez les trois secrets : consumer key, consumer secret et merchant key. Rangez-les dans des [[variable-environnement|variables d'environnement]] côté serveur, jamais dans le navigateur.

La référence technique détaillée n'est lisible qu'une fois connecté au portail.

## Obtenir un jeton d'accès

Échangez la consumer key et le consumer secret contre un [[jeton-acces]] : `POST https://api.orange.com/oauth/v3/token`, avec `grant_type=client_credentials` et l'en-tête `Authorization: Basic …`. Gardez le jeton jusqu'à son expiration, indiquée par `expires_in` dans la réponse.

## Créer un paiement dans le bac à sable

Dans le [[bac-a-sable]], appelez `POST https://api.orange.com/orange-money-webpay/dev/v1/webpayment` avec la merchant key, la devise `OUV`, un `order_id`, le montant, les adresses `return_url`, `cancel_url` et `notif_url`, et la langue.

La réponse contient `payment_url`, la page d'Orange où envoyer le client, et `pay_token`. Enregistrez le `pay_token` avec la commande.

## Vérifier le statut avant de livrer

Au retour du client et à chaque notification, appelez `…/v1/transactionstatus` avec l'`order_id`, le montant et le `pay_token`. Ne livrez que sur `SUCCESS` ; sur `PENDING`, revérifiez plus tard.

## Passer en production

Changez ensemble les clés, le code pays dans l'adresse (`dev` devient `sn`) et la devise. Faites un premier paiement réel de petit montant avant d'ouvrir le service.
