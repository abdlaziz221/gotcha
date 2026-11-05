// Amélioration progressive : le site marche entièrement sans JavaScript.
// Responsable : Loum. Pas de framework, pas de dépendance, quelques lignes seulement.

// Glossaire : au premier toucher d'un terme, afficher sa définition sous le lien ;
// au second, suivre le lien vers /glossaire.
document.addEventListener("click", (event) => {
  const link = event.target.closest('a[href^="/glossaire#"][title]');
  if (!link) return;
  const shown = link.nextElementSibling;
  if (shown && shown.classList.contains("term-popover")) return;
  event.preventDefault();
  const popover = document.createElement("span");
  popover.className = "term-popover";
  popover.setAttribute("role", "note");
  popover.textContent = link.getAttribute("title");
  link.after(popover);
});

// Bouton « Copier » : caché sans JavaScript (le champ reste sélectionnable),
// il copie la valeur du champ dont l'id est dans data-copy.
for (const button of document.querySelectorAll("button[data-copy]")) {
  const field = document.getElementById(button.dataset.copy);
  const label = button.querySelector("span");
  if (!field || !label || !navigator.clipboard) continue;
  button.hidden = false;
  button.addEventListener("click", async () => {
    try {
      await navigator.clipboard.writeText(field.value);
    } catch {
      field.select();
      return;
    }
    button.dataset.copied = "";
    label.textContent = "Copié";
    setTimeout(() => {
      delete button.dataset.copied;
      label.textContent = "Copier";
    }, 2000);
  });
}

