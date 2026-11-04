# `deploy/` : le déploiement sur Datacloud

**Responsable :** Abdoul Aziz (tâches A2, A8). **Relecteur :** Khalifa.

Le règlement impose un déploiement sur Datacloud avec au moins un produit payant, acquis avec la remise CADEV de 40 % (sauf VPS hors Dakar). L'image Docker est à la racine (`Dockerfile`).

## Option 1 : Serverless (à essayer en premier)

Offre Starter : 7,35 $ par mois avant remise, 512 Mo de mémoire, 0,5 processeur virtuel. La page de l'offre annonce le déploiement depuis Git, Python et Docker, les variables d'environnement et secrets, les journaux, une adresse HTTPS, l'accès SSH, des tâches ponctuelles et des disques persistants. Elle ne parle pas de tâches planifiées ([Serverless](https://systalink.com/en/serverless)).

1. Créer le compte sur [platform.systalink.com](https://platform.systalink.com/) et appliquer le code promotionnel.
2. Créer une base **PostgreSQL managée** et noter son adresse de connexion (`postgresql://…`). Le pilote essaie le chiffrement de lui-même ; pour l'exiger, ajouter `?sslmode=require` à la fin de l'adresse.
3. Créer le service Serverless : connecter le dépôt `abdlaziz221/gotcha`, branche `main`, construction par le `Dockerfile`. Chemin de vérification de santé, si la plateforme en demande un : `/healthz`.
4. Variables d'environnement :

   | Variable | Valeur |
   | --- | --- |
   | `GOTCHA_ENV` | `prod` |
   | `DATABASE_URL` | adresse de la base managée |
   | `GOTCHA_SITE_URL` | `https://<domaine public>` |
   | `GOTCHA_ALLOWED_HOSTS` | `<domaine public>` |
   | `GOTCHA_REVIEWERS` | voir `scripts/hash_password.py` |
   | `GOTCHA_GITHUB_CLIENT_ID` et `GOTCHA_GITHUB_CLIENT_SECRET` | Application OAuth GitHub de production, voir « Connexion du serveur MCP » |
   | `GOTCHA_PROXY_HOPS` | `1` (valeur par défaut en production), à confirmer avec la sonde |
   | `GOTCHA_PROBE` | `1` le temps des mesures ci-dessous, puis à retirer |
   | `PORT` | celui qu'attend la plateforme, si elle l'impose |

5. Déployer. **Rien à lancer à la main** : à chaque démarrage, le conteneur applique les migrations puis charge `content/` en base (`scripts/release.py`, décision D18). Les journaux affichent :

   ```text
   Migrations appliquées : 001_init
   5 fiche(s), 8 piège(s), 15 terme(s) chargés.
   ```

   Si le conteneur s'arrête aussitôt, la cause (base injoignable, mot de passe refusé) est juste au-dessus dans les journaux.
6. Vérifier : `https://<domaine>/healthz?db=1` doit répondre `{"status": "ok", …, "database": "ok"}`.

### Mesurer les limites du Serverless (A2)

Le site tourne avec `GOTCHA_PROBE=1`. Depuis un poste :

```bash
python scripts/probe_platform.py https://<domaine>
```

En une dizaine de minutes, le script répond aux questions ci-dessous et imprime un tableau en Markdown. On le recopie dans `docs/DECISIONS.md` (choix entre Serverless et VPS) et dans la fiche Datacloud (A10).

- [ ] Durée maximale d'une requête (le rafraîchissement des pannes prend jusqu'à 5 secondes)
- [ ] Tâches de fond après la réponse : exécutées ou coupées ?
- [ ] Le Serverless joint-il la base managée (réseau, SSL), et en combien de temps ?
- [ ] Le site joint-il Internet (flux de pannes Flutterwave) ?
- [ ] Démarrage à froid : relancer le script après 30 minutes sans visite, puis lire « Premier appel »
- [ ] En-tête `X-Forwarded-For` : le proxy le remplace-t-il ou l'ajoute-t-il ? La ligne du compte rendu donne la valeur de `GOTCHA_PROXY_HOPS` (quotas par adresse IP, A11). Vérifier ensuite la ligne « IP retenue » : ce doit être l'adresse publique du poste qui lance le script.

À relever dans l'interface de Datacloud, que le script ne voit pas :

- [ ] Tâches planifiées disponibles ? Sinon, la lecture des pannes reste déclenchée par les visites (décision D7).
- [ ] Nombre d'instances, mise en veille sans visite
- [ ] Port imposé (`PORT`)

Ensuite, retirer `GOTCHA_PROBE` et redéployer : `/_sonde/requete` doit répondre 404.

**Sans réponse satisfaisante mercredi 4 au soir : passer à l'option 2.**

## Option 2 : VPS à Dakar (repli)

À partir de 5 € par mois environ, remise de 40 % uniquement pour les VPS **situés à Dakar**.

```bash
docker build -t gotcha .
```

```bash
docker run -d --name gotcha --restart unless-stopped --env-file /etc/gotcha.env -p 127.0.0.1:8000:8000 gotcha
```

Le port 8000 n'écoute que sur la machine : tout passe par le proxy, sinon un visiteur pourrait choisir son adresse dans `X-Forwarded-For` et contourner les quotas (`GOTCHA_PROXY_HOPS=1` derrière un seul proxy). Comme sur le Serverless, le conteneur prépare la base à son démarrage. Puis : un proxy HTTPS devant le port 8000 (Caddy ou Nginx, licences permissives), et une tâche planifiée pour les pannes :

```bash
*/10 * * * * docker exec gotcha python -m app.ingest
```

## Après chaque déploiement

- [ ] `/healthz?db=1` répond `ok`
- [ ] Accueil, une fiche, la recherche et `/pannes` s'affichent ; aucune erreur CSP dans la console du navigateur
- [ ] `/styleguide` répond 404 (mode production)
- [ ] Un agent joint `https://<domaine>/mcp`

Ce qu'on apprend ici nourrit la **fiche Datacloud** (`content/fiches/datacloud-sn/`, tâche A10) : chaque difficulté rencontrée est un piège à documenter.

## Connexion du serveur MCP

Par défaut, la production demande une connexion GitHub pour tout appel à `/mcp` (D20).

1. Créer une application OAuth sur <https://github.com/settings/developers>. **Une par adresse** : celle des essais locaux ne sert pas en production.
   - Homepage URL : `https://<domaine public>`
   - Redirect URI : `https://<domaine public>/github/callback`
   - Allow wildcard matching et Device Flow : décochés
2. Générer le secret et le placer seulement dans la console Datacloud, dans `GOTCHA_GITHUB_CLIENT_SECRET`.
3. Vérifier que la base PostgreSQL est branchée : l'application refuse de démarrer sinon, car le stockage `memory` perdrait les comptes et les connexions à chaque redémarrage.
4. Depuis un outil MCP compatible, ajouter `https://<domaine public>/mcp`, se connecter, puis faire lire une fiche.

Pour bloquer un compte : `UPDATE accounts SET blocked = true WHERE pseudo = '<pseudo>';`. L'accès est coupé tout de suite.

**Plan de secours :** `GOTCHA_MCP_AUTH=false` laisse la lecture libre et retire les outils d'écriture.

**Essai local :** avec une application dont la Redirect URI est `http://localhost:8799/github/callback`, définir `GOTCHA_MCP_AUTH=true`, `GOTCHA_SITE_URL=http://localhost:8799` et les deux valeurs GitHub, puis lancer uvicorn sur le port 8799.
