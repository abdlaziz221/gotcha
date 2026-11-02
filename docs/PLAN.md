# Plan de développement

Concours CADEV 2026. Date limite de dépôt : **dimanche 15 novembre, 17 h GMT**. On soumet **un jour avant**.

## Stratégie en trois temps

1. **Contrats (lundi 2 novembre).** Le squelette du dépôt contient déjà une première version des contrats et une application qui tourne de bout en bout sur des fausses données. L'équipe les relit, les corrige si besoin, puis les fige ([CONTRACTS.md](CONTRACTS.md)).
2. **Développement en parallèle (3 au 6 novembre).** Chacun avance dans ses dossiers, sur le stockage « memory ». Personne n'attend personne.
3. **Branchements (7 au 9 novembre).** PostgreSQL sur Datacloud, flux de pannes en direct, serveur MCP en ligne, contenu réel. Puis **gel le 10 novembre** : on ne fait plus que corriger et polir.

Si la boucle complète ne marche pas **vendredi 6 au soir** sur les fausses données, on **réduit le périmètre** (MTN MoMo, Wave et Datacloud seulement) plutôt que de repousser le gel.

## Jalons

| Jalon | Date | Ce qui doit être vrai |
| --- | --- | --- |
| **J1 · Contrats validés** | lun. 2 nov. | Les trois ont relu et approuvé `docs/CONTRACTS.md` ; comptes ouverts |
| **J2 · Socle en ligne** | mer. 4 nov. | Le squelette tourne sur Datacloud et joint une base PostgreSQL ; choix Serverless ou VPS tranché |
| **J3 · Boucle complète sur fausses données** | ven. 6 nov. | Fiche → piège → confirmation → panne signalée → agent IA qui l'évite, sur le stockage memory |
| **J4 · Branchements** | lun. 9 nov. | Production sur PostgreSQL, flux Flutterwave en direct, MCP en ligne, 30 pièges sourcés |
| **J5 · Gel des fonctions** | mar. 10 nov. | Plus aucune nouvelle fonction ; corrections, finitions, tests utilisateurs |
| **J6 · Soumission** | sam. 14 nov. | Projet soumis, dossier complet, démo répétée |
| **J7 · Votes** | 15 – 20 nov. | Les trois ont voté (pairs) ; campagne du vote du public menée |

Sur GitHub, chaque jalon (sauf J5, qui est une date et non un lot de tâches) est un *milestone* qui regroupe ses issues.

## Calendrier

| Jour | Abdoul Aziz | Loum | Khalifa |
| --- | --- | --- | --- |
| **lun. 2** | T1, A1, compte Datacloud | T1, L1 (début) | T1, K1 |
| **mar. 3** | A2 (déploiement du squelette) | L1 | K2 |
| **mer. 4** | A2 (fin, décision), A6 | L2, L3 | K3, K7 |
| **jeu. 5** | A3, A4 | L4, L5 | K4, K5 |
| **ven. 6** | A5, A7 | L6, L7, L8 | K6, K8 |
| **sam. 7** | A8 | L9 | K9 |
| **dim. 8** | A9, A10 | L10, L11 | K10 |
| **lun. 9** | Marge, corrections d'intégration | Marge | Marge |
| **mar. 10** | **Gel des fonctions** | | |
| **mer. 11 – jeu. 12** | A11 | L12 | K11 |
| **ven. 13** | A12 | L13 | Script du pitch |
| **sam. 14** | **Soumission** | | |
| **dim. 15** | Date limite à 17 h · **vote des pairs dès 18 h : les trois votent** | | |

Contenu : environ **une heure par jour et par personne** à partir du mardi, pour atteindre **30 pièges sourcés le dimanche 8**.

## Tâches

Chaque tâche a son issue sur GitHub (même identifiant dans le titre). Le README du dossier concerné explique comment la faire.

### Les trois (T)

| Id | Tâche | Échéance |
| --- | --- | --- |
| T1 | Lire le README, CONTRIBUTING et CONTRACTS ; valider ou amender les contrats | lun. 2 |
| T2 | Recruter 5 à 10 devs testeurs (Galsen DEV, CADEV), dont 2 débutants | jeu. 5 |
| T3 | Vérifier le nom (domaine, compte GitHub) et le confirmer | mar. 3 |
| T4 | Vote des pairs : les trois votent, sinon le projet est exclu | 15 nov. 18 h – 16 nov. 23 h 59 |
| T5 | Campagne du vote du public (message prêt, réseaux, écoles) | 17 – 20 nov. |

### Abdoul Aziz : backend, DevOps, intégration (A)