// Vidéo motion du hero : les 8 scènes sont des panneaux posés dans un même monde (CSS),
// une caméra (transform du monde) passe de l'un à l'autre, puis recule en vue d'ensemble
// avant de boucler. Les animations d'une scène attendent que la caméra soit arrivée (.is-landed).
// Sans JavaScript, les scènes restent affichées en storyboard.
// Elle démarre quand elle arrive à l'écran, s'arrête quand l'onglet est caché,
// et ne démarre jamais seule si l'utilisateur réduit les animations.
const player = document.querySelector("[data-player]");
if (player) {
  const stage = player.querySelector(".player__stage");
  const world = player.querySelector(".player__scenes");
  const scenes = [...world.querySelectorAll(".scene")];
  const toggle = player.querySelector("[data-player-toggle]");
  const label = player.querySelector("[data-player-label]");
  const counter = player.querySelector("[data-player-counter]");
  const path = player.querySelector(".flow__path");
  const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const OVERVIEW = scenes.length;
  // Temps de lecture de chaque scène une fois la caméra arrivée (frappe et entrées comprises).
  const HOLD_MS = [2900, 2600, 3500, 3200, 4300, 3000, 3600, 2800];
  const MOVE_MS = 1100;
  const OVERVIEW_MS = 2200;
  const FRAME_SCALE = 0.94;
  const EASE = "cubic-bezier(0.65, 0, 0.35, 1)";

  let step = 0;
  let paused = true;
  let camera = { x: 0, y: 0, s: 1 };
  let move = null;

  // Frappe : chaque caractère devient un <span> (--i = rang) ; les lecteurs d'écran lisent une copie entière.
  player.querySelectorAll("[data-type]").forEach((element) => {
    const text = element.textContent;
    const copy = document.createElement("span");
    copy.className = "visually-hidden";
    copy.textContent = text;
    const typed = document.createElement("span");
    typed.className = "type";
    typed.setAttribute("aria-hidden", "true");
    [...text].forEach((character, i) => {
      const char = document.createElement("span");
      char.className = "type__char";
      char.style.setProperty("--i", i);
      char.textContent = character;
      typed.append(char);
    });
    element.replaceChildren(copy, typed);
  });

  // --- Caméra ---------------------------------------------------------------
  const css = (c) => `translate(${c.x}px, ${c.y}px) scale(${c.s})`;

  const frame = (index) => {
    const W = stage.clientWidth;
    const H = stage.clientHeight;
    if (index === OVERVIEW) {
      const s = Math.min(W / world.offsetWidth, H / world.offsetHeight) * 0.9;
      return { x: (W - world.offsetWidth * s) / 2, y: (H - world.offsetHeight * s) / 2, s };
    }
    const panel = scenes[index];
    const s = FRAME_SCALE;
    return {
      x: W / 2 - s * (panel.offsetLeft + panel.offsetWidth / 2),
      y: H / 2 - s * (panel.offsetTop + panel.offsetHeight / 2),
      s,
    };
  };

  // Entre deux scènes, la caméra recule à mi-chemin pour montrer le trajet, puis avance.
  const midway = (from, to) => {
    const W = stage.clientWidth;
    const H = stage.clientHeight;
    const cx = ((W / 2 - from.x) / from.s + (W / 2 - to.x) / to.s) / 2;
    const cy = ((H / 2 - from.y) / from.s + (H / 2 - to.y) / to.s) / 2;
    const s = Math.min(from.s, to.s) * 0.6;
    return { x: W / 2 - s * cx, y: H / 2 - s * cy, s };
  };

  const flyTo = (index, duration) => {
    const from = camera;
    const to = frame(index);
    camera = to;
    if (move) move.cancel();
    move = null;
    world.style.transform = css(to);
    if (!duration) return;
    const keyframes = [{ transform: css(from) }];
    if (index !== OVERVIEW && from.s === to.s) keyframes.push({ transform: css(midway(from, to)), offset: 0.5 });
    keyframes.push({ transform: css(to) });
    move = world.animate(keyframes, { duration, easing: EASE });
    if (paused || document.hidden) move.pause();
  };

  const layout = () => {
    world.style.setProperty("--stage-w", `${stage.clientWidth}px`);
    world.style.setProperty("--stage-h", `${stage.clientHeight}px`);
    if (path) path.style.setProperty("--path", `${path.offsetWidth}px`);
  };

  // --- Minuterie qu'on peut mettre en pause -------------------------------
  let timer = null;
  let action = null;
  let remaining = 0;
  let due = 0;

  const arm = () => {
    clearTimeout(timer);
    if (!action || paused || document.hidden) return;
    due = performance.now() + remaining;
    timer = setTimeout(() => {
      const run = action;
      action = null;
      run();
    }, remaining);
  };

  const disarm = () => {
    if (action) remaining = Math.max(0, due - performance.now());
    clearTimeout(timer);
  };

  const later = (run, ms) => {
    clearTimeout(timer);
    action = run;
    remaining = ms;
    due = performance.now() + ms;
    arm();
  };

  // --- Déroulé ----------------------------------------------------------------
  const land = () => {
    if (step !== OVERVIEW) scenes[step].classList.add("is-landed");
    if (!reduced) later(next, step === OVERVIEW ? OVERVIEW_MS : HOLD_MS[step]);
  };

  const go = (index, instant = false) => {
    step = index;
    world.classList.toggle("is-overview", index === OVERVIEW);
    if (counter) {
      const total = String(OVERVIEW).padStart(2, "0");
      counter.textContent = index === OVERVIEW ? `${total} / ${total}` : `${String(index + 1).padStart(2, "0")} / ${total}`;
    }
    if (index === 0) scenes.forEach((scene) => scene.classList.remove("is-done"));
    scenes.forEach((scene, i) => {
      scene.classList.remove("is-landed");
      scene.classList.toggle("is-active", i === index);
    });
    const duration = instant || reduced ? 0 : MOVE_MS;
    flyTo(index, duration);
    if (duration) later(land, duration);
    else land();
  };

  function next() {
    if (step !== OVERVIEW) scenes[step].classList.add("is-done");
    go((step + 1) % (OVERVIEW + 1));
  }

  const resume = () => {
    if (paused || document.hidden) {
      disarm();
      if (move && move.playState === "running") move.pause();
    } else {
      if (move && move.playState === "paused") move.play();
      arm();
    }
  };

  const setPaused = (value) => {
    paused = value;
    if (!paused) player.classList.add("has-started");
    player.classList.toggle("is-paused", paused);
    label.textContent = paused ? "Lire la vidéo" : "Mettre en pause";
    resume();
  };

  const showcase = document.querySelector("[data-showcase]");
  const playerFrame = document.querySelector("[data-player-frame]");
  let scaleTicking = false;
  const updateShowcaseScale = () => {
    scaleTicking = false;
    if (!showcase || !playerFrame || reduced) return;
    const rect = showcase.getBoundingClientRect();
    const vh = window.innerHeight || 900;
    const start = vh * 0.82;
    const end = vh * 0.14;
    const raw = (start - rect.top) / Math.max(1, start - end);
    const t = Math.max(0, Math.min(1, raw));
    const eased = 1 - (1 - t) ** 2.2;
    const scale = 0.82 + 0.18 * eased;
    const y = (1 - eased) * 20;
    playerFrame.style.setProperty("--player-scale", scale.toFixed(4));
    playerFrame.style.setProperty("--player-y", `${y.toFixed(1)}px`);
  };
  const requestShowcaseScale = () => {
    if (scaleTicking || reduced) return;
    scaleTicking = true;
    requestAnimationFrame(updateShowcaseScale);
  };

  player.classList.add("player--live", "is-paused");
  layout();
  updateShowcaseScale();
  go(0, true);
  if (!reduced) {
    // go(0, true) pose la scène sans attendre : on garde ses animations pour le lancement.
    scenes[0].classList.remove("is-landed");
    later(land, 0);
    window.addEventListener("scroll", requestShowcaseScale, { passive: true });
  }

  window.addEventListener("resize", () => {
    layout();
    updateShowcaseScale();
    if (move) move.cancel();
    move = null;
    camera = frame(step);
    world.style.transform = css(camera);
  });

  toggle.hidden = false;
  if (reduced) {
    // Pas de lecture automatique : le bouton passe à la scène suivante, sans mouvement.
    label.textContent = "Scène suivante";
    toggle.addEventListener("click", next);
  } else {
    toggle.addEventListener("click", () => setPaused(!paused));
    document.addEventListener("visibilitychange", resume);
    if ("IntersectionObserver" in window) {
      const observer = new IntersectionObserver((entries) => {
        if (entries.some((entry) => entry.isIntersecting)) {
          observer.disconnect();
          setPaused(false);
        }
      }, { threshold: 0.3 });
      observer.observe(player);
    } else {
      setPaused(false);
    }
  }
}

