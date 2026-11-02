# Démo du jury (3 minutes)

**Responsable :** Khalifa (scénario, agent, test automatisé, tâche K8), avec Loum (écrans) et Abdoul Aziz (mise en ligne).

**Message :** un agent IA qui intègre MTN MoMo et déploie sur Datacloud, sans puis avec Gotcha, et une panne qui remonte en direct.

## Scénario

| Temps | Ce qu'on montre | Ce qu'on dit |
| --- | --- | --- |
| 0:00 | Un agent de code reçoit la consigne : « Ajoute le paiement MTN MoMo à cette petite boutique » | Le problème : la doc ne dit pas tout |
| 0:30 | **Sans Gotcha** : l'agent oublie l'en-tête `X-Target-Environment`, l'appel au bac à sable échoue | Ce que vivent les devs, et leurs agents |
| 1:00 | **Avec Gotcha** (serveur MCP branché) : l'agent appelle `get_fiche`, applique le piège, le paiement passe | Le savoir des devs, lisible par les agents |
| 1:40 | L'agent lit la fiche Datacloud et déploie la boutique du premier coup | Utile aussi pour les autres équipes |
| 2:10 | Un dev signale une panne d'Orange Money Sénégal : la fiche passe en « dégradé », l'agent prévient et propose un repli | Les pannes en direct |
| 2:40 | Sur mobile, un étudiant ouvre la même fiche en mode pas à pas ; le pied de page rappelle « Hébergé à Dakar » | Accessible aux débutants, souverain |

Le piège exact sera choisi après le test du bac à sable (K3) : `X-Target-Environment` s'il se reproduit, sinon la devise EUR.

## Préparation

- [ ] Configuration du client MCP de l'agent pointant vers `https://<domaine>/mcp`
- [ ] Projet « boutique » minimal prêt, dans deux états (sans et avec Gotcha)
- [ ] Comptes bac à sable MTN MoMo fonctionnels, clés dans les variables d'environnement
- [ ] Test automatisé reproductible du scénario (ne dépend pas de l'humeur de l'agent)
- [ ] Vidéo de secours enregistrée (K11)
- [ ] Démo répétée **10 fois** avant le 14 novembre

## Si quelque chose casse en direct

1. Basculer sur la vidéo de secours, sans s'excuser longuement.
2. Montrer le test automatisé qui rejoue le scénario.
3. Montrer la fiche dans le navigateur : le piège, ses sources, ses confirmations.
