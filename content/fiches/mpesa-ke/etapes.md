## Créer une application Daraja

Sur le portail Daraja, créez une application : vous obtenez une consumer key et un consumer secret. Ce sont des [[cle-api|clés d'API]] : gardez-les hors du code.

## Obtenir un jeton OAuth

Échangez la consumer key et le consumer secret contre un [[jeton-acces|jeton d'accès]]. Il expire : mettez-le en cache et renouvelez-le à temps.

## Lancer un paiement STK Push

L'API STK Push affiche une demande de paiement sur le téléphone du client, qui la valide avec son code M-Pesa.

## Recevoir et vérifier le callback

Safaricom appelle votre [[callback]] avec le résultat. Vérifiez-le avant de livrer, et traitez chaque paiement une seule fois ([[idempotence]]).
