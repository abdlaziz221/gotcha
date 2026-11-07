# Plan de développement

Concours CADEV 2026. Date limite de dépôt : **dimanche 15 novembre, 17 h GMT**. On soumet **un jour avant**.

## Stratégie en trois temps

1. **Contrats (lundi 2 novembre).** Le squelette du dépôt contient déjà une première version des contrats et une application qui tourne de bout en bout sur des fausses données. L'équipe les relit, les corrige si besoin, puis les fige ([CONTRACTS.md](CONTRACTS.md)).
2. **Développement en parallèle (3 au 6 novembre).** Chacun avance dans ses dossiers, sur le stockage « memory ». Personne n'attend personne.
3. **Branchements (7 au 9 novembre).** PostgreSQL sur Datacloud, flux de pannes en direct, serveur MCP en ligne, contenu réel. Puis **gel le 10 novembre** : on ne fait plus que corriger et polir.

Si la boucle complète ne marche pas **vendredi 6 au soir** sur les fausses données, on **réduit le périmètre** (MTN MoMo, Wave et Datacloud seulement) plutôt que de repousser le gel.

## Priorités jusqu'à la soumission

On ne change plus le positionnement ni l'architecture (D29). Quand deux travaux se concurrencent, le premier de cette liste passe devant.

| Ordre | Niveau | Priorité | Ce qui doit être vrai |
| --- | --- | --- | --- |
| 1 | Bloquant | **Relectures et fusion des PR** | Loum et Khalifa relisent dans l'ordre : 43, 45, 47, 49 à 54, puis 44, 46 et 48. Conflits résolus, intégration dans l'ordre |
| 2 | Bloquant | **Recevabilité** | Droits, origine du code, licences, comptes Datacloud et inscription de l'équipe vérifiés ([SUBMISSION.md](SUBMISSION.md)) |
| 3 | Bloquant | **Déploiement** | HTTPS, PostgreSQL, persistance après redémarrage, accès public qui marche |
| 4 | Important | **Contenu** | Au moins 15 pièges relus et publiés, sans gonfler leur niveau de confiance |
| 5 | Important | **Démonstration** | Wave sans puis avec Gotcha, lecture par MCP, panne en direct, courte séquence en wolof ([DEMO.md](DEMO.md)) |
| 6 | Conditionnel | **Audio en wolof** (D26) | Seulement quand le produit principal est stable. **Abandon si le socle n'est pas en ligne le dimanche 8 novembre** |

## Jalons

| Jalon | Date | Ce qui doit être vrai |
| --- | --- | --- |
| **J1 · Contrats validés** | lun. 2 nov. | Les trois ont relu et approuvé `docs/CONTRACTS.md` ; comptes ouverts |
| **J2 · Socle en ligne** | mer. 4 nov. | Le squelette tourne sur Datacloud et joint une base PostgreSQL ; choix Serverless ou VPS tranché |
| **J3 · Boucle complète sur fausses données** | ven. 6 nov. | Fiche → piège → confirmation → panne signalée → agent IA qui l'évite, sur le stockage memory |
| **J4 · Branchements** | lun. 9 nov. | Production sur PostgreSQL, flux Flutterwave en direct, MCP en ligne, au moins 15 pièges relus et publiés |
| **J5 · Gel des fonctions** | mar. 10 nov. | Plus aucune nouvelle fonction ; corrections, finitions, tests utilisateurs |
| **J6 · Soumission** | sam. 14 nov. | Projet soumis, dossier complet, démo répétée |
| **J7 · Votes** | 15 – 20 nov. | Les trois ont voté (pairs) et vérifié la confirmation ; campagne du vote du public menée |
| **J8 · Jury et résultats** | 21 – 23 nov. | Notation les 21 et 22, chacun sait expliquer la solution ; résultats le 23 |

Sur GitHub, chaque jalon (sauf J5, qui est une date et non un lot de tâches) est un *milestone* qui regroupe ses issues.

## Calendrier

