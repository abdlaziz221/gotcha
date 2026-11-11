## Créer un compte

Inscrivez-vous sur platform.systalink.com.

## Choisir l'offre

[[serverless|Serverless]] : vous connectez votre dépôt Git et la plateforme déploie à chaque modification. [[vps|VPS]] : un serveur que vous administrez vous-même, à Dakar.

Nous avons déployé Gotcha sur l'offre Serverless Free, à Dakar, construite par le `Dockerfile` du dépôt, branche `main`. Elle n'a ni base de données ni disque : si votre application garde des données, prévoyez une base ailleurs (voir le piège sur les redémarrages).

## Configurer l'application

Donnez à l'application tout ce qui change d'un environnement à l'autre par des [[variable-environnement|variables d'environnement]], jamais dans le dépôt : l'adresse publique du site, la liste des noms d'hôte acceptés, l'adresse de la base, les secrets.

Le nom d'hôte public a la forme `<service>-<suffixe>.platform-systalink.com`. Si votre application vérifie l'en-tête `Host` (c'est le cas du SDK Python de [[mcp|MCP]]), ajoutez ce nom à sa liste d'hôtes acceptés.

## Brancher une base PostgreSQL

Créez une base PostgreSQL managée, puis donnez son adresse à l'application, par exemple dans `DATABASE_URL`. Une base hébergée ailleurs fonctionne aussi : nous avons branché notre service Free sur une base PostgreSQL externe. Prenez son adresse **externe** (l'adresse interne ne marche que chez son hébergeur) et ajoutez `?sslmode=require` à la fin pour exiger le chiffrement.

## Connexion GitHub

Si votre site propose la connexion GitHub, l'adresse de retour (`https://<domaine>/github/callback` chez nous) doit être déclarée dans l'application GitHub. Une même application accepte plusieurs adresses de retour : ajoutez celle de Datacloud à côté des autres, sans cocher la correspondance par joker. Avec un joker, GitHub accepterait aussi tout sous-domaine et tout sous-dossier de cette adresse : un code d'autorisation pourrait partir ailleurs que sur votre page de retour. Une application qui n'avait qu'une adresse de retour avant le 3 août 2026 a le joker activé d'office pour celle-ci : vérifiez dans ses réglages qu'il est désactivé.

## Derrière le proxy

Le service est derrière un proxy, qui complète l'en-tête `X-Forwarded-For`. Pour les quotas par adresse, lisez la dernière valeur de cet en-tête, jamais la première : celle-là, le visiteur peut l'inventer. Le 11 novembre, douze requêtes portant chacune une fausse adresse différente ont été comptées ensemble et bloquées dès la onzième : la fausse adresse ne contourne pas le quota. Vérifiez aussi que deux réseaux différents ont bien des quotas séparés, sinon la dernière valeur est celle d'un proxy interne et tous vos visiteurs partagent le même quota.

## Vérifier le déploiement

Depuis un autre réseau que le vôtre, ouvrez une adresse de santé de l'application (`/healthz?db=1` chez nous) : elle doit répondre et dire qu'elle joint la base. Le statut LIVE de la console ne suffit pas (voir le piège sur l'adresse publique).