// Accueil : compteurs qui montent jusqu'à leur valeur quand ils arrivent à l'écran.
// Sans JavaScript (ou avec moins d'animations demandées), la valeur finale est déjà écrite.
const counters = document.querySelectorAll("[data-count]");
if (counters.length && "IntersectionObserver" in window && !window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
  const countUp = (element) => {
    const target = Number(element.dataset.count);
    const start = performance.now();
    const tick = (now) => {
      const progress = Math.min(1, (now - start) / 1200);
      const eased = 1 - (1 - progress) ** 3;
      element.textContent = String(Math.round(target * eased));
      if (progress < 1) requestAnimationFrame(tick);
    };
    requestAnimationFrame(tick);
  };
  const counterObserver = new IntersectionObserver((entries) => {
    for (const entry of entries) {
      if (!entry.isIntersecting) continue;
      counterObserver.unobserve(entry.target);
      countUp(entry.target);
    }
  }, { threshold: 0.6 });
  counters.forEach((element) => {
    element.textContent = "0";
    counterObserver.observe(element);
  });
}

// Accueil : le menu des trois usages suit l'étape lue à l'écran.
const wayLinks = [...document.querySelectorAll("[data-way]")];
if (wayLinks.length && "IntersectionObserver" in window) {
  const byId = new Map(wayLinks.map((link) => [link.hash.slice(1), link]));
  const wayObserver = new IntersectionObserver((entries) => {
    for (const entry of entries) {
      if (!entry.isIntersecting) continue;
      wayLinks.forEach((link) => link.removeAttribute("aria-current"));
      byId.get(entry.target.id)?.setAttribute("aria-current", "step");
    }
  }, { rootMargin: "-40% 0px -55% 0px" });
  byId.forEach((_, id) => {
    const step = document.getElementById(id);
    if (step) wayObserver.observe(step);
  });
}