| Id | Tâche | Où | Échéance |
| --- | --- | --- | --- |
| A1 | Écrire à cadev@systalink.com : droits sur le code du **lauréat** (l'article 9 ne couvre que les non-lauréats) | — | lun. 2 |
| A2 | Déployer le squelette sur Datacloud ; `/healthz?db=1` relié à une base PostgreSQL managée ; mesurer durée maximale d'une requête, tâches planifiées, accès à la base ; trancher Serverless ou VPS | `deploy/` | mer. 4 |
| A3 | `PostgresStore` : fiches, recherche plein texte, glossaire | `app/stores/postgres/` | jeu. 5 |
| A4 | `PostgresStore` : pannes et dernières lectures des flux | `app/stores/postgres/` | jeu. 5 |
| A5 | `PostgresStore` : contributions et confirmations ; activer PostgreSQL dans la CI | `app/stores/postgres/`, `.github/` | ven. 6 |
| A6 | `scripts/seed.py` opérationnel (`upsert_fiche`, `upsert_glossary`) | `scripts/`, `app/stores/postgres/` | mer. 4 |
| A7 | Relecture en production : comptes relecteurs, circuit « approuvé → intégré au contenu » | `app/services/`, `app/security/` | ven. 6 |
| A8 | Bascule de la production sur PostgreSQL : variables, domaine, HTTPS | `deploy/` | sam. 7 |
| A9 | Contenu Orange Money Sénégal et Côte d'Ivoire : 3 à 5 pièges recoupés | `content/` | dim. 8 |
| A10 | Fiche Datacloud (F2) réécrite à partir de notre déploiement réel, puis publiée | `content/fiches/datacloud-sn/` | dim. 8 |
| A11 | Revue de sécurité en production : en-têtes, cookies, quotas derrière le proxy | `app/security/` | mer. 11 |
| A12 | Dossier de soumission : licences, titularité, déclaration de l'usage de l'IA, rôles | `docs/SUBMISSION.md` | ven. 13 |

### Loum : frontend et design (L)

| Id | Tâche | Où | Échéance |
| --- | --- | --- | --- |
| L1 | Identité visuelle et design system : couleurs, typographie, logo, composants visibles dans `/styleguide` | `app/web/static/`, `templates/components/` | mar. 3 |
| L2 | Accueil : la promesse comprise en 5 secondes par un visiteur pressé (vote des pairs) | `templates/pages/home.html` | mer. 4 |
| L3 | Page fiche : lecture sur mobile, mode pas à pas, glossaire au toucher | `templates/pages/fiche.html` | mer. 4 |
| L4 | Recherche et résultats | `templates/pages/search.html` | jeu. 5 |
| L5 | Formulaire de contribution, bouton « ça marche encore », page de remerciement | `templates/pages/contribute.html` | jeu. 5 |
| L6 | Badge d'état, journal des pannes, formulaire de signalement | `templates/pages/incidents.html` | ven. 6 |
| L7 | Page « Où sont vos données », glossaire, pied de page souveraineté | `templates/pages/data.html` | ven. 6 |
| L8 | Écran de relecture | `templates/pages/review.html` | ven. 6 |
| L9 | Pages d'erreur et états vides | `templates/pages/error.html` | sam. 7 |
| L10 | Audit mobile et 3G (moins de 200 Ko par page), accessibilité (contrastes, clavier, lecteur d'écran) | tout `app/web/` | dim. 8 |
| L11 | Contenu Wave : 3 à 5 pièges recoupés ; relecture du glossaire pour les débutants | `content/` | dim. 8 |
| L12 | Test avec 2 étudiants débutants, puis corrections | — | jeu. 12 |
| L13 | Visuels de soumission et de campagne | — | ven. 13 |

### Khalifa : IA, MCP, pannes (K)

| Id | Tâche | Où | Échéance |
| --- | --- | --- | --- |
| K1 | Ouvrir les comptes bac à sable MTN MoMo et Daraja ; demander l'accès Orange Money | — | lun. 2 |
| K2 | Brancher un vrai agent de code sur le serveur MCP local ; affiner les descriptions et les réponses des outils | `app/mcp/` | mar. 3 |
| K3 | Reproduire le piège `X-Target-Environment` dans le bac à sable MTN (sinon la devise EUR) ; mettre la fiche à jour | `content/fiches/mtn-momo/` | mer. 4 |
| K4 | Import Flutterwave : affiner la correspondance opérateur et pays, tester sur le flux en direct | `app/ingest/` | jeu. 5 |
| K5 | Règles d'état (seuils, expiration des signalements), documentées | `app/services/status.py` | jeu. 5 |
| K6 | Outil `report_outage` : quotas, abus, messages | `app/mcp/` | ven. 6 |
| K7 | Détection des secrets : vrais formats de clés (Wave, Orange, MTN, Daraja), faux positifs | `app/security/secrets.py` | mer. 4 |
| K8 | Scénario de démo et test automatisé reproductible de l'agent | `docs/DEMO.md`, `tests/` | ven. 6 |
| K9 | Serveur MCP en ligne sur Datacloud, testé depuis un vrai agent | `app/mcp/`, `deploy/` | sam. 7 |
| K10 | Contenu MTN MoMo et M-Pesa : une vingtaine de pièges sourcés et vérifiés | `content/` | dim. 8 |
| K11 | Répéter la démo 10 fois ; enregistrer une vidéo de secours | — | jeu. 12 |

## Chemin critique

1. **Datacloud (A2)** : c'est le premier risque, pas le code. Sans réponse mercredi soir, on bascule sur un VPS à Dakar sans débattre.
2. **Contenu (A9, A10, L11, K10)** : un carnet vide ne vaut rien. On écrit tous les jours.
3. **Bac à sable MTN (K1, K3)** : la démo en dépend. Piège de rechange : la devise EUR.

## Critères de réussite du MVP

- [ ] Au moins 30 pièges sourcés sur au moins 4 services de paiement, plus la fiche Datacloud.
- [ ] Un agent IA évite un vrai piège grâce au serveur MCP, en démo et dans un test automatisé.
- [ ] Au moins 5 devs extérieurs, dont 2 débutants, confirment ou ajoutent un piège avant le 14 novembre.
- [ ] Au moins une autre équipe de la CADEV utilise la fiche Datacloud pour déployer.
- [ ] Une panne signalée ou importée apparaît sur la fiche concernée en moins de 15 minutes.
- [ ] Aucun bouton mort ni page vide sur le site en ligne.
- [ ] Toutes les dépendances passent le contrôle des licences.
