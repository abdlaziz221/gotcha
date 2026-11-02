# `app/ingest/` : l'import des pannes

**Responsable :** Khalifa. **Relecteur :** Abdoul Aziz.

Lit le flux public d'incidents de Flutterwave (format Statuspage v2, `https://status.flutterwave.com/api/v2/incidents.json`), qui couvre notamment Orange Money et Wave au Sénégal, et le traduit en pannes Gotcha (`Incident`).

## Ce que contient ce dossier

| Fichier | Rôle |
| --- | --- |
| `flutterwave.py` | `map_incident` (texte → service et pays), `parse_incidents`, `FlutterwaveFeed` (lecture en direct ou depuis l'extrait enregistré) |
| `__main__.py` | `python -m app.ingest` : un rafraîchissement, pour une tâche planifiée sur VPS |

## Comment ça marche

1. Le flux ne donne ni l'opérateur ni le pays sous forme structurée : on les **déduit du texte** (titre et messages).
2. Opérateurs reconnus : Orange, MTN, M-Pesa et Safaricom, Wave. D'autres sont connus mais non suivis (Airtel, Telecel, InTouch…) : un incident qui ne cite qu'eux est ignoré.
3. Pays : noms cités dans le texte, sinon devise d'un seul pays (GHS → Ghana, KES → Kenya…). XOF et XAF couvrent plusieurs pays : on n'en déduit rien.
4. Incident Mobile Money sans opérateur cité : une panne « sans service » par pays, qui concerne tous les services de paiement du pays.
5. Une panne par couple (service, pays), avec un identifiant stable : `flutterwave:<id>:<pays>:<service>`.

**Quand le flux est lu :** à l'ouverture d'une page, en tâche de fond, si la dernière lecture date de plus de 10 minutes (`IncidentService.refresh_if_stale`). Sur un VPS, on peut aussi lancer `python -m app.ingest` toutes les 10 minutes.

## Tâches

| Id | Tâche | Échéance |
| --- | --- | --- |
| K4 | Affiner la correspondance opérateur et pays sur le flux **en direct** ; ajouter chaque cas réel aux tests | jeu. 5 |

## Comment faire

- L'extrait réel enregistré est dans `fixtures/flutterwave_incidents.json` (9 incidents d'octobre 2026). Pour en ajouter un : copier l'incident depuis le flux en direct dans ce fichier, puis écrire le test attendu dans `tests/ingest/test_flutterwave.py`.
- Pour lire le flux en direct en local : `GOTCHA_INGEST_LIVE=true uvicorn app.main:app --reload`.
- Lecture réseau avec `urllib` (bibliothèque standard), HTTPS uniquement, délai de 5 secondes : jamais `requests` ni `httpx` (certifi, licence MPL).
- Une erreur de lecture ne casse jamais une page : elle est journalisée et la lecture est retentée plus tard.

## Tester

```bash
pytest tests/ingest
```

## À ne pas faire

- Attribuer une panne à un opérateur « au hasard » : mieux vaut une panne sans service qu'une fausse alerte sur Wave.
- Lire le flux à chaque requête : respecter l'intervalle minimal.
