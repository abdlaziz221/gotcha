---
title: "Le serveur MCP répond 421 « Invalid Host header »"
severity: blocking
environments: [production]
api_version: null
error_codes: ["421"]
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

Le site s'affiche, mais chaque appel au serveur [[mcp|MCP]] (`POST /mcp`) répond `421 Misdirected Request` avec le texte `Invalid Host header`. L'[[agent-ia|agent]] n'arrive pas à se connecter.

## Cause

Le SDK Python de MCP protège le serveur contre le *DNS rebinding* : il refuse toute requête dont l'en-tête `Host` n'est pas dans sa liste d'hôtes acceptés. Derrière le proxy de Datacloud, l'application reçoit le nom public `<service>-<suffixe>.platform-systalink.com`, absent d'une liste qui ne contient que des noms locaux (`localhost`, `127.0.0.1`).

## Solution

Ajoutez le nom public exact à la liste des hôtes acceptés par une [[variable-environnement]], puis redéployez. Chez nous :

```text
GOTCHA_ALLOWED_HOSTS=<service>-<suffixe>.platform-systalink.com
```

Ne désactivez pas la protection pour aller plus vite : elle empêche un site tiers d'appeler votre serveur à travers le navigateur d'un visiteur.

## Preuve

10 novembre 2026 : `/healthz` répond 200, mais `POST /mcp` répond `421` et `Invalid Host header` tant que la variable manque. Le 11 novembre, avec le nom public dans la variable, le même appel répond `401` avec l'en-tête `WWW-Authenticate` attendu (connexion GitHub demandée).
