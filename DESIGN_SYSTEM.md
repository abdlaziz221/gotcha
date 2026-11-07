# Système de design Gotcha

Référence visuelle du site. Responsable : Loum (`app/web/static/`, `app/web/templates/`).

Ce document est la règle. Le CSS et les gabarits s'y conforment ; en cas d'écart, on corrige le code, pas le document, sauf décision explicite.

Statut : version 3, 5 novembre 2026. Couleurs et typographie reprises des maquettes de référence (orange vif, bordeaux, linéale et italique à empattement), adaptées au contenu de Gotcha et à l'accessibilité. Les pages de la PR 51 (connexion, données, relecture) restent à migrer après sa fusion.

---

## 1. Intention

Gotcha est un carnet de terrain technique avec une identité chaleureuse : fond blanc, cartes gris très clair, un orange vif comme signature, un bordeaux profond pour les moments forts, et des titres qui mêlent une linéale sobre et une italique à empattement.

- **Public** : un développeur, souvent débutant, sur téléphone et en 3G. Il doit comprendre l'accueil en cinq secondes, sans compte.
- **Densité** : aérée. De grands titres, peu d'éléments par écran, des cartes gris clair sans bordure lourde.
- **Mise en page** : asymétrique. Une colonne principale de lecture et un volet secondaire, plutôt que des grilles de cartes identiques.
- **Mouvement** : presque aucun. Un retour visuel au clic et au survol, rien d'autre.

### Logo (« Got you »)

Le fichier `app/web/static/img/logo.svg` (et `favicon.svg`) réunit quatre références au double sens de *Gotcha* (*« Got you »* : le piège qui vous attrape, et le pair qui vous couvre) dans une grille de `64 × 64` :

1. **Le monogramme `G`** : un arc circulaire blanc (`#FFFFFF`, trait de `6px` à terminaisons arrondies) sur médaillon orange signature (`#FF6819`, rayon `16px`).
2. **Le viseur optique (« Got you! »)** : quatre équerres de cadrage en bordeaux profond (`#450D05`) dans les angles, qui symbolisent la détection et le verrouillage d'une anomalie non documentée.
3. **La coche et les bras ouverts (« I got you »)** : le bras rentrant du `G` plonge vers le centre et remonte en coche de confirmation (`✓`), dessinant deux bras ouverts qui rattrapent le développeur.
4. **Le piège neutralisé** : le disque bordeaux (`#450D05`) au foyer du `G`, simultanément point d'alerte intercepté au centre du viseur et silhouette humaine soutenue par la coche.

---

## 2. Couleurs

Un seul thème, clair. Pas de thème sombre, pas de fond noir. La seule zone foncée autorisée est le **bandeau bordeaux** (un par page au plus). Le CSS déclare `color-scheme: light`.

Chaque couleur a son contraste mesuré (WCAG 2.2). Texte : 4,5 au minimum. Bordure de champ, contour de focus, icône seule : 3 au minimum.

### Marque

| Jeton | Valeur | Rôle | Contraste |
| :--- | :--- | :--- | :--- |
| `--color-brand` | `#FF6819` | Orange signature : pastilles, anneaux, graphiques, soulignements, chiffres et texte **sur le bandeau bordeaux**, logo | 5,52 sur `#450D05` · **2,90 sur blanc : jamais de texte orange vif sur fond clair** |
| `--color-brand-soft` | `#FFA576` | Orange clair : dégradés de données, fonds d'illustration, texte secondaire sur le bandeau | 8,30 sur `#450D05` |
| `--color-brand-tint` | `#FFF0E8` | Bouton secondaire, onglet actif, sélection, message mis en avant | |
| `--color-primary` | `#CC470C` | Fond du bouton principal (texte blanc), contour de focus | 4,69 avec texte blanc |
| `--color-primary-hover` | `#B43C0A` | Survol du bouton, liens et texte orange sur fond clair | 5,26 sur `#FFF0E8` · 5,85 sur blanc |
| `--color-primary-active` | `#9A3412` | Bouton pressé, liens survolés | 6,20 sur `#FFE8DB` |
| `--color-on-primary` | `#FFFFFF` | Texte sur `--color-primary` | |
| `--color-maroon` | `#450D05` | Fond du bandeau bordeaux | 16,0 avec texte blanc |
| `--color-maroon-surface` | `#5A1A0F` | Cartes posées sur le bandeau | |

Règle : orange vif `#FF6819` pour décorer, ou pour écrire sur le bordeaux. Sur fond clair, le texte orange est `--color-primary-hover` et le bouton est `--color-primary`.

### Interface

