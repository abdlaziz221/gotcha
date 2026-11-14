# Démo du jury

Le scénario, minute par minute, est dans [docs/DEMO.md](../docs/DEMO.md). Ce dossier contient ce qu'il faut pour le jouer.

| Fichier | Rôle |
| --- | --- |
| `boutique/` | La boutique sur laquelle travaille l'agent : une page produit, un bouton « Payer avec Wave » pas encore branché |
| `mcp-gotcha.json` | Branche l'agent sur le serveur MCP en ligne (connexion GitHub au premier appel) |
| `check_live.py` | À lancer juste avant de monter sur scène : vérifie que le site en ligne est prêt |

Le test automatique qui rejoue le scénario est `tests/mcp/test_demo_scenario.py`.

## Avant de monter sur scène

```bash
python demo/check_live.py
```

Toutes les lignes doivent dire OK. Sinon, on passe directement à la vidéo de secours.

Préparer ensuite deux copies de la boutique, dans deux terminaux :

```bash
cp -r demo/boutique /tmp/boutique-sans
cp -r demo/boutique /tmp/boutique-avec
cp demo/mcp-gotcha.json /tmp/boutique-avec/.mcp.json
```

Dans `/tmp/boutique-avec`, lancer l'agent une première fois **avant la démo** et faire la connexion GitHub : sur scène, le clic « Autoriser » est déjà fait.

## Sur scène

Même consigne dans les deux terminaux :

> Intègre le paiement Wave à cette boutique, je veux tester dans le bac à sable.

- **Sans Gotcha** (`/tmp/boutique-sans`) : on montre la configuration qu'il propose pour un bac à sable que la documentation de Wave ne mentionne pas.
- **Avec Gotcha** (`/tmp/boutique-avec`) : l'agent appelle `get_fiche`, prévient qu'aucun bac à sable n'est documenté, isole l'appel à Wave pour le simuler, et cite sa source et son niveau de confiance.

## Si quelque chose casse

1. Vidéo de secours.
2. `python -m pytest tests/mcp/test_demo_scenario.py -v` : rejoue le scénario, sans agent, en quelques secondes.
3. La fiche dans le navigateur : <https://gotcha-80c95631.platform-systalink.com/fiches/wave-sn>.
