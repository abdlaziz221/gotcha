## Ouvrir un compte Wave Business

L'accès à l'API passe par un compte Wave Business. Prévoyez ce délai dès le début du projet.

## Créer une clé d'API

La [[cle-api|clé d'API]] se crée dans la section développeur du portail Wave Business, réservée aux administrateurs. Elle ne s'affiche en entier qu'une fois : copiez-la tout de suite dans une [[variable-environnement]], jamais dans le code ni dans le navigateur.

## Créer le paiement

Appelez `POST https://api.wave.com/v1/checkout/sessions` avec l'en-tête `Authorization: Bearer <clé>`, le montant (`amount`, en texte), la devise `XOF`, et les adresses `success_url` et `error_url`. Ajoutez `client_reference` pour retrouver votre commande.

La réponse contient `wave_launch_url` : laissez le navigateur du client ouvrir cette adresse, qui lance l'application Wave.

## Recevoir le résultat

Enregistrez un [[webhook]] dans le portail Wave Business, en choisissant la sécurité « Signing Secret », recommandée en production. Wave y envoie `checkout.session.completed` quand le paiement réussit, et `checkout.session.payment_failed` quand il échoue.

Ne livrez jamais sur une notification non vérifiée : n'importe qui peut appeler votre adresse. Faites l'une de ces deux vérifications, ou les deux :

- **Vérifier la signature.** L'en-tête `Wave-Signature` vaut `t=<horodatage>,v1=<signature>`. Recalculez un HMAC-SHA256 de l'horodatage suivi du corps brut de la requête, avec le secret du webhook, et comparez-le à `v1`. Rejetez la requête si la signature diffère ou si l'horodatage a plus de 5 minutes.
- **Relire la session.** Appelez `GET /v1/checkout/sessions/:id` avec votre clé d'API, et ne livrez que si `payment_status` vaut `succeeded`.

Répondez tout de suite par un code 2xx, puis traitez l'événement : sinon, Wave le renvoie pendant 3 jours. Un même événement peut arriver plusieurs fois, ou pas du tout : gardez son `id` pour ne livrer qu'une fois ([[idempotence]]), et relisez la session au retour du client sur `success_url`.
