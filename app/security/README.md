# `app/security/` : la sécurité transverse

**Responsables :** Abdoul Aziz (tout le dossier sauf `secrets.py`) et Khalifa (`secrets.py`). **Relecteur :** l'autre.

## Ce que contient ce dossier

| Fichier | Rôle |
| --- | --- |
| `headers.py` | Middleware qui ajoute les en-têtes de sécurité : CSP stricte, `nosniff`, `X-Frame-Options`, `Referrer-Policy`, `Permissions-Policy`, `Cross-Origin-Opener-Policy`, HSTS en production |
| `csrf.py` | Jeton CSRF par double soumission : cookie `gotcha_csrf` (`__Host-gotcha_csrf` en production) + champ caché ; dépendance `verify_csrf` sur chaque POST |
| `ratelimit.py` | Quotas par IP, en mémoire ; dépendance `rate_limit(nom, limit=…, window_seconds=…)` ; `client_ip` lit l'adresse du visiteur selon `GOTCHA_PROXY_HOPS` |
| `auth.py` | Relecteurs : HTTP Basic, mots de passe hachés avec scrypt, 10 essais ratés par adresse et par quart d'heure ; dépendance `require_reviewer` |
| `github.py` | Identification par GitHub : aucune permission demandée, jeton oublié après lecture du profil public, erreurs sans aucun secret |
| `secrets.py` | Détection des clés et jetons dans les contributions (règles maison) |

## Tâches

| Id | Tâche | Qui | Échéance |
| --- | --- | --- | --- |
| K7 | `secrets.py` : vrais formats de clés Wave, Orange Money, MTN MoMo, Daraja ; chaque règle avec un vrai positif et un faux positif dans `tests/unit/test_security.py` | Khalifa | mer. 4 |
| A11 | Revue en production : en-têtes présents, cookie `Secure`, quotas corrects derrière le proxy de Datacloud (`GOTCHA_PROXY_HOPS`), CSP sans erreur dans la console. Revue du code **faite** (ci-dessous) ; vérifications en ligne après le déploiement | Abdoul Aziz | mer. 11 |

## Comment faire

- **Nouvelle route POST** : `dependencies=[Depends(verify_csrf), Depends(rate_limit("nom", limit=…, window_seconds=…))]`.
- **Ajouter un relecteur** : `python scripts/hash_password.py <pseudo>`, puis ajouter la ligne obtenue à `GOTCHA_REVIEWERS` sur Datacloud (séparateur `;`).
- **Nouvelle règle de secret** : l'ajouter à `RULES` avec un libellé français, puis deux tests (une clé fictive au bon format, un texte normal qui ne doit pas déclencher). Ne jamais mettre une vraie clé dans un test.
- **Assouplir la CSP** (par exemple pour une image externe) : à éviter ; si c'est indispensable, en discuter et noter la décision dans `docs/DECISIONS.md`.

## Revue A11 (3 novembre)

| Constat | Risque | Correction |
| --- | --- | --- |
| L'adresse du visiteur était la **première** valeur de `X-Forwarded-For`, et uvicorn croyait cet en-tête quelle que soit sa provenance (`--forwarded-allow-ips='*'`) | Un visiteur pouvait inventer une adresse à chaque requête et contourner tous les quotas (contributions, signalements, MCP) | `client_ip` lit la valeur ajoutée par le dernier proxy de confiance (`GOTCHA_PROXY_HOPS`, 1 en production) ; uvicorn lancé avec `--no-proxy-headers` (D19) |
| `/relecture` acceptait des essais de mot de passe sans limite | Mot de passe devinable par essais répétés ; chaque essai coûte un calcul scrypt, de quoi saturer une petite instance | 10 essais ratés par adresse et par quart d'heure, puis 429 avant tout calcul ; un pseudo inconnu coûte autant qu'un mauvais mot de passe |
| Cookie CSRF sans préfixe | Chez un hébergeur qui partage un domaine entre clients, un autre sous-domaine peut poser son propre cookie `gotcha_csrf` et contourner la double soumission | En production, cookie `__Host-gotcha_csrf` (le navigateur refuse qu'un autre sous-domaine le pose) ; le jeton attendu est celui lu par le middleware |
| Pas de `Cross-Origin-Opener-Policy` | Une page ouverte depuis un autre site garde un lien vers la nôtre | `Cross-Origin-Opener-Policy: same-origin` |
| VPS : `-p 8000:8000` dans `deploy/README.md` | Le port de l'application, joignable sans passer par le proxy, laisse le visiteur choisir son `X-Forwarded-For` | `-p 127.0.0.1:8000:8000` |

Vérifié sans changement : CSP stricte sans script ni style en ligne ; cookie `HttpOnly`, `SameSite=Lax`, `Secure` en production ; HSTS en production ; pages d'erreur sans trace technique ; documentation de l'API désactivée ; liens et ressources en chemins relatifs (le protocole vu par uvicorn n'a pas d'effet). Compression des pages : aucune page qui porte le jeton CSRF ne renvoie un texte venu de l'adresse (condition de l'attaque BREACH). **À garder** : ne jamais afficher un paramètre d'URL sur une page qui contient un formulaire.

**Reste à vérifier en ligne**, après le déploiement (A2, A8) :

- [ ] `GOTCHA_PROXY_HOPS` réglé d'après la sonde (`scripts/probe_platform.py`, ligne `X-Forwarded-For`), et « IP retenue » égale à l'adresse publique du poste de test
- [ ] En-têtes présents sur `https://<domaine>/` et cookie `__Host-gotcha_csrf; Secure`
- [ ] Aucune erreur CSP dans la console du navigateur, sur l'accueil, une fiche, `/contribuer` et `/pannes`
- [ ] `/relecture` : 401 sans identifiants, 429 après 10 essais ratés

## Limites connues

- Les quotas sont **par instance** : sur le Serverless, plusieurs instances ont chacune leurs compteurs. Suffisant pour le MVP ; à déplacer dans PostgreSQL en cas d'abus.
- La détection des secrets attrape les formats connus, pas tout : la relecture humaine reste obligatoire.
- Les formats Wave viennent de docs.wave.com. Les longueurs de la clé d'abonnement MTN MoMo et de la clé marchand Orange Money restent à confirmer sur de vrais comptes (K1) ; les clés Daraja n'ont pas de format publié et passent par les règles génériques.
- Un secret sans guillemets et sans chiffre, ou contenant un point ou un souligné, n'est détecté que dans un fichier `.env` ou YAML : sinon on signalerait les noms de variables.

## Tester

```bash
pytest tests/unit/test_security.py tests/web/test_forms.py
```

## À ne pas faire

- Journaliser un secret détecté, un mot de passe ou une URL de base de données.
- Désactiver `verify_csrf` « pour tester » : utiliser la fixture `csrf` des tests.
