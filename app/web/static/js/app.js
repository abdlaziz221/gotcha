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
  const dock = player.querySelector("[data-player-dock]");
  const stepButtons = [...player.querySelectorAll("[data-player-step]")];
  const beams = player.querySelector(".world-beams");
  const SVG = "http://www.w3.org/2000/svg";
  const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const OVERVIEW = scenes.length;
  const HOLD_MS = [2900, 2600, 3400, 3200, 3800, 3100, 3400, 2800];
  const MOVE_MS = 1150;
  const OVERVIEW_MS = 2200;
  const FRAME_SCALE = 0.94;
  const EASE = "cubic-bezier(0.65, 0, 0.35, 1)";
  const SETTLE = "cubic-bezier(0.22, 1, 0.36, 1)";
  const BREATH = 1.018;

  let step = 0;
  let paused = true;
  let camera = { x: 0, y: 0, s: 1 };

  // Titre de scène : le texte après le numéro passe dans un masque (il monte en roulant).
  scenes.forEach((scene) => {
    const title = scene.querySelector(".scene__step");
    if (!title) return;
    const mask = document.createElement("span");
    mask.className = "step__mask";
    const text = document.createElement("span");
    text.className = "step__text";
    [...title.childNodes].slice(1).forEach((node) => text.append(node));
    text.textContent = text.textContent.trim();
    mask.append(text);
    title.append(mask);
  });

  // Frappe : texte [data-type] découpé en mots insécables puis en lettres (Web Animations, CSP).
  const sceneTyped = scenes.map((scene) => {
    const groups = [];
    scene.querySelectorAll("[data-type]").forEach((element, groupIndex) => {
      const text = element.textContent;
      const copy = document.createElement("span");
      copy.className = "visually-hidden";
      copy.textContent = text;
      const typed = document.createElement("span");
      typed.className = "type";
      typed.setAttribute("aria-hidden", "true");
      const chars = [];
      for (const token of text.split(/(\s+)/)) {
        if (!token) continue;
        const holder = /^\s+$/.test(token) ? typed : document.createElement("span");
        if (holder !== typed) {
          holder.className = "type__word";
          typed.append(holder);
        }
        for (const character of token) {
          const char = document.createElement("span");
          char.className = "type__char";
          char.textContent = character;
          holder.append(char);
          chars.push(char);
        }
      }
      element.replaceChildren(copy, typed);
      groups.push({ chars, baseDelay: groupIndex === 0 ? 180 : 850 });
    });
    return groups;
  });

  const playTyping = (index) => {
    if (reduced || index === OVERVIEW || typeof Element.prototype.animate !== "function") return;
    for (const { chars, baseDelay } of sceneTyped[index] || []) {
      chars.forEach((char, i) => {
        if (index === 0 && i < 21) return;
        const n = index === 0 ? i - 21 : i;
        char.animate(
          [{ opacity: 0, transform: "translateY(0.35em)" }, { opacity: 1, transform: "none" }],
          { duration: 220, delay: baseDelay + n * 18, easing: "cubic-bezier(0.2, 0.8, 0.2, 1)", fill: "both" }
        );
      });
    }
  };

  // --- Caméra (Web Animations API avec fill: "forwards" pour respecter style-src 'self') ---
  const css = (c) => `translate(${c.x}px, ${c.y}px) scale(${c.s})`;

  const frame = (index) => {
    const W = stage.clientWidth;
    const H = stage.clientHeight;
    if (index === OVERVIEW) {
      const s = Math.min(W / world.offsetWidth, H / world.offsetHeight) * 0.88;
      return { x: (W - world.offsetWidth * s) / 2, y: (H - world.offsetHeight * s) / 2 - 12, s };
    }
    const panel = scenes[index];
    const s = FRAME_SCALE;
    return {
      x: W / 2 - s * (panel.offsetLeft + panel.offsetWidth / 2),
      y: H / 2 - s * (panel.offsetTop + panel.offsetHeight / 2),
      s,
    };
  };

  // Caméra qui respire : travelling avant de 1,8 % pendant la scène ; le trajet suivant en part.
  const breathe = (duration) => {
    if (reduced || typeof Element.prototype.animate !== "function") return;
    const W = stage.clientWidth;
    const H = stage.clientHeight;
    const from = camera;
    const to = {
      s: from.s * BREATH,
      x: W / 2 - BREATH * (W / 2 - from.x),
      y: H / 2 - BREATH * (H / 2 - from.y),
    };
    camera = to;
    moves.forEach((anim) => anim.cancel());
    moves = layers.map((layer) => layer.animate(
      [{ transform: css(from) }, { transform: css(to) }],
      { duration, easing: "cubic-bezier(0.37, 0, 0.63, 1)", fill: "forwards" }
    ));
    if (paused || document.hidden) moves.forEach((anim) => anim.pause());
  };

  const midway = (from, to) => {
    const W = stage.clientWidth;
    const H = stage.clientHeight;
    const cx = ((W / 2 - from.x) / from.s + (W / 2 - to.x) / to.s) / 2;
    const cy = ((H / 2 - from.y) / from.s + (H / 2 - to.y) / to.s) / 2;
    const s = Math.min(from.s, to.s) * 0.62;
    return { x: W / 2 - s * cx, y: H / 2 - s * cy, s };
  };

  const layers = beams ? [world, beams] : [world];
  let moves = [];
  const flyTo = (index, duration) => {
    const from = camera;
    const to = frame(index);
    camera = to;
    moves.forEach((anim) => anim.cancel());
    moves = [];
    if (typeof Element.prototype.animate !== "function") return;
    if (!duration) {
      moves = layers.map((layer) => layer.animate([{ transform: css(to) }, { transform: css(to) }], { duration: 1, fill: "forwards" }));
      return;
    }
    // Départ et recul en douceur, arrivée qui se cale lentement.
    const keyframes = [{ transform: css(from), easing: EASE }];
    if (index !== OVERVIEW && Math.abs(from.s - to.s) < 0.08) {
      keyframes.push({ transform: css(midway(from, to)), offset: 0.45, easing: SETTLE });
    } else {
      keyframes[0].easing = SETTLE;
    }
    keyframes.push({ transform: css(to) });
    moves = layers.map((layer) => layer.animate(keyframes, { duration, fill: "forwards" }));
    if (paused || document.hidden) moves.forEach((anim) => anim.pause());
  };

  // Faisceaux : un tracé par passage d'une scène à la suivante (parcours en serpentin).
  const links = [];
  const drawBeams = () => {
    if (!beams) return;
    beams.setAttribute("width", String(world.offsetWidth));
    beams.setAttribute("height", String(world.offsetHeight));
    beams.setAttribute("viewBox", `0 0 ${world.offsetWidth} ${world.offsetHeight}`);
    beams.replaceChildren();
    links.length = 0;
    for (let i = 0; i < scenes.length - 1; i += 1) {
      const a = scenes[i];
      const b = scenes[i + 1];
      let d;
      if (Math.abs(a.offsetTop - b.offsetTop) < 2) {
        const y = a.offsetTop + a.offsetHeight / 2;
        const right = b.offsetLeft > a.offsetLeft;
        const x1 = right ? a.offsetLeft + a.offsetWidth : a.offsetLeft;
        const x2 = right ? b.offsetLeft : b.offsetLeft + b.offsetWidth;
        d = `M ${x1} ${y} H ${x2}`;
      } else {
        const x = a.offsetLeft + a.offsetWidth / 2;
        d = `M ${x} ${a.offsetTop + a.offsetHeight} V ${b.offsetTop}`;
      }
      const group = document.createElementNS(SVG, "g");
      group.setAttribute("class", "wbeam");
      for (const name of ["wbeam__track", "wbeam__ray"]) {
        const line = document.createElementNS(SVG, "path");
        line.setAttribute("class", name);
        line.setAttribute("d", d);
        line.setAttribute("pathLength", "100");
        group.append(line);
      }
      const [, x1, y1] = d.match(/M ([\d.]+) ([\d.]+)/);
      const end = d.match(/([HV]) ([\d.]+)$/);
      const x2 = end[1] === "H" ? end[2] : x1;
      const y2 = end[1] === "V" ? end[2] : y1;
      for (const [cx, cy] of [[x1, y1], [x2, y2]]) {
        const dot = document.createElementNS(SVG, "circle");
        dot.setAttribute("class", "wbeam__dot");
        dot.setAttribute("cx", cx);
        dot.setAttribute("cy", cy);
        dot.setAttribute("r", "12");
        group.append(dot);
      }
      beams.append(group);
      links.push(group);
    }
  };

  const runBeam = (from, to) => {
    links.forEach((link, i) => {
      link.classList.toggle("is-running", to === from + 1 && i === from);
      link.classList.toggle("is-done", to !== OVERVIEW && to !== 0 && i < to);
    });
  };

  const layout = () => {
    drawBeams();
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
    if (step !== OVERVIEW) {
      scenes[step].classList.add("is-landed");
      playTyping(step);
    }
    if (!reduced) {
      const hold = step === OVERVIEW ? OVERVIEW_MS : HOLD_MS[step];
      breathe(hold);
      later(next, hold);
    }
  };

  const go = (index, instant = false) => {
    runBeam(step, index);
    step = index;
    world.classList.toggle("is-overview", index === OVERVIEW);
    stage.classList.toggle("is-overview", index === OVERVIEW);
    if (counter) {
      const total = String(OVERVIEW).padStart(2, "0");
      counter.textContent = index === OVERVIEW ? `${total} / ${total}` : `${String(index + 1).padStart(2, "0")} / ${total}`;
    }
    stepButtons.forEach((btn) => {
      btn.classList.toggle("is-current", Number(btn.dataset.playerStep) === index);
    });
    if (index === 0) scenes.forEach((scene) => scene.classList.remove("is-done"));
    scenes.forEach((scene, i) => {
      scene.classList.remove("is-landed");
      scene.classList.toggle("is-active", i === index);
      if (index !== OVERVIEW && i < index) scene.classList.add("is-done");
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
      moves.forEach((anim) => { if (anim.playState === "running") anim.pause(); });
    } else {
      moves.forEach((anim) => { if (anim.playState === "paused") anim.play(); });
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
  let frameAnim = null;
  const updateShowcaseScale = () => {
    scaleTicking = false;
    if (!showcase || !playerFrame || reduced || typeof Element.prototype.animate !== "function") return;
    const rect = showcase.getBoundingClientRect();
    const vh = window.innerHeight || 900;
    const start = vh * 0.82;
    const end = vh * 0.14;
    const raw = (start - rect.top) / Math.max(1, start - end);
    const t = Math.max(0, Math.min(1, raw));
    const eased = 1 - (1 - t) ** 2.2;
    const scale = 0.86 + 0.14 * eased;
    const y = (1 - eased) * 18;
    const transform = `translate3d(0, ${y.toFixed(1)}px, 0) scale(${scale.toFixed(4)})`;
    if (frameAnim) frameAnim.cancel();
    frameAnim = playerFrame.animate([{ transform }, { transform }], { duration: 1, fill: "forwards" });
  };
  const requestShowcaseScale = () => {
    if (scaleTicking || reduced) return;
    scaleTicking = true;
    requestAnimationFrame(updateShowcaseScale);
  };

  player.classList.add("player--live", "is-paused");
  if (dock) {
    dock.hidden = false;
    stepButtons.forEach((btn) => {
      btn.addEventListener("click", () => {
        player.classList.add("has-started");
        go(Number(btn.dataset.playerStep));
      });
    });
  }
  layout();
  updateShowcaseScale();
  go(0, true);
  if (!reduced) {
    scenes[0].classList.remove("is-landed");
    later(land, 0);
    window.addEventListener("scroll", requestShowcaseScale, { passive: true });
  }

  window.addEventListener("resize", () => {
    layout();
    updateShowcaseScale();
    flyTo(step, 0);
  });

  toggle.hidden = false;
  if (reduced) {
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

// Accueil, « Comment ça marche » : rayons, ressorts et pulsations (Web Animations API).
// Tout suit le même rythme de 2,4 s pour rester synchronisé ; une carte ne joue que si elle est à l'écran.
const stack = document.querySelector("[data-stack]");
if (stack && "IntersectionObserver" in window && typeof Element.prototype.animate === "function"
    && !window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
  stack.classList.add("stack--live");
  const BEAT = 2400;
  const cardAnimations = new Map();

  for (const card of stack.querySelectorAll(".stack__card")) {
    const anims = [];
    const add = (anim) => {
      anim.pause();
      anims.push(anim);
    };

    // Rayon : un trait de longueur fixe qui parcourt tout le tracé, mesuré une fois.
    for (const ray of card.querySelectorAll("[data-beam-ray]")) {
      if (typeof ray.getTotalLength !== "function") continue;
      const length = Math.ceil(ray.getTotalLength()) || 200;
      const dash = Math.max(28, Math.round(length * 0.3));
      ray.setAttribute("stroke-dasharray", `${dash} ${length + dash}`);
      // La tête du trait arrive au bout à 84 % du rythme (moment des pulsations), la queue sort ensuite.
      // Easing par segment : l'easing global décalerait ces instants.
      add(ray.animate(
        [
          { strokeDashoffset: dash, opacity: 1, easing: "cubic-bezier(0.45, 0, 0.25, 1)" },
          { strokeDashoffset: dash - length, opacity: 1, offset: 0.84, easing: "linear" },
          { strokeDashoffset: -length, opacity: 1, offset: 0.94 },
          { strokeDashoffset: -length, opacity: 0 },
        ],
        { duration: BEAT, delay: Number(ray.dataset.delay || 0), iterations: Infinity }
      ));
    }

    // Pulsation : l'élément réagit quand un rayon part de lui ou l'atteint (data-at, part du rythme).
    for (const el of card.querySelectorAll("[data-pulse]")) {
      const at = Number(el.dataset.at || 0.84);
      add(el.animate(
        [
          { transform: "scale(1)", offset: 0 },
          { transform: "scale(1)", offset: Math.max(0, at - 0.02), easing: "cubic-bezier(0.34, 1.56, 0.64, 1)" },
          { transform: "scale(1.08)", offset: Math.min(1, at + 0.05), easing: "ease-out" },
          { transform: "scale(1)", offset: Math.min(1, at + 0.16) },
          { transform: "scale(1)", offset: 1 },
        ],
        { duration: BEAT, delay: Number(el.dataset.delay || 0), iterations: Infinity }
      ));
    }

    // Ressort : légère flottaison décalée d'un élément à l'autre.
    card.querySelectorAll("[data-spring-tile]").forEach((tile, index) => {
      const tilt = index % 2 === 0 ? 2 : -2;
      add(tile.animate(
        [
          { transform: "translateY(0) rotate(0deg)" },
          { transform: `translateY(-0.35em) rotate(${tilt}deg)`, offset: 0.45 },
          { transform: `translateY(-0.2em) rotate(${tilt / 2}deg)`, offset: 0.65 },
          { transform: "translateY(0) rotate(0deg)" },
        ],
        { duration: 3200 + (index % 3) * 400, delay: index * 240, iterations: Infinity, easing: "ease-in-out" }
      ));
    });

    cardAnimations.set(card, anims);
  }

  const playing = new IntersectionObserver((entries) => {
    for (const entry of entries) {
      entry.target.classList.toggle("is-playing", entry.isIntersecting);
      for (const anim of cardAnimations.get(entry.target) || []) {
        if (entry.isIntersecting) anim.play();
        else anim.pause();
      }
    }
  }, { threshold: 0.25 });
  stack.querySelectorAll(".stack__card").forEach((card) => playing.observe(card));
}
