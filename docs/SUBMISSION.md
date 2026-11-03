# Soumission et votes

**Responsable :** Abdoul Aziz (tâche A12), avec les trois membres pour les déclarations personnelles.

Date limite : **dimanche 15 novembre 2026, 17 h GMT**. Objectif : soumettre le **samedi 14**.

Ce dossier reprend ce que le règlement exige (articles 4 à 6 et annexe 1), les textes prêts à coller dans le formulaire et la marche à suivre le jour J. Les numéros d'article renvoient au règlement officiel, consultable depuis l'interface du concours sur [platform.systalink.com](https://platform.systalink.com/).

## 1. Recevabilité

Un seul point manquant rend le projet irrecevable. Une déclaration inexacte est une fraude qui entraîne la disqualification (article 10).

| Condition | Article | Qui | Preuve ou état |
| --- | --- | --- | --- |
| Chaque membre a 18 ans révolus et la nationalité d'un pays d'Afrique francophone ou anglophone, ou y réside | 4 | Les trois | Pièce d'identité exigée avant tout prix |
| Chaque membre a **son propre compte Datacloud** et a accepté le règlement et la politique de confidentialité | 4, 5 | Les trois | [ ] Abdoul Aziz · [ ] Loum · [ ] Khalifa |
| Équipe inscrite sur Datacloud, de 2 à 5 membres | 4 | Le représentant | [ ] Faite. Le code promotionnel CADEV n'est donné qu'aux équipes inscrites |
| Représentant unique désigné | 4 | Les trois | Représentant : ……… |
| Clé de répartition du prix déclarée | 4 | Les trois | Décision de l'équipe : ……… |
| Pays de représentation : **Sénégal**, pays de nationalité ou de résidence du représentant. Choix définitif | 4 | Le représentant | Détermine le groupe national du vote des pairs |
| Aucun membre n'est collaborateur de Systalink ou de son groupe, membre du jury ou proche d'un juré | 4 | Les trois | À vérifier dès la publication du jury (au plus tard le 20 novembre) |
| Projet **déployé et accessible en ligne** | 6 | Abdoul Aziz (A2, A8) | `https://<domaine>/healthz?db=1` répond `"database":"ok"` |
| Au moins un produit Datacloud acheté avec la remise CADEV de 40 % | 6, 8 | Abdoul Aziz (A2) | Produit : ……… · facture conservée. L'article 6 renvoie par erreur à l'article 9 : la remise est à l'article 8 |
| Création originale, faite pendant le concours, libre de droits de tiers | 6 | Les trois | Voir la section 4 |
| Déclaration de titularité de chaque membre | 6 | Les trois | Voir la section 5 |
| Liste de tous les composants et de leurs licences | 6 | Abdoul Aziz | Voir la section 3 |
| Déclaration de l'usage des outils d'IA | 6 | Les trois | Voir la section 6 |

## 2. Textes du formulaire

Les chiffres (pièges publiés, services, pays) se vérifient le jour J, sur le site en ligne. Pour compter les pièges publiés :

```bash
grep -l "publication: published" content/fiches/*/pieges/*.md | wc -l
```

**Nom du projet :** Gotcha

**Accroche :** Les pièges du paiement et du déploiement en Afrique que personne ne documente.

**Description courte :**

> Gotcha est le carnet de terrain partagé des devs africains qui intègrent Wave, Orange Money, MTN MoMo ou M-Pesa, ou qui déploient sur Datacloud. On y trouve ce que la documentation ne dit pas : des pièges sourcés et relus par un humain, l'état des services en direct, et un serveur MCP pour que les agents de code IA les évitent aussi.

**Problème :**

> Un dev qui intègre un paiement mobile en Afrique perd des jours sur des détails absents de la documentation officielle. Par exemple : une devise fictive en bac à sable, une adresse qui change en production, un statut « en attente » qu'il ne faut pas relancer. Les réponses existent, mais elles sont éparpillées dans des groupes WhatsApp, des tickets GitHub et des blogs. Les agents de code IA, de plus en plus utilisés, refont les mêmes erreurs.

**Solution :**

> Une fiche par service et par pays : les étapes, puis les pièges, chacun présenté en symptôme, cause et solution, avec ses sources. Les devs confirment qu'un piège existe encore ou en proposent un nouveau, relu avant publication. L'état de chaque service combine le flux public d'incidents de Flutterwave et les signalements des devs. Un serveur MCP donne le même savoir aux agents IA : lister les services, lire une fiche, chercher un piège, connaître l'état d'un service, signaler une panne.

**Ce qui le distingue :**

> - Rien n'est publié sans source et sans relecture humaine.
> - Lisible par les agents IA (MCP), pas seulement par les humains.
> - Pensé pour la 3G : pages de moins de 200 Ko, utilisables sans JavaScript.
> - Glossaire et mode pas à pas pour les débutants.
> - Données hébergées à Dakar, sur Datacloud.

**Liens :**

| Quoi | Lien |
| --- | --- |
| Site en ligne | `https://<domaine>` (A8) |
| Page la plus parlante | `https://<domaine>/fiches/<la fiche la plus riche en pièges publiés>` |
| Serveur MCP | `https://<domaine>/mcp` |
| Code source | <https://github.com/abdlaziz221/gotcha> |
| Vidéo de démo | Lien de la vidéo de secours (K11) |

**Rôles :**

| Membre | GitHub | Rôle | Parties du projet |
| --- | --- | --- | --- |
| Abdoul Aziz | `abdlaziz221` | Full-Stack : backend, DevOps, intégration | Stockage PostgreSQL et migrations, services des fiches et des contributions, routes du site, sécurité, déploiement sur Datacloud, CI, contenu Orange Money et Datacloud |
| Loum | `AliouLoum` | Frontend et design | Identité visuelle, pages et composants, accessibilité, budget 3G, contenu Wave, visuels |
| Khalifa | `TechwithXalifa` | Ingénieur IA | Serveur MCP, import des pannes Flutterwave, règles d'état des services, détection des secrets, démo avec un agent, contenu MTN MoMo et M-Pesa |

**Visuels :** ceux de la tâche L13.

## 3. Composants et licences

Le règlement n'admet que des composants sous licence permissive et demande de les déclarer tous (article 6). La CI vérifie à chaque PR les licences d'une installation neuve (`python scripts/check_licenses.py`).

- **Paquets Python :** [LICENCES.md](LICENCES.md), généré par `python scripts/check_licenses.py --markdown`. Il sépare les paquets livrés avec l'application des outils de développement. À regénérer le jour J.
- **Autres composants :**

| Composant | Rôle | Licence | Livré avec l'application |
| --- | --- | --- | --- |
| Python 3.12 (image officielle `python:3.12-slim`) | Interpréteur | PSF-2.0 | Oui, dans l'image |
| Système Debian de cette image | Système du conteneur | Licence propre à chaque paquet, dont la GPL pour certains outils système | Environnement d'exécution : le code de Gotcha ne l'intègre ni ne le modifie, comme le système de n'importe quel hébergeur |
| PostgreSQL | Base de données managée de Datacloud | PostgreSQL License (permissive) | Non : service de Datacloud |
| `postgres:17-alpine` | Base jetable des tests en CI | PostgreSQL License | Non : CI seulement |
| pip-audit | Recherche de failles connues, en CI | Apache-2.0 ; dépend de certifi (MPL-2.0) | Non : installé dans un environnement isolé de la CI, jamais dans l'image (D14) |
| CircleCI, GitHub | Intégration continue, hébergement du code | Services en ligne | Non |
| Logo, favicon, feuille de style, JavaScript | Interface | Créés par l'équipe | Oui |
| Polices | Texte | Polices du système du visiteur | Aucune police livrée |

## 4. Originalité et droits des tiers

- **Code :** le dépôt a été créé le 2 novembre 2026 (premier commit `e2e0c97`), après l'ouverture du concours le 29 septembre. Aucun élément de code antérieur au concours n'y est intégré. Si un membre en intègre un, il le déclare ici avant la soumission (article 6).
- **Contenu :** les fiches et les pièges sont écrits par l'équipe à partir de sources citées sur chaque page. Rien n'est copié, et rien n'est publié sans relecture humaine (D10).
- **Contributions des visiteurs :** publiées sous licence CC BY 4.0 (D12). Les données personnelles se limitent au pseudo et à l'e-mail.
- **Pannes :** le flux public d'incidents de Flutterwave est lu en direct. Chaque incident garde le lien vers sa page d'origine quand le flux le fournit.
- **Licence du code :** droits réservés à l'équipe (D13), sans fichier de licence. Le dépôt est public, mais le code n'est pas réutilisable sans accord.

## 5. Déclaration de titularité

Chaque membre la fait lors de la soumission (article 6). Texte type :

> Je déclare que le projet Gotcha a été créé en dehors de toute mission confiée par un employeur, un client ou un établissement d'enseignement susceptible d'en revendiquer les droits.

Un membre qui ne peut pas signer cette phrase (stage, contrat, projet d'école) doit joindre l'**autorisation écrite** de l'employeur, du client ou de l'établissement concerné.

| Membre | Déclaration faite | Autorisation à joindre |
| --- | --- | --- |
| Abdoul Aziz | [ ] | [ ] Sans objet · [ ] Jointe |
| Loum | [ ] | [ ] Sans objet · [ ] Jointe |
| Khalifa | [ ] | [ ] Sans objet · [ ] Jointe |

## 6. Déclaration de l'usage des outils d'IA

L'usage des outils d'IA est libre, mais il doit être déclaré lors de la soumission : les outils utilisés et les parties du projet concernées (article 6). Il ne donne ni bonus ni pénalité. En revanche, le jury note la maîtrise de toute la solution, y compris des parties produites avec l'IA (annexe 1).

La déclaration se fait dans le formulaire. Elle doit être **exacte et complète** : une déclaration inexacte est une fraude (article 10). Pour n'oublier aucune partie, chaque membre passe en revue :

- le code : backend, interface, serveur MCP, import des pannes, tests, CI et déploiement ;
- la documentation du dépôt ;
- le contenu : recherche des sources, rédaction des fiches et des pièges ;
- les visuels, la vidéo et le pitch.

Le règlement demande aussi de garantir que cet usage respecte les conditions d'utilisation des outils et les droits des tiers.

## 7. Maîtrise de la solution devant le jury

La qualité technique compte pour 30 % de la note, et la maîtrise par l'équipe en fait partie (annexe 1). Chaque membre doit pouvoir expliquer ses parties, et les grandes lignes de celles des autres.

| Partie | Qui l'explique | Ce qu'il faut savoir justifier |
| --- | --- | --- |
| Architecture : couches, ports, deux stockages, tests de contrat | Abdoul Aziz | D1, D4, D17 ; [ARCHITECTURE.md](ARCHITECTURE.md) |
| PostgreSQL : schéma, migrations, préparation au démarrage | Abdoul Aziz | D6, D18 ; `migrations/`, `scripts/release.py` |
| Sécurité : CSP, CSRF, quotas derrière le proxy, relecteurs | Abdoul Aziz | D19 ; [app/security/README.md](../app/security/README.md) |
| Déploiement : Datacloud, Serverless ou VPS, variables | Abdoul Aziz | [deploy/README.md](../deploy/README.md) |
| Licences : pourquoi ni requests, ni httpx, ni psycopg | Abdoul Aziz | D2, D3, D14 ; [LICENCES.md](LICENCES.md) |
| Interface : 3G, sans JavaScript indispensable, accessibilité | Loum | D1 ; budget de 200 Ko par page |
| Serveur MCP : outils, réponses, signalement des pannes | Khalifa | D8 ; [DEMO.md](DEMO.md) |
| Pannes : flux Flutterwave, règles d'état | Khalifa | D7 ; `app/services/status.py` |
| Contenu : sources, vérification, publication | Les trois | D10 ; [content/README.md](../content/README.md) |

Pour s'entraîner, chacun présente aux deux autres une partie qu'il n'a pas écrite, puis répond à leurs questions.

## 8. Le jour J (samedi 14 novembre)

1. **Code :** `main` à jour, CI verte, aucune PR en attente qui doive faire partie de la soumission.
2. **Licences :** lancer `python scripts/check_licenses.py --markdown`. Si `docs/LICENCES.md` change, le faire fusionner.
3. **Site en ligne :**
   - `/healthz?db=1` répond `"database":"ok"` ;
   - HTTPS actif ;
   - les brouillons n'apparaissent pas ;
   - le serveur MCP répond.
   Faire aussi les vérifications de [app/security/README.md](../app/security/README.md).
4. **Chiffres :** compter les pièges publiés et mettre à jour les textes de la section 2.
5. **Formulaire :** coller les textes et les liens de la section 2, puis joindre la liste des composants (section 3).
6. **Déclarations :** titularité de chaque membre (section 5) et usage des outils d'IA (section 6).
7. **Après l'envoi :** faire une capture de la confirmation et cocher la section 1.
8. **Jusqu'aux résultats (23 novembre) :**
   - garder le site en ligne et le produit Datacloud payé ;
   - ne déployer que des corrections ;
   - surveiller `/healthz`.

## 9. Votes

| Étape | Dates | À faire |
| --- | --- | --- |
| Vote des pairs | 15 nov. 18 h – 16 nov. 23 h 59 | **Les trois votent** : un seul oubli exclut le projet (article 7) |
| Vote du public (10 % de la note au plus) | 17 – 20 nov. | Message de campagne prêt avant le 15 ; Galsen DEV, écoles, testeurs. Chaque vote est confirmé par e-mail : prévenir les votants |
| Jury | 21 – 22 nov. | Démo répétée, chacun capable d'expliquer son code (section 7) |
| Résultats | 23 nov. | |