| Jeton | Valeur | Rôle | Contraste |
| :--- | :--- | :--- | :--- |
| `--color-bg` | `#FAF9F6` | Fond crème chaud de toutes les pages | |
| `--color-surface` | `#F4F2EE` | Cartes coquille, volet latéral, encarts | |
| `--color-surface-raised` | `#FFFFFF` | Élément blanc posé sur une carte ou sur le fond crème | |
| `--color-text` | `#0B0907` | Texte principal, titres | 16,9 sur `#F4F2EE` · 17,9 sur `#FAF9F6` |
| `--color-text-secondary` | `#686058` | Partie italique des titres, descriptions, métadonnées | 5,65 sur `#FAF9F6` · 5,32 sur `#F4F2EE` |
| `--color-border` | `#E8E3DA` | Séparateurs fins chauds (1px, décoratif) | |
| `--color-border-input` | `#686058` | Bordure des champs | 5,65 sur `#FAF9F6` |

### États (services, pièges, contributions)

Fond clair teinté, texte foncé de la même famille. Les teintes vert d'eau et rose des maquettes servent de fond.

| Jeton | Texte | Fond | Usage | Contraste |
| :--- | :--- | :--- | :--- | :--- |
| `success` | `#047857` | `#E3F3E4` | Service sans panne signalée, confirmé en production, contribution publiée | 4,75 |
| `warning` | `#B45309` | `#FFF4E0` | **Réservé** : service dégradé, sévérité « Important », en attente de relecture, saisie non enregistrée | 4,61 |
| `danger` | `#B91C1C` | `#F3E3E4` | Service en panne, sévérité « Bloquant », erreur de formulaire | 5,21 |
| `info` | `#1D4ED8` | `#E8EEFB` | Niveau « Reproduit », « À revérifier » | 5,76 |
| `neutral` | `#374151` | `#EEEEEE` | État inconnu, « Sourcé », « Mineur », brouillon | 8,88 |

L'ambre (`warning`) ne sert jamais à décorer.

---

## 3. Typographie

Deux voix, comme sur les maquettes : une **linéale** nette pour tout le texte, et une **italique à empattement** grise pour la deuxième moitié des grands titres (« Ce que les devs *ont déjà résolu* sur Wave »).

### Polices

Les maquettes utilisent Neue Montreal (linéale) et IvyOra Display (italique). Ces deux polices sont commerciales et payantes : elles ne peuvent pas être embarquées sans licence achetée, et les règles du projet n'acceptent que les licences MIT, BSD, Apache, ISC ou PSF. Le site reproduit donc leur allure avec les polices du système, sans aucun téléchargement :

| Jeton | Pile | Remplace |
| :--- | :--- | :--- |
| `--font-sans` | `"Helvetica Neue", "Segoe UI", system-ui, -apple-system, Roboto, "Noto Sans", "Liberation Sans", Arial, sans-serif` | Neue Montreal |
| `--font-serif` | `"Iowan Old Style", "Palatino Linotype", Palatino, "Book Antiqua", "Noto Serif", Georgia, serif` (toujours en italique) | IvyOra Display |
| `--font-mono` | `ui-monospace, "SF Mono", "Cascadia Mono", "Roboto Mono", Menlo, Consolas, "Liberation Mono", monospace` | |

Si l'équipe achète un jour les licences et accepte de changer la règle des licences, seuls ces trois jetons changent.

### Échelle (reprise des maquettes)

| Rôle | Taille | Graisse | Interligne | Approche |
| :--- | :--- | :--- | :--- | :--- |
| Titre d'accueil (display) | `3.5rem` (56px), `2.25rem` sur mobile | 500 | 1.1 | `-0.03em` |
| Titre de page (H1) | `2.5rem` (40px), `2rem` sur mobile | 500 | 1.15 | `-0.025em` |
| Heading (H2) | `1.875rem` (30px) | 500 | 1.2 | `-0.02em` |
| Title (H3, titres de cartes) | `1.125rem` (18px) | 500 | 1.2 | |
| Body | `1.125rem` (18px) | 400 | 1.5 | |
| Description (métadonnées, aide) | `0.875rem` (14px) | 400 | 1.5 | |
| Libellé technique (chasse fixe, majuscules) | `0.75rem` (12px) | 400 | 1.2 | |

- Les titres sont en graisse 500, jamais en gras lourd : la hiérarchie vient de la taille.
- **Italique à empattement** : seulement dans les H1 et H2, sur la fin du titre, en `--color-text-secondary`. Balise `<em>` dans le titre. Jamais dans le corps du texte ni dans l'interface (boutons, métadonnées, formulaires).
- Largeur de ligne maximale : `65ch` pour tout texte courant.

### Police à chasse fixe obligatoire

`--font-mono` sert à tout ce qui se recopie à l'identique : codes d'erreur et statuts HTTP (`401`, `INVALID_SIGNATURE`), en-têtes et paramètres (`X-Target-Environment`), URL d'API, commandes, extraits de code, numéros de version.

---

## 4. Espacements, rayons, ombres

### Espacements

