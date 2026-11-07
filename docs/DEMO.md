# Démo du jury (3 minutes)

**Responsable :** Khalifa (scénario, agent, test automatisé, tâche K8), avec Loum (écrans) et Abdoul Aziz (mise en ligne).

**Message :** les solutions que les développeurs découvrent ne se perdent plus. Un agent retrouve une solution vérifiée, un autre en propose une nouvelle, et une panne remonte en direct.

## Scénario

| Temps | Ce qu'on montre | Ce qu'on dit |
| --- | --- | --- |
| 0:00 | Un agent de code reçoit la consigne : « Ajoute le paiement MTN MoMo à cette petite boutique » | Le problème : la doc ne dit pas tout |
| 0:30 | **Sans Gotcha** : l'agent échoue sur le piège retenu, ou y passe plus de temps et de tokens. On montre le résultat réel du test | Ce que vivent les devs, et leurs agents |
| 1:00 | **Avec Gotcha** : connexion GitHub en un clic, l'agent appelle `get_fiche`, applique le piège et cite sa source et son niveau de confiance | Le savoir vérifié, lisible par les agents |
| 1:30 | L'agent résout un problème absent de Gotcha, montre un brouillon à son développeur et le propose. Un relecteur le publie | Les solutions ne se perdent plus |
| 1:40 | L'agent lit la fiche Datacloud et déploie la boutique du premier coup | Utile aussi pour les autres équipes |
| 2:10 | Un dev signale une panne d'Orange Money Sénégal : la fiche passe en « dégradé », l'agent prévient et propose un repli | Les pannes en direct |
| 2:40 | Sur mobile, un étudiant ouvre la même fiche en mode pas à pas ; le pied de page rappelle « Hébergé à Dakar » | Accessible aux débutants, souverain |

**Le piège est choisi parmi les échecs réels d'un agent sans Gotcha** (au moins 5 essais avec et sans Gotcha, en mesurant tokens, tentatives, temps et réussite), et reproduit dans le bac à sable (K3). Un agent connaît peut-être déjà `X-Target-Environment` : ne rien affirmer sans ce test. Sans gain mesuré, on ne promet pas d'économie de tokens et on défend le savoir vérifié et les pannes.

## Préparation

- [ ] Configuration du client MCP de l'agent pointant vers `https://<domaine>/mcp`
- [ ] Projet « boutique » minimal prêt, dans deux états (sans et avec Gotcha)
- [ ] Comptes bac à sable MTN MoMo fonctionnels, clés dans les variables d'environnement
- [ ] Test de l'agent sans puis avec Gotcha, résultats notés ici
- [ ] Test automatisé reproductible du scénario (ne dépend pas de l'humeur de l'agent)
- [ ] Vidéo de secours enregistrée (K11)
- [ ] Démo répétée **10 fois** avant le 14 novembre

## Si quelque chose casse en direct

1. Basculer sur la vidéo de secours, sans s'excuser longuement.
2. Montrer le test automatisé qui rejoue le scénario.
3. Montrer la fiche dans le navigateur : le piège, ses sources, ses confirmations.
