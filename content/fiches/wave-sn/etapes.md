## Ouvrir un compte Wave Business

L'accès à l'API passe par un compte Wave Business. Prévoyez ce délai dès le début du projet.

## Créer une clé d'API

La [[cle-api|clé d'API]] se crée dans la section développeur du portail Wave Business, réservée aux administrateurs. Elle ne s'affiche en entier qu'une fois : copiez-la tout de suite dans une [[variable-environnement]], jamais dans le code ni dans le navigateur.

## Créer le paiement

Appelez `POST https://api.wave.com/v1/checkout/sessions` avec l'en-tête `Authorization: Bearer <clé>`, le montant (`amount`, en texte), la devise `XOF`, et les adresses `success_url` et `error_url`. Ajoutez `client_reference` pour retrouver votre commande.

La réponse contient `wave_launch_url` : laissez le navigateur du client ouvrir cette adresse, qui lance l'application Wave.

## Recevoir le résultat

Enregistrez un [[webhook]] dans le portail Wave Business. Wave y envoie `checkout.session.completed` quand le paiement réussit, et `checkout.session.payment_failed` quand il échoue. Ne livrez que sur cet événement ou sur une lecture de la session (`GET /v1/checkout/sessions/:id`) dont `payment_status` vaut `succeeded`.
