# Démo du jury (3 minutes)

**Responsable :** Khalifa (scénario, agent, test automatisé, tâche K8), avec Loum (écrans) et Abdoul Aziz (mise en ligne).

**Message :** les solutions que les développeurs découvrent ne se perdent plus. Un agent retrouve une solution sourcée, avec son niveau de confiance, un autre en propose une nouvelle, et une panne remonte en direct.

## Scénario

| Temps | Ce qu'on montre | Ce qu'on dit |
| --- | --- | --- |
| 0:00 | Un agent de code reçoit la consigne : « Intègre le paiement Wave à cette boutique, je veux tester dans le bac à sable » | Le problème : ce savoir est difficile à trouver |
| 0:30 | **Sans Gotcha** : l'agent prépare une configuration pour un bac à sable que la documentation de Wave ne mentionne pas. On montre son vrai résultat | Ce que vivent les devs, et leurs agents |
| 1:00 | **Avec Gotcha** : connexion GitHub en un clic, l'agent appelle `get_fiche`, prévient qu'aucun bac à sable n'est documenté, simule l'appel en local et cite sa source et son niveau de confiance | Le savoir sourcé, avec son niveau de confiance, lisible par les agents |
| 1:30 | L'agent résout un problème absent de Gotcha, montre un brouillon à son développeur et le propose. Un relecteur le publie | Les solutions ne se perdent plus |
| 2:10 | Une panne d'Orange Money Sénégal est signalée : la fiche passe en « dégradé », et l'agent prévient avant d'écrire le code | Les pannes en direct |
| 2:40 | Sur mobile, un étudiant ouvre la même fiche en mode pas à pas et écoute une dizaine de secondes d'explication en wolof, avec sa transcription (si l'audio est livré, D26) ; le pied de page rappelle « Hébergé à Dakar » | Accessible aux débutants, souverain |

**À trancher avant de figer ce scénario :** l'absence de bac à sable Wave n'est qu'au niveau « sourcé », et notre propre fiche Orange Money cite un article intitulé « bac à sable Wave et Orange Money » (Kolonell). Si un environnement de test Wave existe, un juré pourrait montrer que l'agent sans Gotcha avait raison. Il faut lire cette source, puis vérifier avec un vrai compte Wave Business (voir la préparation). Si un bac à sable existe, on change de piège pour la démo (M-Pesa, ci-dessous).

**Le cœur de la démo reste Wave sans puis avec Gotcha, et la panne en direct.** Le wolof la complète sans la remplacer : un jury panafricain ne le comprendra pas forcément, d'où une séquence courte et sa transcription.

**Piège de rechange :** M-Pesa, où l'agent fait confiance au callback sans demander le statut à Safaricom. La fiche Datacloud reviendra dans la démo quand elle sera écrite à partir de notre déploiement (A10).

**Ne pas utiliser `X-Target-Environment` :** l'agent le connaît déjà, même sans web et sans Gotcha. La démo prévue au départ n'aurait rien montré.

## Résultats de l'essai du 4 novembre

Un agent de code du commerce, avec un modèle économique, a reçu la même consigne dans un dossier vide. Chaque case compte 5 essais, et le score mesure la part des pièges de la fiche pris en compte dans le code ou le README produit.

| Tâche | Sans web ni Gotcha | Avec le web | Avec Gotcha |
| --- | --- | --- | --- |
| MTN MoMo | 100 % | 100 % | 100 % |
| Orange Money Sénégal | 90 % | 93 % | 100 % |
| M-Pesa | 60 % | 70 % | 100 % |
| Wave Sénégal | 50 % | 40 % | 100 % |
| Datacloud | 25 % | 75 % | 100 % |

**Les écarts les plus nets :**

| Ce qui est vérifié | Sans web | Avec le web | Avec Gotcha |
| --- | --- | --- | --- |
| Wave : dire qu'aucun bac à sable n'est documenté | 0 sur 5 | 0 sur 5 | 5 sur 5 |
| M-Pesa : confirmer le paiement par une requête de statut | 1 sur 5 | 0 sur 5 | 5 sur 5 |
| Datacloud : citer `platform.systalink.com` | 0 sur 5 | 4 sur 5 | 5 sur 5 |
| Orange Money en panne : prévenir le développeur | Impossible | Non testé | 5 sur 5 |

**Coût pour l'ensemble des cinq tâches** (somme des médianes de tokens et de temps, somme des coûts moyens) : ce que coûte l'agent **avec Gotcha**, par rapport à chaque autre agent :

| L'agent avec Gotcha, comparé à… | Tokens | Coût | Temps |
| --- | --- | --- | --- |
| l'agent qui cherche sur le web | -21 % (moins cher) | -51 % | -26 % |
| l'agent sans web ni Gotcha | +40 % (plus cher) | +30 % | +14 % |

**Ce qu'on peut dire :** un agent qui consulte Gotcha couvre plus de pièges, et il coûte moins qu'un agent qui cherche sur le web. Il coûte plus qu'un agent qui répond de mémoire, souvent à tort sur ces services. On ne promet donc pas une « économie de tokens » sans préciser la comparaison.

**Les limites de cet essai :**
- 5 essais par case, un seul agent et son modèle le moins cher : un modèle plus fort peut réduire les écarts.
- Les points vérifiés viennent de nos propres fiches, ce qui avantage Gotcha par construction.
- Un point vérifié veut dire que le code ou le README en tient compte, pas que le code marche : aucune API de paiement n'a été appelée.
- Les pièges eux-mêmes sont encore au niveau « sourcé ». Si une fiche se trompe, l'agent recopie l'erreur.
- La consigne Wave demande un bac à sable, ce qui pousse l'agent à en supposer un.
- L'agent avait déjà Gotcha installé, sans connexion, et le serveur lui demandait de le consulter. Il l'a fait dans tous les essais.

## Préparation

- [ ] Configuration du client MCP de l'agent pointant vers `https://<domaine>/mcp`
- [ ] Projet « boutique » minimal prêt, dans deux états (sans et avec Gotcha)
- [ ] Comptes Wave Business et bac à sable Daraja, pour vérifier ce que la démo affirme ; lire l'article Kolonell cité plus haut et **trancher l'existence d'un bac à sable Wave** avant de figer le scénario
- [ ] **Relire et publier les pièges Wave et M-Pesa de la démo** (`publication: published`, `verified_by` d'un humain qui n'en est pas l'auteur) : en production, les brouillons sont invisibles et `get_fiche` ne les trouverait pas. Le 5 sur 5 a été obtenu avec le brouillon visible. Responsables : Loum (Wave, L11) et Khalifa (M-Pesa, K10), au plus tard le **lun. 9** ; Aziz vérifie sur le site en ligne
- [x] Test de l'agent sans puis avec Gotcha, résultats notés ici
- [ ] Refaire ce test avec l'agent qui servira à la démo, avant de figer le scénario
- [ ] Test automatisé reproductible du scénario (ne dépend pas de l'humeur de l'agent)
- [ ] Vidéo de secours enregistrée (K11)
- [ ] Démo répétée **10 fois** avant le 14 novembre

## Si quelque chose casse en direct

1. Basculer sur la vidéo de secours, sans s'excuser longuement.
2. Montrer le test automatisé qui rejoue le scénario.
3. Montrer la fiche dans le navigateur : le piège, ses sources, ses confirmations.
