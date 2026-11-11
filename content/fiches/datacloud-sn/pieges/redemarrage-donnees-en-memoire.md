---
title: "Le service redémarre seul : tout ce qui est en mémoire est perdu"
severity: major
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

Des comptes, des sessions ou des données enregistrées disparaissent sans raison apparente. Les journaux montrent que l'application a redémarré alors que vous n'avez rien déployé.

## Cause

Le service Serverless peut redémarrer de lui-même. L'offre Free n'a ni base de données ni disque : tout ce que l'application garde en mémoire ou dans le système de fichiers du conteneur repart de zéro à chaque redémarrage.

## Solution

Gardez les données dans une base PostgreSQL : managée chez Datacloud, ou hébergée ailleurs. Dans ce cas, donnez son adresse **externe** et ajoutez `?sslmode=require` pour exiger le chiffrement. Si vous n'avez pas de base, n'activez que ce qui peut tout perdre sans dommage : chez nous, la lecture seule, sans compte ni formulaire.

## Preuve

10 novembre 2026, service Serverless Free à Dakar, application FastAPI avec stockage en mémoire. Journaux : deux redémarrages dans la même journée, à 01 h 18 et à 08 h 55, sans nouveau déploiement de notre part. Le 11 novembre, le même service branché sur une base PostgreSQL externe (`sslmode=require`) répond `"database": "ok"` sur `/healthz?db=1`, et la connexion GitHub fonctionne.
