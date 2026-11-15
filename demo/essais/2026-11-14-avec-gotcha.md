# Essai du 14 novembre 2026 : avec Gotcha

Agent : un agent de codage du commerce, sans accès au web, outils de fichiers seulement, plus les outils de lecture du serveur MCP de Gotcha (contenu de production, brouillons masqués).
Consigne : « Intègre le paiement Wave à cette boutique, je veux tester dans le bac à sable. » (dossier `demo/boutique`).
Coût : 0.29 $, 17 tours, 67 s.

Réponse finale de l'agent, recopiée telle quelle :

---

Je ne peux pas lancer le test sans votre approbation, et la demande a été refusée ou n'a pas abouti. Je n'ai donc pas pu exécuter le flux de bout en bout.

## Ce qui est fait

Le code est écrit, mais **il n'a pas été exécuté**.

- **`wave_client.py`** (nouveau)
  - `WaveHttp` appelle la vraie API : `POST /v1/checkout/sessions` avec le montant en texte, la devise `XOF`, `client_reference`, `success_url` et `error_url`. Il relit aussi la session avec `GET`.
  - `WaveFake` simule Wave en mémoire, avec une fausse page de paiement locale.
  - `verify_signature` contrôle `Wave-Signature` (`t=…,v1=…`). C'est un HMAC-SHA256 de l'horodatage suivi du corps brut. La requête est rejetée si la signature diffère ou si l'horodatage a plus de 5 minutes.
- **`app.py`** (modifié)
  - `POST /payer` crée la commande et la session, puis redirige vers `wave_launch_url`.
  - `POST /webhook/wave` vérifie la signature et répond 2xx tout de suite. Il traite chaque `id` d'événement une seule fois. Avant de marquer la commande payée, il relit la session et vérifie `payment_status == succeeded`.
  - `/succes` relit la session au retour du client au lieu de croire l'URL.
  - `/erreur` affiche le message d'échec.
  - L'état des commandes est gardé en mémoire, donc il est perdu au redémarrage. Il faudra une base de données avant la production.

## Le point sur le « bac à sable »

D'après la fiche Gotcha, Wave n'a **pas de bac à sable public**. Ce point est classé « sourced » : il vient de la documentation et n'a pas été testé par Gotcha. La clé d'API est liée à un vrai compte Wave Business, qu'il faut ouvrir en avance. Voici donc deux façons de tester :

- **Mode `fake` (par défaut)** : `python app.py`, puis http://localhost:8080. Le bouton « Payer » mène à une fausse page Wave où vous choisissez « Payer » ou « Échouer ». Le webhook signé est envoyé à la vraie route.
- **Mode `live`** : `WAVE_MODE=live WAVE_API_KEY=… WAVE_WEBHOOK_SECRET=… BASE_URL=<url publique> python app.py`. Il faut une URL publique pour le webhook, et vous payez de vrais petits montants. Le portail Wave Business peut envoyer un événement `test.test_event` pour tester le webhook sans payer.

## Non vérifié

La forme exacte du JSON des événements (`data` contenant la session) est ma supposition d'après la fiche. Vérifiez-la avec un premier événement réel.

Pour tester, j'ai préparé `flow_test.py` dans le répertoire temporaire de la session. Il lance l'app et vérifie le paiement, l'échec, un webhook non signé et un horodatage périmé. Autorisez-moi à l'exécuter, ou lancez simplement `python app.py` et essayez le flux dans le navigateur.
