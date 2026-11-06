# `deploy/` : le déploiement sur Datacloud

**Responsable :** Abdoul Aziz (tâches A2, A8). **Relecteur :** Khalifa.

Le règlement impose un déploiement sur Datacloud avec au moins un produit payant, acquis avec la remise CADEV de 40 % (sauf VPS hors Dakar). L'image Docker est à la racine (`Dockerfile`).

## Option 1 : Serverless (à essayer en premier)

Offre Starter (environ 7,35 $ par mois avant remise), dépôt Git connecté, Docker accepté.

1. Créer le compte sur [platform.systalink.com](https://platform.systalink.com/) et appliquer le code promotionnel.
2. Créer une base **PostgreSQL managée**.
3. Créer le service Serverless : connecter le dépôt `abdlaziz221/gotcha`, branche `main`, construction par le `Dockerfile`.
4. Variables d'environnement :

   | Variable | Valeur |
   | --- | --- |
   | `GOTCHA_ENV` | `prod` |
   | `DATABASE_URL` | adresse de la base managée |
   | `GOTCHA_SITE_URL` | `https://<domaine public>` |
   | `GOTCHA_ALLOWED_HOSTS` | `<domaine public>` |
   | `GOTCHA_REVIEWERS` | voir `scripts/hash_password.py` |
   | `PORT` | celui qu'attend la plateforme, si elle l'impose |

   En production, le site lit tout dans PostgreSQL (`GOTCHA_STORE=postgres`, valeur par défaut quand `GOTCHA_ENV=prod`) : appliquer les migrations et charger le contenu (étape 5) **avant** d'ouvrir le site.
5. Appliquer le schéma et charger le contenu, depuis un poste qui joint la base :

   ```bash
   DATABASE_URL=… python scripts/migrate.py
   ```

   ```bash
   DATABASE_URL=… python scripts/seed.py
   ```

6. Vérifier : `https://<domaine>/healthz?db=1` doit répondre `{"status": "ok", …, "database": "ok"}`.

### À mesurer pendant A2 (et à noter dans `docs/DECISIONS.md`)

- [ ] Durée maximale d'une requête (le rafraîchissement des pannes prend jusqu'à 5 secondes)
- [ ] Tâches de fond après la réponse : sont-elles exécutées ou coupées ?
- [ ] Tâches planifiées disponibles ?
- [ ] Le Serverless joint-il la base managée (réseau, SSL) ?
- [ ] Démarrage à froid : combien de secondes ?
- [ ] En-tête `X-Forwarded-For` transmis par le proxy (quotas par IP) ?

**Sans réponse satisfaisante mercredi 4 au soir : passer à l'option 2.**

## Option 2 : VPS à Dakar (repli)

À partir de 5 € par mois environ, remise de 40 % uniquement pour les VPS **situés à Dakar**.

```bash
docker build -t gotcha .
```

```bash
docker run -d --name gotcha --restart unless-stopped --env-file /etc/gotcha.env -p 8000:8000 gotcha
```

Puis : un proxy HTTPS devant le port 8000 (Caddy ou Nginx, licences permissives), et une tâche planifiée pour les pannes :

```bash
*/10 * * * * docker exec gotcha python -m app.ingest
```

## Après chaque déploiement

- [ ] `/healthz?db=1` répond `ok`
- [ ] Accueil, une fiche, la recherche et `/pannes` s'affichent ; aucune erreur CSP dans la console du navigateur
- [ ] `/styleguide` répond 404 (mode production)
- [ ] Un agent joint `https://<domaine>/mcp`

Ce qu'on apprend ici nourrit la **fiche Datacloud** (`content/fiches/datacloud-sn/`, tâche A10) : chaque difficulté rencontrée est un piège à documenter.