Échelle de base 4px : `--space-1` (4px), `--space-2` (8px), `--space-3` (12px), `--space-4` (16px), `--space-5` (20px), `--space-6` (24px), `--space-8` (32px), `--space-10` (40px), `--space-12` (48px), `--space-16` (64px), `--space-24` (96px, entre les grandes sections de l'accueil).

### Rayons

| Jeton | Valeur | Usage |
| :--- | :--- | :--- |
| `--radius-sm` | `8px` | Code en ligne |
| `--radius-md` | `14px` | Champs, encarts, sous-cartes |
| `--radius-lg` | `24px` | Cartes de fiches, cartes de pièges, bandeau bordeaux |
| `--radius-pill` | `9999px` | Boutons, champ de recherche |

### Ombres

Presque aucune : les cartes se distinguent par leur fond gris `#F6F6F6`, pas par une ombre. `--shadow-sm` (`0 1px 2px rgba(11, 9, 7, 0.05)`) seulement pour un élément blanc posé sur une carte grise. Aucune ombre colorée, aucun halo.

### Libellé de section

Petit libellé centré au-dessus d'un titre de section, entouré de deux traits fins de 24px (en CSS, pas en caractères) : `.kicker`. 14px, `--color-text-secondary`. Une par section au plus.

---

## 5. Icônes

**Lucide uniquement**, recopié en SVG inline dans les gabarits. Aucun JavaScript, aucune police d'icônes, aucune autre bibliothèque.

- Licence : ISC. Le texte de licence de Lucide est ajouté au dépôt avec les icônes.
- Emplacement : la macro Jinja `icon(name, label=None, size=20)` dans `app/web/templates/components/icons.html`, qui contient seulement les icônes utilisées. Licence : `components/LUCIDE-LICENSE.txt`.
- Taille : 16px à côté d'un texte d'état ou d'une métadonnée, 20px dans un bouton ou un titre. Trait de 2px, couleur `currentColor`, posés par la classe `.icon` dans `app.css` (pas d'attributs `stroke` sur chaque `<svg>` : la page pèse moins). La macro ne pose que `width` ; la hauteur suit le `viewBox`.
- Une icône seule (sans texte) porte un `aria-label`. Une icône à côté d'un texte porte `aria-hidden="true"`.

Correspondance fixe :

| Sens | Icône Lucide |
| :--- | :--- |
| Aucune panne signalée | `circle-check` |
| Dégradé | `triangle-alert` |
| En panne | `circle-x` |
| État inconnu | `circle-help` |
| Sourcé | `book-open` |
| Reproduit | `flask-conical` |
| Confirmé en production | `shield-check` |
| En attente de relecture | `clock` |
| Contributeur, relecteur | `user` |
| Réservé aux membres | `lock` |
| Recherche | `search` |
| Audio en wolof | `volume-2` |
| Lien externe | `external-link` |

---

## 6. Composants

### Bouton

- **Principal** : pilule, fond `--color-primary`, texte blanc, graisse 500, hauteur minimale 44px. Survol `--color-primary-hover`, pression `--color-primary-active` et `translateY(1px)`.
- **Secondaire** : pilule, fond `--color-brand-tint`, texte `--color-primary-hover`.
- **Discret** : pilule, fond blanc, bordure `--color-border-input`, texte `--color-text`.
- **Sur bandeau bordeaux** : pilule, fond `--color-brand`, texte `--color-text` (6,86).
- Surface plate : pas de dégradé, pas d'ombre colorée.
- Un seul bouton principal par zone visible.
- Toujours `<button type="button">`, `<button type="submit">` ou `<a>`. Jamais un `<div>` ou un `<span>` cliquable.
- Le libellé dit l'action : « Contribuer », « Confirmer ce piège ». Jamais « Cliquez ici ».

### État et sévérité

**Aucun badge, aucune pastille, aucune étiquette en pilule** sur le site. Un état ou une sévérité s'écrit en texte, dans la ligne de métadonnées :

- icône Lucide de 16px + libellé, dans la couleur de l'état (section 2), graisse 500, sans fond ni bordure ;
- les autres métadonnées (environnement, version, niveau de confiance, brouillon) sont du texte gris, séparées par `·` ;
- les codes d'erreur restent en `<code>`.

```html
<span class="status status--down">{{ icon("circle-x", size=16) }}En panne</span>
```

### Champ de formulaire

- Libellé visible **au-dessus** du champ, toujours. Pas de libellé flottant, pas de placeholder à la place du libellé.
- Aide en `--color-muted` **sous** le champ.
- Bordure 1px `--color-border-input`, rayon `--radius-md`, hauteur minimale 44px.
- Focus : contour 2px `--color-primary`, décalé de 2px.
- Erreur : bordure `danger`, message sous le champ avec l'icône `circle-x`, relié par `aria-describedby`.

### Carte de fiche

- Fond `--color-surface` (`#F6F6F6`), sans bordure ni ombre, rayon `--radius-lg`.
- En-tête : nom du service. Ligne suivante : état du service en texte, type, pays.
- Corps : type de service, pays, résumé en une phrase.
- Pied : nombre de pièges et date de mise à jour (`date_fr`).
- Toute la carte est un seul lien `<a>` sur le titre ; pas de lien imbriqué.

