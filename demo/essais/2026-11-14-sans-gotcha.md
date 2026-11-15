# Essai du 14 novembre 2026 : sans Gotcha

Agent : un agent de codage du commerce, sans accès au web, outils de fichiers seulement.
Consigne : « Intègre le paiement Wave à cette boutique, je veux tester dans le bac à sable. » (dossier `demo/boutique`).
Coût : 0.26 $, 12 tours, 39 s.

Réponse finale de l'agent, recopiée telle quelle :

---

Le paiement Wave est branché dans `app.py`, mais je ne l'ai pas testé. Je n'ai pas pu lancer la vérification de syntaxe (`py_compile`), car la commande demandait une approbation que je n'ai pas obtenue. Il n'y a pas non plus de clé API Wave ici.

**Ce qui change**
- Le bouton « Payer avec Wave » appelle maintenant `create_wave_session()`. Cette fonction envoie `POST {WAVE_API_BASE}/v1/checkout/sessions` avec le montant en XOF, une référence de commande unique et les URLs de retour. Elle redirige ensuite le client (303) vers le `wave_launch_url` renvoyé.
- Deux pages de retour ont été ajoutées : `/succes` et `/echec`.
- Si la clé manque ou si Wave refuse la session, la page affiche une erreur lisible (500 ou 502) avec le détail renvoyé par Wave.
- Il n'y a toujours aucune dépendance : le code utilise seulement `urllib`.
- Le README est mis à jour.

**Pour tester**
```bash
export WAVE_API_KEY="..."                      # clé de test du portail Wave Business
export SHOP_BASE_URL="https://xxxx.ngrok.app"  # tunnel HTTPS vers localhost:8080
python app.py
```

Il faut d'abord vérifier la syntaxe avec `python3 -m py_compile app.py`.

**À savoir**
- **Tunnel HTTPS :** d'après ma connaissance de l'API Wave, `success_url` et `error_url` doivent être en HTTPS. En local, il faut donc un tunnel comme ngrok ou cloudflared, et `SHOP_BASE_URL` doit pointer dessus. Je n'ai pas pu le vérifier dans la documentation.
- **Bac à sable :** je n'ai pas supposé d'URL de sandbox. `WAVE_API_BASE` vaut `https://api.wave.com` par défaut. Si votre compte de test utilise un autre hôte, changez cette variable.
- **Confirmation du paiement :** le retour sur `/succes` ne prouve pas que le paiement est passé. Pour la production, il faudra un webhook ou une vérification côté serveur de l'état de la session. Je peux l'ajouter si vous voulez.
