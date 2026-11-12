---
title: "Le service est LIVE, mais son adresse publique ne répond pas"
severity: blocking
environments: [production]
api_version: null
error_codes: []
confidence: production
publication: draft
verified_by: null
last_confirmed_on: 2026-11-11
sources:
  - title: Retour de terrain, déploiement de Gotcha sur Datacloud Serverless Free
    author: abdlaziz221
    accessed_on: 2026-11-11
---

## Symptôme

La console affiche le service en LIVE et les journaux montrent que l'application a démarré, mais son adresse en `*.platform-systalink.com` ne répond pas : le navigateur finit par abandonner, sans aucune page d'erreur.

## Cause

Ici, la panne ne venait pas de l'application, mais de l'accès public de la plateforme : même un sous-domaine inventé en `*.platform-systalink.com` ne répondait pas, alors que la console platform.systalink.com restait joignable. Le statut LIVE dit seulement que le conteneur tourne.

## Solution

1. Testez depuis un autre réseau (données mobiles par exemple) pour écarter votre connexion.
2. Testez un sous-domaine inventé de `platform-systalink.com` : s'il ne répond pas non plus, la panne est du côté de la plateforme, inutile de modifier votre code.
3. Prévenez le support. Si le formulaire de ticket de la console échoue lui aussi, écrivez à l'adresse de contact de Systalink.
4. Pour une échéance proche (démonstration, soumission), gardez un second déploiement de secours ailleurs, configuré de la même façon.

## Pistes qui ont échoué

- Attendre un redémarrage du service : après celui de 08 h 55, il revient en LIVE, l'adresse reste muette.
- Changer de réseau ou de navigateur, passer par Tor : aucune différence.

## Preuve

10 novembre 2026, service Serverless Free à Dakar, construit par Docker depuis la branche `main`. Journaux : l'application démarre à 01 h 02, puis de nouveau à 01 h 18 et 08 h 55, sans qu'aucune requête n'y apparaisse. Depuis une connexion fibre, des données mobiles et Tor, aucune connexion n'aboutit sur les ports 80 et 443 de l'adresse du service, ni d'un sous-domaine inventé ; la console répond normalement. Le formulaire de ticket répond « La création du ticket a échoué ». L'adresse répond de nouveau le soir du 10 novembre, sans aucun changement de notre côté.