// Accueil, « Comment ça marche » : moteur Animated Beam & ressorts (Web Animations API,
// le moteur natif utilisé par Framer Motion), actif uniquement quand la carte est à l'écran.
const stack = document.querySelector("[data-stack]");
if (stack && "IntersectionObserver" in window && !window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
  stack.classList.add("stack--live");
  const cardAnimations = new Map();

  for (const card of stack.querySelectorAll(".stack__card")) {
    const anims = [];
    // Faisceaux SVG (Animated Beams) : mesure exacte de chaque courbe Bezier / coude.
    for (const ray of card.querySelectorAll("[data-beam-ray]")) {
      if (typeof ray.getTotalLength !== "function" || typeof ray.animate !== "function") continue;
      const length = Math.ceil(ray.getTotalLength()) || 220;
      const beamSize = Math.max(36, Math.round(length * 0.24));
      const delay = Number(ray.dataset.delay || 0);
      ray.setAttribute("stroke-dasharray", `${beamSize} ${length + beamSize}`);
      const anim = ray.animate(
        [
          { strokeDashoffset: length + beamSize, opacity: 0 },
          { strokeDashoffset: Math.round(length * 0.78), opacity: 1, offset: 0.16 },
          { strokeDashoffset: 0, opacity: 1, offset: 0.84 },
          { strokeDashoffset: -beamSize, opacity: 0 },
        ],
        {
          duration: 2400,
          delay,
          iterations: Infinity,
          easing: "cubic-bezier(0.22, 1, 0.36, 1)",
        }
      );
      anim.pause();
      anims.push(anim);
    }

    // Tuiles flottantes avec physique de ressort (spring keyframes type Framer Motion).
    card.querySelectorAll("[data-spring-tile]").forEach((tile, index) => {
      if (typeof tile.animate !== "function") return;
      const tilt = index % 2 === 0 ? 2.5 : -2.5;
      const anim = tile.animate(
        [
          { transform: "translate(-50%, -50%) translate3d(0, 0px, 0) rotate(0deg) scale(1)" },
          { transform: `translate(-50%, -50%) translate3d(0, -6px, 0) rotate(${tilt}deg) scale(1.03)`, offset: 0.45 },
          { transform: `translate(-50%, -50%) translate3d(0, -4px, 0) rotate(${tilt * 0.5}deg) scale(1.01)`, offset: 0.65 },
          { transform: "translate(-50%, -50%) translate3d(0, 0px, 0) rotate(0deg) scale(1)" },
        ],
        {
          duration: 3200 + (index % 3) * 350,
          delay: index * 220,
          iterations: Infinity,
          easing: "cubic-bezier(0.34, 1.56, 0.64, 1)",
        }
      );
      anim.pause();
      anims.push(anim);
    });

    cardAnimations.set(card, anims);
  }

  const playing = new IntersectionObserver((entries) => {
    for (const entry of entries) {
      entry.target.classList.toggle("is-playing", entry.isIntersecting);
      const anims = cardAnimations.get(entry.target) || [];
      for (const anim of anims) {
        if (entry.isIntersecting) anim.play();
        else anim.pause();
      }
    }
  }, { threshold: 0.25 });
  stack.querySelectorAll(".stack__card").forEach((card) => playing.observe(card));
}
