---
title: "L'instance gratuite se met en veille : rien de ce qui est en mémoire ne dure"
severity: major
environments: [production]
api_version: null
error_codes: []
confidence: production
publication: draft
verified_by: null
last_confirmed_on: 2026-11-11
sources:
  - title: Console Datacloud, page du service (offre Free)
    url: https://platform.systalink.com/
    accessed_on: 2026-11-10
  - title: Retour de terrain, déploiement de Gotcha sur Datacloud Serverless Free
    author: abdlaziz221
    accessed_on: 2026-11-11
---

## Symptôme

Des comptes, des sessions ou des données enregistrées disparaissent, et la première visite après un moment de calme met longtemps à répondre.

## Cause

La console prévient, sur la page d'un service Free, que l'instance gratuite se met en veille en cas d'inactivité, ce qui peut retarder les requêtes de 50 secondes ou plus. L'offre Free n'inclut ni base de données ni disque. Tout ce que l'application garde en mémoire, ou dans le système de fichiers du conteneur, ne survit pas à un redémarrage : changement de variable, nouveau déploiement ou reprise après la veille.

## Solution

Gardez les données dans une base PostgreSQL : managée chez Datacloud, ou hébergée ailleurs. Dans ce cas, donnez son adresse **externe** et ajoutez `?sslmode=require` pour exiger le chiffrement. Si vous n'avez pas de base, n'activez que ce qui peut tout perdre sans dommage : chez nous, la lecture seule, sans compte ni formulaire. Prévenez aussi vos testeurs que la première page peut être lente.

## Preuve

10 novembre 2026, service Serverless Free à Dakar, application FastAPI avec stockage en mémoire. La page du service affiche « Votre instance gratuite se mettra en veille en cas d'inactivité, ce qui peut retarder les requêtes de 50 secondes ou plus ». Les journaux montrent l'arrêt puis le redémarrage de l'application à 01 h 18 et à 08 h 55 : à chaque fois, elle repart d'un stockage en mémoire neuf (« Stockage mémoire : aucune base à préparer ») : le contenu est rechargé depuis les fichiers, mais les comptes et les contributions d'avant sont perdus. Le 11 novembre, le même service branché sur une base PostgreSQL externe (`sslmode=require`) répond `"database": "ok"` sur `/healthz?db=1`, et la connexion GitHub fonctionne.
