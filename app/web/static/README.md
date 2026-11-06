# `app/web/static/` : CSS, JavaScript, images

**Responsable :** Loum. **Relecteur :** Abdoul Aziz.

Servis tels quels sous `/static/…`. Pas d'étape de compilation, pas de dépendance npm.

## Ce que contient ce dossier

| Fichier | Contenu |
| --- | --- |
| `css/app.css` | Styles communs à toutes les pages : jetons, base, en-tête, pied de page, composants, utilitaires |
| `css/accueil.css` | Styles de l'accueil seulement (hero, démo, sections, FAQ), chargés par `pages/home.html` |
| `css/pages.css` | Styles des autres pages (fiche, recherche, formulaires, pannes, textes, panneaux) ; chaque page charge deux feuilles au plus, pour rester sous 200 Ko |
| `js/app.js` | Amélioration progressive : définition du glossaire au toucher. Le site marche sans |
| `img/logo.svg`, `img/favicon.svg` | Logo provisoire, à remplacer (L1) |

## Comment faire

- **Mobile d'abord** : styles de base pour les petits écrans, puis `@media (min-width: 48rem)` pour les grands.
- Les couleurs, tailles et espacements passent par les **jetons** (`--color-…`, `--space-…`) de la section 1 ; on ne met pas de couleur en dur dans un composant. Les jetons du thème sombre sont dans le bloc `prefers-color-scheme: dark`.
- Nommage des classes : `bloc`, `bloc__element`, `bloc--variante` (ex. `card__title`, `badge--down`).
- Polices : celles du système (rapides, aucune requête). Une police personnalisée doit être hébergée ici, en `woff2`, et peser moins de 30 Ko.
- Images : SVG de préférence. Une image matricielle passe par un outil de compression et fait moins de 50 Ko.

## Budget

Une page et tous ses fichiers : **moins de 200 Ko** (vérifié par `tests/web/test_pages.py`). Aujourd'hui : environ 25 Ko.

## À ne pas faire

- Ajouter un framework CSS ou JavaScript (Bootstrap, Tailwind par CDN, React…) : poids, CSP et licences.
- Charger une ressource externe : la CSP la bloque.
- Rendre une fonction indispensable dépendante de JavaScript : tout doit marcher sans.