### Carte de piège

Le composant central. Ordre de lecture fixe :

1. **Titre**.
2. **Métadonnées**, en une ligne de texte : sévérité (couleur et icône), environnement, version d'API, codes d'erreur, niveau de confiance.
3. **Attribution** : contributeur et relecteur avec l'icône `user`, en texte courant, pas en note.
4. **Symptôme**, puis **Cause**.
5. **Solution**, avec bloc de code. En aperçu public, un encart remplace la solution (voir plus bas).
6. **Pistes qui ont échoué**, puis **Preuve**.
7. **Audio en wolof**, s'il existe : lecteur `<audio controls preload="none">` et transcription relue, sous le texte français qui reste la référence.
8. **Confirmation** : `<details>` avec champ de preuve et nombre de confirmations.

Fond `--color-surface`, rayon `--radius-lg`, bordure gauche de 4px aux couleurs de la sévérité (`danger`, `warning`, `neutral`). La sévérité reste aussi écrite dans les métadonnées.

### Encart

- Fond `--color-surface`, sans bordure, rayon `--radius-md`, icône à gauche.
- Texte de l'aperçu public, sans variation : « La solution est réservée aux membres. Compte gratuit, connexion avec GitHub. » avec l'icône `lock`.
- Ne jamais écrire sur une page une consigne adressée aux agents IA.

### Tableau

- En-tête en `--color-surface`, texte 14px graisse 500.
- Lignes séparées par `--color-border`.
- Sur mobile, le tableau défile horizontalement dans son conteneur ; la page, jamais.

---

## 7. Mise en page

- Mobile d'abord. Points de rupture : `40rem` et `64rem`.
- Largeur maximale du contenu : `72rem`. Marges latérales : 16px sur mobile, 24px au-delà de `40rem`.
- Hauteur pleine écran : `min-height: 100dvh`, jamais `100vh`.
- Chaque bloc a sa propre zone : aucun chevauchement, aucune position absolue décorative.
- **Pas de rangée de trois cartes identiques.** On hiérarchise : une carte large et deux étroites, ou une liste.

### Archétypes de pages

