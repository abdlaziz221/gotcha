# `app/web/templates/` : les gabarits HTML

**Responsable :** Loum. **Relecteur :** Abdoul Aziz.

Gabarits Jinja2. Toutes les pages existent déjà et marchent avec les fausses données : le travail consiste à les **concevoir et les finir**, pas à attendre le backend.

## Ce que contient ce dossier

```
base.html               Mise en page commune : en-tête, navigation, pied de page « Hébergé à Dakar »
components/             Macros réutilisables
├── flash.html          Message après une action (?ok=…)
├── status.html         Badge d'état d'un service, élément de la liste des pannes
├── cards.html          Carte de fiche, carte de piège (avec « ça marche encore »), liste de sources
└── forms.html          Champs de formulaire (texte, zone de texte, liste), barre de recherche
pages/                  Une page par fichier, chacune étend base.html
```

Chaque page reçoit `page` (son contexte, décrit dans `app/web/viewmodels.py`), `csrf_token`, `site` et `request`. Tableau des pages et de leurs contextes : [docs/CONTRACTS.md](../../../docs/CONTRACTS.md), section 3.

## Tâches

| Id | Tâche | Échéance |
| --- | --- | --- |
| L1 | Design system : couleurs, typographie, logo, composants (dans `/styleguide`) | mar. 3 |
| L2 | `pages/home.html` : la promesse comprise en 5 secondes | mer. 4 |
| L3 | `pages/fiche.html` : lecture mobile, mode pas à pas, glossaire au toucher | mer. 4 |
| L4 | `pages/search.html` | jeu. 5 |
| L5 | `pages/contribute.html`, bouton « ça marche encore », `pages/message.html` | jeu. 5 |
| L6 | `components/status.html`, `pages/incidents.html`, `pages/report_outage.html` | ven. 6 |
| L7 | `pages/data.html`, `pages/glossary.html`, pied de page | ven. 6 |
| L8 | `pages/review.html` | ven. 6 |
| L9 | `pages/error.html`, états vides | sam. 7 |
| L10 | Audit mobile, 3G, accessibilité | dim. 8 |
| L14 | Lecteur audio et transcription sur la fiche, si le socle est en ligne (D26) | lun. 9 |
| L15 | Afficher près de chaque piège qui l'a apporté et qui l'a relu | lun. 9 |

## Comment faire

- Lancer `uvicorn app.main:app --reload` et ouvrir **`/styleguide`** : tous les composants y sont, avec tous leurs états (normal, dégradé, en panne, brouillon, à revérifier, erreurs de formulaire).
- Pour voir une page dans un état précis : `/fiches/wave-sn` est « dégradé » (panne fictive), `/fiches/mtn-momo?mode=pas-a-pas&etape=2` montre le mode pas à pas, `/relecture` montre deux contributions fictives.
- Une macro qui a besoin de `csrf_token` s'importe avec `with context` :

  ```jinja
  {% from "components/cards.html" import gotcha_card with context %}
  ```

- Tout formulaire POST contient :

  ```html
  <input type="hidden" name="csrf_token" value="{{ csrf_token }}">
  ```

- Les classes d'état suivent les valeurs du modèle : `badge--{{ status.status.value }}` donne `badge--normal`, `badge--degraded`, `badge--down` ou `badge--unknown`.
- Dates : filtres `date_fr` (« 28 oct. 2026 ») et `datetime_fr` (« 28 oct. 2026 à 14 h 05 »).
- Accessibilité : un seul `<h1>` par page, des `<label>` sur tous les champs, `aria-current` sur la navigation, contrastes suffisants, cibles tactiles de 44 px.

## Travailler sans attendre les autres

Besoin d'une donnée qui n'est pas dans le contexte ? L'ajouter dans `app/web/viewmodels.py` (avec une valeur par défaut) et la remplir dans `app/web/presenters.py`, ou demander à Abdoul Aziz. En attendant, travailler avec ce qui existe : le contrat ne change pas sous vos pieds.

## Tester

```bash
pytest tests/web
```

Le test des liens morts parcourt tout le site depuis l'accueil ; le test de poids vérifie qu'une page et ses fichiers font moins de 200 Ko.

## À ne pas faire

- **Aucun style ni script en ligne** (`style="…"`, `<script>…</script>`, `onclick=`) : la politique de sécurité (CSP) les bloque. Tout va dans `static/`.
- Jamais `|safe` : les champs `*_html` sont déjà nettoyés et s'affichent tels quels.
- Pas de lien vers une page qui n'existe pas encore.
- Pas de ressource externe (police Google, CDN, image distante) : la CSP les bloque, et la souveraineté l'interdit.