| Jour | Abdoul Aziz | Loum | Khalifa |
| --- | --- | --- | --- |
| **lun. 2** | T1, compte Datacloud | T1, L1 (début) | T1, K1 |
| **mar. 3** | A2 (déploiement du squelette) | L1 | K2 |
| **mer. 4** | A2 (fin, décision), A6 | L2, L3 | K3, K7 |
| **jeu. 5** | A3, A4 | L4, L5 | K4, K5 |
| **ven. 6** | A5, A7 | L6, L7, L8 | K6, K8 |
| **sam. 7** | A8 | L9 | K9 |
| **dim. 8** | A9, A10, A13 à A15, A18 · **point de décision sur le wolof** | L10, L11 | K10 |
| **lun. 9** | A16, A19 (si l'audio est retenu), corrections d'intégration | L14, L15 | K12 |
| **mar. 10** | **Gel des fonctions** | | |
| **mer. 11 – jeu. 12** | A11 | L12 | K11 |
| **ven. 13** | A12, A1 (réponse écrite avant la soumission) · rôles et déclarations relus à trois (T7, T8) | L13 | Script du pitch |
| **sam. 14** | **Soumission** | | |
| **dim. 15** | Date limite à 17 h · **vote des pairs dès 18 h : les trois votent** | | |

Contenu : environ **une heure par jour et par personne** à partir du mardi, pour atteindre **au moins 15 pièges relus et publiés le dimanche 8**.

Audio en wolof, si le point de décision du 8 est positif : le code avant le gel, puis les enregistrements et leur relecture du 11 au 13 (c'est du contenu, pas une fonction).

## Tâches

Chaque tâche a son issue sur GitHub (même identifiant dans le titre). Le README du dossier concerné explique comment la faire.

### Les trois (T)

| Id | Tâche | Échéance |
| --- | --- | --- |
| T1 | Accepter l'invitation GitHub ; installer son poste (CONTRIBUTING, « Installer son poste ») ; lire le README, CONTRIBUTING et CONTRACTS ; valider ou amender les contrats | lun. 2 |
| T2 | Recruter 5 à 10 devs testeurs (Galsen DEV, CADEV), dont 2 débutants | jeu. 5 |
| T3 | Vérifier le nom (domaine, compte GitHub) et le confirmer | mar. 3 |
| T4 | Vote des pairs : les trois votent, sinon le projet est exclu | 15 nov. 18 h – 16 nov. 23 h 59 |
| T5 | Campagne du vote du public (message prêt, réseaux, écoles) | 17 – 20 nov. |
| T6 | Relire et fusionner les PR dans l'ordre : 43, 45, 47, 49 à 54, puis 44, 46 et 48 | dès maintenant |
| T7 | Recevabilité : comptes Datacloud, inscription de l'équipe, représentant, clé de répartition, pays, titularité ; chacun vérifie qu'aucun élément ne vient d'un prototype ou d'un projet antérieur, ou le déclare (article 6). Rôles écrits d'après le travail réel, preuves gardées (D28) | ven. 13 |
| T8 | Inventaire précis des outils d'IA : outils, fonctions concernées, validation humaine. Il se remplit dans le formulaire (article 6) | ven. 13 |
| T9 | Copier le libellé exact du sujet depuis l'interface du concours et vérifier notre alignement | dès que possible |
| T10 | Séance interne : chacun sait expliquer OAuth, le cycle MCP, PostgreSQL, les niveaux de confiance, les protections contre les contributions malveillantes et le déploiement sur Datacloud | jeu. 12 |
| T11 | Audio en wolof, si le socle est en ligne le 8 : enregistrer 3 à 5 explications, faire écouter et relire chacune par un second locuteur (D26) | 11 – 13 nov. |

### Abdoul Aziz : backend, DevOps, intégration (A)

| Id | Tâche | Où | Échéance |
| --- | --- | --- | --- |
| A1 | Écrire à cadev@systalink.com : droits sur le code du **lauréat** (l'article 9 ne couvre que les non-lauréats). Obtenir une réponse écrite avant la soumission | — | ven. 13 |
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
| A13 | Connexion GitHub du serveur MCP : comptes, jetons, quotas (D20) | `app/services/oauth.py`, `app/mcp/oauth.py`, `migrations/` | dim. 8 |
| A14 | Niveaux de confiance, preuves et dates des sources (D22) | `app/domain/`, `content/` | dim. 8 |
| A15 | Connexion et aperçu public sur le site, contributions avec compte (D23) | `app/web/`, `app/services/` | dim. 8 |
| A16 | Outils MCP pour proposer et confirmer un piège, compteurs d'usage (D24) | `app/mcp/`, `app/services/` | lun. 9 |
| A18 | Ouvrir la fiche Wave sans compte (D27) et compter les consultations de façon anonymisée | `content/fiches/wave-sn/`, `app/services/` | dim. 8 |
| A19 | Audio en wolof, si le socle est en ligne : champs du piège, route protégée, recherche (D26) | `app/domain/`, `app/stores/`, `app/web/routes/` | lun. 9 |

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
| L12 | Test avec 2 étudiants débutants, puis corrections. Leur demander ce qu'ils préfèrent : audio en wolof, transcription en wolof ou explication en français | — | jeu. 12 |
| L13 | Visuels de soumission et de campagne | — | ven. 13 |
| L14 | Lecteur audio et transcription sur la fiche, sur mobile, si le socle est en ligne (D26) | `templates/components/cards.html` | lun. 9 |
| L15 | Afficher près de chaque piège « Relu par » à partir de `verified_by`. Le modèle n'a aucun champ pour l'auteur : l'ajouter changerait `app/domain/` (accord des trois) la veille du gel, donc pas d'auteur affiché, et jamais d'attribution inventée | `templates/components/cards.html` | lun. 9 |

### Khalifa : IA, MCP, pannes (K)

| Id | Tâche | Où | Échéance |
| --- | --- | --- | --- |
| K1 | Ouvrir les comptes bac à sable MTN MoMo et Daraja ; demander l'accès Orange Money | — | lun. 2 |
| K2 | Brancher un vrai agent de code sur le serveur MCP local ; affiner les descriptions et les réponses des outils | `app/mcp/` | mar. 3 |
| K3 | Reproduire des pièges dans les bacs à sable MTN et Daraja (dont le callback M-Pesa) ; passer les fiches au niveau `reproduced` | `content/fiches/mtn-momo/` | mer. 4 |
| K4 | Import Flutterwave : affiner la correspondance opérateur et pays, tester sur le flux en direct | `app/ingest/` | jeu. 5 |
| K5 | Règles d'état (seuils, expiration des signalements), documentées | `app/services/status.py` | jeu. 5 |
| K6 | Outil `report_outage` : quotas, abus, messages | `app/mcp/` | ven. 6 |
| K7 | Détection des secrets : vrais formats de clés (Wave, Orange, MTN, Daraja), faux positifs | `app/security/secrets.py` | mer. 4 |
| K8 | Test de l'agent sans puis avec Gotcha (tokens, tentatives, temps, réussite) ; scénario de démo et test automatisé reproductible | `docs/DEMO.md`, `tests/` | ven. 6 |
| K9 | Serveur MCP en ligne sur Datacloud, testé depuis un vrai agent | `app/mcp/`, `deploy/` | sam. 7 |
| K10 | Contenu MTN MoMo et M-Pesa : une dizaine de pièges bien documentés, avec leur niveau de confiance | `content/` | dim. 8 |
| K11 | Répéter la démo 10 fois ; enregistrer une vidéo de secours | — | jeu. 12 |
| K12 | Si l'audio est retenu : interroger un agent en wolof (5 essais). Il doit trouver le bon piège, et un locuteur juge son explication. Sinon, on ne le montre pas | `docs/DEMO.md` | lun. 9 |

## Chemin critique

1. **Relectures (T6)** : chaque PR a besoin d'une approbation pour arriver sur `main`, et la pile avance une PR à la fois. Le dépôt public montre `main` aux votants et au jury.
2. **Datacloud (A2)** : c'est le premier risque, pas le code. Sans réponse mercredi soir, on bascule sur un VPS à Dakar sans débattre. Il faut aussi un produit Datacloud acheté avec la remise de 40 %, sans quoi le projet est irrecevable.
3. **Contenu (A9, A10, L11, K10)** : un carnet vide ne vaut rien. On écrit tous les jours.
4. **Bacs à sable (K1, K3)** : ils ne servent plus à la démo (D25), mais ils font passer des pièges de « sourcé » à « reproduit », à commencer par M-Pesa.
5. **Vote des pairs (T4)** : il élimine avant le jury. L'accueil, les fiches Wave et Datacloud ouvertes et un lien direct dans le formulaire doivent convaincre en une minute, sans compte.

## Critères de réussite du MVP

- [ ] Au moins 15 pièges relus et publiés sur au moins 4 services de paiement, plus la fiche Datacloud, dont une partie réellement reproduite. Aucun n'est marqué « confirmé en production » sans preuve de production.
- [ ] Un agent IA évite un vrai piège grâce au serveur MCP, en démo et dans un test automatisé.
- [ ] Au moins 5 devs extérieurs, dont 2 débutants, confirment ou ajoutent un piège avant le 14 novembre.
- [ ] Au moins une autre équipe de la CADEV utilise la fiche Datacloud pour déployer.
- [ ] Une panne signalée ou importée apparaît sur la fiche concernée en moins de 15 minutes.
- [ ] Aucun bouton mort ni page vide sur le site en ligne.
- [ ] Toutes les dépendances passent le contrôle des licences.