| Page | Structure |
| :--- | :--- |
| **Accueil** (`/`) | Une phrase qui dit ce qu'est Gotcha, le champ de recherche, puis la liste des fiches. Sur écran large : 2/3 fiches, 1/3 état des services en direct. |
| **Recherche** (`/recherche`) | Champ de recherche en haut, résultats en liste avec leur type (Fiche, Piège, Code d'erreur). |
| **Fiche** (`/fiches/<service>`) | Sur écran large : 2/3 pièges, 1/3 volet (état du service, pannes récentes, sources). Sur mobile, le volet passe sous l'en-tête. |
| **Pannes** (`/pannes`) | Liste chronologique, état en texte et source de chaque signalement. |
| **Contribuer** (`/contribuer`) | Formulaire en une colonne, `65ch` au plus, libellés au-dessus. |
| **Relecture** (`/relecture`) | Liste des contributions en attente (« En attente de relecture » en texte `warning` avec `clock`), détail à droite sur écran large. |
| **Connexion** | Une phrase, un bouton « Se connecter avec GitHub », la liste de ce que Gotcha garde. |

---

## 8. Mouvement

- On n'anime que `transform` et `opacity`. Jamais `top`, `left`, `width`, `height`, `margin` ni les couleurs.
- Interactions : 150 à 200ms, courbe `ease-out`. Survol d'une carte : `translateY(-2px)`, rien de plus.
- Tout en CSS. Le JavaScript ne sert qu'aux améliorations (bouton Copier, glossaire), jamais à afficher le contenu.
- Pas d'indicateur de chargement tournant. Les pages sont rendues côté serveur.
- `@media (prefers-reduced-motion: reduce)` coupe toutes les animations et affiche l'état final.
- Gotcha a sa propre signature de mouvement. On ne reprend pas les effets d'un autre site (pas d'équerres de cadrage autour des éléments, pas de cadre qui grandit au défilement, pas de cartes empilées qui s'enfoncent). Deux motifs seulement :
  - **Le trait** : un soulignement orange de 2px qui se dessine de gauche à droite (`scaleX(0)` à `scaleX(1)`, 220ms). Liens de l'en-tête, synthèse des usages, ligne corrigée de la vidéo.
  - **L'alvéole** : un petit hexagone orange (`clip-path`), écho au nid d'abeilles du fond de la vitrine. Libellés de section, séparateurs, étapes.

### Hero de l'accueil

Le hero occupe toute la largeur de l'écran (fond décrit ci-dessous) et au moins toute la hauteur visible sous l'en-tête (`min-height: calc(100dvh - 65px)`), contenu centré verticalement et fondu en bas vers `--color-bg`. Pas d'étiquette au-dessus du titre, pas de liste d'états dans le hero.

### Structure du hero

Centré, inspiré des pages produit : le titre sur deux lignes (le mot qui tourne seul sur la seconde, avec une lueur orange floue derrière lui), le sous-titre, la recherche en pilule, deux boutons (« Voir un exemple » discret, « Ajouter un piège » secondaire), puis une ligne de preuves en texte avec une coche verte (chiffres réels, gratuit, relu par des humains, Dakar). En dessous, la **vitrine** : l'aperçu de l'agent en grand cadre (conversation à gauche, réponse de Gotcha à droite), posé sur une lueur orange, avec en pied l'adresse MCP et le bouton Copier. La conversation se joue quand la vitrine arrive à l'écran.

### En-tête

Barre collante (`position: sticky; top: 0`), fond crème plein (`--color-bg`) et filet de 1px en bas :
- **À gauche** : le monogramme `Gotcha` (`32 × 32`) et le nom du site.
- **Au centre** (sur grand écran) : les quatre rubriques principales (`Rechercher`, `Pannes`, `Glossaire`, `Données`) en gris secondaire. Au survol et sur la page active : texte foncé et **trait** orange qui se dessine dessous.
- **À droite** : deux boutons du système, `Signaler` (secondaire) et `Contribuer` (principal), dont la flèche avance de 3px au survol.
- **Sur téléphone** : un menu `<details>` (icônes `menu` et `x`), qui fonctionne sans JavaScript ; la page active y porte un filet orange à gauche.

### Agents de codage autour du hero

Neuf logos d'agents compatibles MCP, **en couleur quand la marque en a** (Claude Code, Codex, Cursor, Antigravity, GitHub Copilot, Gemini CLI, Windsurf, Cline, OpenCode), dans des tuiles blanches arrondies. À partir de 90rem : comme sur une constellation, cinq à gauche et quatre à droite du texte, légèrement inclinés (4 à 8°), qui flottent de 8px en 6 à 7,5s. Placés par rapport au bloc de texte : **toujours entièrement visibles**, jamais sous l'en-tête, la vidéo ni le texte (vérifié de 1440 à 2560 px, avec 10px de marge). En dessous de 90rem : rangée centrée sous les preuves, précédée de « Se branche à tout agent compatible MCP ». Logos : Lobe Icons, licence MIT (`components/agents.html`, `components/LOBE-ICONS-LICENSE`), attribut `style` retiré pour la CSP. Les marques appartiennent à leurs propriétaires.

### Fond du hero

Surface coquille d'œuf chaude (`--color-bg: #faf9f6`). Derrière la vitrine vidéo (`.hero__bloom`), une bande pleine largeur (`100vw`) en **alvéoles** : nid d'abeilles orange très pâle (motif SVG en `data:` dans le CSS, 1 trait de 1px à 28 % d'opacité), sur `--color-brand-tint` avec un fondu orange clair au centre, effacée en haut et en bas par un masque. Immobile.

### Vitrine plein écran et vidéo motion

Lecteur maison (`.player`) dans un liseré blanc de 8px (`.player-frame`, filet `--color-border` et ombre douce), sans effet au défilement :
- **Vitrine large** : la vitrine (`.hero__showcase`) déborde du conteneur de texte pour occuper presque toute la largeur de la fenêtre, avec une scène de hauteur proche de l'écran (`clamp(32rem, calc(100dvh - 11.25rem), 46rem)`).
- **Barre de navigateur (`player__bar`)** : trois pastilles macOS (`#ff5c5f`, `#fac800`, `#34c759`), icônes de navigation, barre d'adresse arrondie (`.player__address`) affichant le cadenas, `app.gotcha.sn`, le titre de la démonstration et le compteur de scène en direct (`01 / 08`), suivis du bouton Pause/Lecture.
- **Scénario en 8 scènes** : raconte le test réel du 4 novembre : le dev demande le paiement Wave, l'agent suppose un bac à sable, il interroge Gotcha (`search_gotchas`), Gotcha trouve le piège avec sa source, l'agent corrige son code (ligne barrée en rouge, ligne corrigée en vert), il vérifie les pannes en direct (`get_service_status`), il prévient le dev, le piège est confirmé.

**Un seul monde, une caméra, des faisceaux.** Avec JavaScript, les 8 scènes sont des panneaux posés en serpentin (1 à 4, puis 5 à 8 au retour, 9rem d'écart) sur une toile à points (`.player__stage`). Une caméra (un `transform` sur `.player__scenes` et sur `.world-beams`, piloté par `app.js` avec l'API Web Animations) passe de l'un à l'autre en 1,1 s. À mi-chemin, elle recule (échelle × 0,6) pour montrer le trajet, puis elle avance. Les panneaux sont reliés par des **faisceaux** (`.wbeam`, SVG tracé par `app.js` d'un bord à l'autre, ancres rondes) : pointillé clair au repos, un rayon orange le parcourt pendant le passage de la caméra, puis il reste allumé (orange clair). Après la scène 8, la caméra recule en vue d'ensemble (2,2 s) : tout le chemin est allumé et les rayons le parcourent en cascade ; puis retour à la scène 1. La scène en cours est cerclée d'orange clair. Références : « White dot UI motion system » (rossaxbt, https://motionvideo.xyz/videos/rossaxbt-4e066d) et « 14-second UI morph loop » (flxrnc, https://motionvideo.xyz/videos/flxrnc-c083a6).

**Dans chaque scène.** Les animations attendent l'arrivée de la caméra (`.is-landed`). Les durées viennent de « Staggered UI card animation » (fleyta88, https://motionvideo.xyz/videos/fleyta88-1cd374) : blocs 280ms, titres 220ms, métadonnées 160ms, 60ms d'écart. Les textes marqués `data-type` sont tapés lettre par lettre (26ms par caractère), avec une copie entière pour les lecteurs d'écran. Un curseur envoie le message du dev. L'agent affiche trois points avant de répondre (`.typing`). Les échanges sont des faisceaux (`.sbeam`, SVG à `pathLength="100"`) : agent vers Gotcha (scène 3, l'onde part de Gotcha à l'arrivée), Gotcha vers l'agent avant la fiche (scène 4), appel vers l'état du service (scène 6), dev vers la fiche, en vert, avant « +1 confirmation » (scène 8). Le trait rouge de la ligne retirée se dessine. Éditeur et bulles clairs (DS-05) ; numéro de scène en texte mono orange foncé, sans pastille (DS-19). Une scène pas encore jouée n'affiche que son titre ; une scène jouée garde son état final. **Finitions.** Les entrées utilisent un ressort (`--spring`, fonction `linear()` avec léger dépassement, repli en `cubic-bezier` à rebond). Le numéro de scène tourne en se posant, le titre monte de derrière un masque (`.step__mask`), la fenêtre se pose sur le ressort et son badge glisse depuis la droite. Les lettres tapées montent de 0,35em en apparaissant (mots insécables, sauf dans le code). La caméra part en douceur, recule, puis se cale lentement ; pendant la lecture d'une scène elle avance de 1,8 % (« respiration »). Scène 4 : un reflet traverse la carte du piège. Scène 5 : un liseré vert pousse devant chaque ligne corrigée. Scène 6 : les barres du radar montent en cascade. Scène 8 : la coche tourne en se posant et le compteur roule de 14 à 15 (`.roll`, valeur lue par les lecteurs d'écran : 15). Vue d'ensemble : une vague parcourt les panneaux dans l'ordre du récit.

**Contrôles.** Pas de barre d'étapes : un petit bouton pause dans la barre de la fenêtre, qui fige aussi la caméra et les faisceaux. La vidéo démarre quand elle arrive à l'écran et s'arrête quand l'onglet est caché. Sans JavaScript : les scènes s'affichent en storyboard. Si l'utilisateur réduit les animations : pas de lecture automatique ni de mouvement de caméra, le bouton passe à la scène suivante.

### Sections de l'accueil sous le hero

Gabarit `components/landing.html`, dans cet ordre :

1. **Comment ça marche** : quatre cartes d'étapes (1/4 à 4/4) qui suivent le cycle de Gotcha (le dev tombe sur un piège, son agent le rédige sans rien de privé, un humain relit et publie, les agents suivants le retrouvent). Texte à gauche, illustration à droite à partir de 64rem. Cartes blanches pleines, filet `--color-border`, l'une sous l'autre (pas de rail ni de ligne qui les relie). Illustrations en « faisceaux » : scène de 440 unités qui se met à l'échelle comme une image (unités `cqw`, pleine largeur de la carte sous 64rem) ; éléments en cartes blanches à filet, état en icône + texte coloré, sans fond coloré ; rayons orange (vert pour ce qui est validé, rouge pour ce qui est refusé) qui parcourent les tracés au rythme commun de 2,4 s, et l'élément atteint réagit (`data-pulse`).
2. **Trois façons de s'en servir** : lire, brancher (adresse MCP et outils), partager. Chaque étape (`.way`) a deux colonnes à partir de 64rem (`1fr` / `1.15fr`, `min-height: 22rem`) : à gauche le numéro (`01` à `03`), le titre, l'explication, **le trait** (`.way__rule`, 2,5rem), une phrase de synthèse et le lien d'action ; à droite un écran (`.screen`, fenêtre claire avec barre d'adresse, jamais de fond noir) : la page de recherche avec de vrais pièges de `content/fiches/`, le terminal de l'agent (configuration MCP, appel `search_gotchas`, réponse, quatre outils), le formulaire de contribution « En attente de relecture ». L'écran se pose au défilement et ses lignes arrivent l'une après l'autre, sans boucle (DS-14). À partir de 64rem, menu d'étapes collant à gauche (`top: 112px`) : gris secondaire au repos ; l'étape lue (`aria-current="step"`, posé par `app.js`) passe en texte foncé et son alvéole glisse et s'allume devant le libellé.
3. **La preuve** : barres par service (sans web, avec le web, avec Gotcha) et trois compteurs, avec les chiffres du test du 4 novembre 2026 et leurs limites écrites sous le graphique. Aucun chiffre inventé ni arrondi.
4. **Ce que Gotcha couvre** : une ligne par fiche (`.svc`, dans une liste blanche `.svc-list`) groupée par type (`.svc-group`, libellé mono en capitales suivi d'un filet) : nom, pays et date de confirmation, état en direct (icône + texte), nombre de pièges, flèche. Toute la ligne mène à la fiche. Petit écran : le nom sur toute la largeur, état et pièges dessous. À droite (64rem et plus), les pannes en cours.
5. **Questions fréquentes** (`.faq`) : en-tête à gauche, collant à partir de 64rem ; à droite un accordéon natif `<details name="faq">` (une seule réponse ouverte, sans JavaScript). Numéros en compteur CSS (`01`), rond « + » qui tourne en « − » sur fond orange à l'ouverture, liseré orange de 2px qui pousse à gauche, réponse qui descend de 8px. Les réponses ne décrivent que ce que le site fait vraiment (page Données, outils MCP, filtre des secrets, durée des signalements).
6. **Bandeau final** (`.band`, le seul bandeau bordeaux) : appel à contribuer, bouton principal et lien « Signaler une panne », trois compteurs réels (fiches, pièges, pannes en cours).

**Pied de page** (`base.html`, toutes les pages) : logo et phrase de présentation, hébergement à Dakar avec le lien « Où sont vos données », deux colonnes de liens (Explorer, Participer), puis la licence des contributions sous un filet.

Séparateurs et libellés : au-dessus de chaque section après le hero, un trait de 1px (`--color-border`) coupé au centre par une alvéole vide (`.section-sep`). Le libellé de chaque en-tête de section (`.section-head .kicker`) commence par une alvéole orange de 10px, immobile.

Mouvement : lié au défilement, en CSS (`animation-timeline`) : titres, textes et illustrations qui montent en apparaissant, barres qui se remplissent.

| Effet | Classe | Détail |
| :--- | :--- | :--- |
| L'aperçu se pose | `.way__card` | Glisse de la droite (`translate(28px, 12px) rotate(2deg)` à rien) pendant que l'étape entre |
| Boucle 1/4 | `.art-line--error`, `.art-line--fix` | 4,8s : l'erreur pulse, la correction glisse (`translateY(6px)` à 0) et sa coche s'allume |
| Boucle 2/4 | `.art-field--secret code::after`, `.art-alert` | 4,8s : la clé est biffée d'un trait qui se dessine, le bandeau « Secret détecté » rebondit (`scale(0.96)` à 1) |
| Boucle 3/4 | `.art-checks li`, `.art-stamp` | 4,8s : les trois critères se cochent avec 180ms d'écart, puis le tampon tombe (`scale(1.18) rotate(-6deg)` à `scale(1) rotate(-3deg)`) |
| Boucle 4/4 | `.art-agent::after`, `.art-hub::after`, `.art-plus` | Une impulsion part de chaque agent vers Gotcha (2,4s), Gotcha émet une onde (`scale(1.6)`), la confirmation flotte de 6px |

Les compteurs montent jusqu'à leur valeur (`app.js`, valeur finale déjà écrite sans JavaScript). Les boucles des illustrations ne tournent que si `app.js` a posé `.stack--live` sur la liste, et seulement pour la carte à l'écran (`.is-playing`, `IntersectionObserver`) ; hors écran, elles sont en pause. Sans JavaScript, sans ce support du navigateur ou avec moins d'animations demandées : tout est visible et immobile.

### Mouvement du hero (accueil seulement)

Le hero est le seul endroit où le mouvement sert d'accroche. Cinq effets légers en CSS (`transform` et `opacity`), pas plus :

| Effet | Classe | Détail |
| :--- | :--- | :--- |
| Entrée en cascade | `.reveal`, `.reveal--1` à `.reveal--6` | Montée de 14px et apparition, 700ms, décalage de 100ms par élément |
| Mot qui tourne dans le titre | `.rotator` | 5 services, 2,5s chacun, montée puis sortie par le haut. Les lecteurs d'écran lisent la phrase complète |
| Logos des agents qui flottent | `.agent`, `.agent__tile` | Apparition en cascade, puis montée de 8px en 6 à 7,5s, aller-retour, inclinaison conservée |
| Alvéoles lumineuses ascendantes | `.hero__spark` | 8 alvéoles orange et bordeaux qui s'élèvent doucement depuis le relief inférieur |
| Vidéo motion | `.player`, `.player__stage`, `.scene`, `.wbeam`, `.sbeam` | 8 panneaux dans un même monde reliés par des faisceaux, caméra qui recule puis avance entre eux (1,1s) pendant qu'un rayon parcourt le faisceau, vue d'ensemble avant la boucle ; dans chaque scène, frappe, faisceaux et entrées en cascade (0 à 3,6s) |

Aucune de ces animations ne masque du contenu de façon durable : sans animation, tout est visible.

---

## 9. Rédaction

- **100 % français** dans l'interface : boutons, libellés, messages d'erreur, infobulles. Les termes techniques restent tels quels (`webhook`, `callback`), en police à chasse fixe.
- Phrases courtes, vocabulaire d'un débutant.
- Aucune formule marketing creuse : « révolutionnaire », « nouvelle génération », « sans effort », « seamless », « next-gen ».
- Aucun texte de remplissage : « Faites défiler pour découvrir », « Bientôt disponible ». Ce qui n'est pas fini est retiré.
- Dates : toujours via `date_fr` et `datetime_fr` (`app/web/labels.py`). Jamais de format écrit à la main dans un gabarit.
- Libellés d'état et de sévérité : toujours ceux de `app/web/labels.py`, pour un seul vocabulaire sur tout le site.

---

## 10. Interdictions

Chaque PR qui touche `app/web/` est relue contre cette liste.

| Code | Interdit | À la place |
| :--- | :--- | :--- |
| `DS-01` | Emoji dans un gabarit ou un texte d'interface | Icône Lucide |
| `DS-02` | `<div>` ou `<span>` cliquable | `<button>` ou `<a>` |
| `DS-03` | Autre bibliothèque d'icônes, police d'icônes | Lucide en SVG inline |
| `DS-04` | Police téléchargée (Google Fonts ou fichier), police sous licence non autorisée | Polices du système (section 3) |
| `DS-05` | Fond noir, thème sombre, plus d'un bandeau bordeaux par page | Fond blanc, cartes `#F6F6F6`, un bandeau `--color-maroon` au plus |
| `DS-06` | Couleur néon, halo lumineux, ombre colorée, dégradé violet ou cyan | Couleurs de la section 2. Dégradés admis : orange vers orange clair dans une illustration de données, et le panneau abricot derrière la vidéo du hero |
| `DS-07` | Texte orange vif `#FF6819` sur fond clair, deuxième couleur d'accent | `--color-primary-hover` pour le texte, l'orange seul comme accent |
| `DS-08` | Ambre décoratif | `warning` seulement pour ses quatre usages |
| `DS-09` | État signalé par la couleur seule | Icône + texte + couleur |
| `DS-10` | Libellé flottant ou placeholder seul | Libellé au-dessus du champ |
| `DS-11` | Rangée de trois cartes identiques | Mise en page hiérarchisée |
| `DS-12` | `100vh` | `100dvh` |
| `DS-13` | Animation de `top`, `left`, `width`, `height`, `margin` | `transform`, `opacity` |
| `DS-14` | Indicateur de chargement tournant, animation en boucle hors du hero et des illustrations de « Comment ça marche » (section 8) | Page rendue côté serveur |
| `DS-15` | Texte anglais dans l'interface (hors termes techniques) | Français |
| `DS-16` | Date formatée à la main | `date_fr`, `datetime_fr` |
| `DS-17` | Texte sous le contraste minimal (4,5 ; 3 pour bordures et icônes) | Jetons de la section 2 |
| `DS-18` | Italique à empattement hors des H1 et H2 | Linéale |
| `DS-19` | Badge, pastille, étiquette en pilule ou à fond coloré | État en texte : icône + libellé dans sa couleur |

---

## 11. Accessibilité

Cible : WCAG 2.2 niveau AA.

- Contrastes : voir les tableaux de la section 2.
- Zone cliquable de 44px au minimum.
- Contour de focus visible sur tout élément interactif (`:focus-visible`, 2px `--color-primary`).
- Lien d'évitement « Aller au contenu » en tête de page.
- Un seul `<h1>` par page, titres dans l'ordre.
- Chaque audio a sa transcription.
- La page reste utilisable à 200 % de zoom, sans défilement horizontal.

---

## 12. Poids et performance

| Élément | Budget |
| :--- | :--- |
| Feuille de style compressée (gzip) | 12 Ko au plus (5,4 Ko au 5 novembre 2026) |
| Page complète compressée (HTML, CSS, SVG), hors audio | 45 Ko au plus |
| JavaScript | Aucun requis. Seul `static/js/app.js` (définition du glossaire au toucher) existe, en amélioration progressive |

Les fichiers audio (environ 180 Ko pour 45 secondes) se chargent seulement à la lecture (`preload="none"`).

Mesure avant chaque PR qui touche le CSS :

```bash
gzip -c app/web/static/css/app.css | wc -c
```

---

## 13. Vérification

Le guide de style `/styleguide` (développement seulement, 404 en production) montre chaque composant de ce document. Un composant absent du guide de style n'est pas terminé.
