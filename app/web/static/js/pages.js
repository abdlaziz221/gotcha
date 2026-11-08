// Pages intérieures : amélioration progressive, chargée après app.js, jamais sur l'accueil.
// Responsable : Loum. Sans JavaScript, chaque page reste complète : les éléments ajoutés ici
// sont cachés (attribut hidden) dans le HTML et révélés seulement si le script tourne.

const $$ = (selector, root = document) => Array.from(root.querySelectorAll(selector));

// Petit message de confirmation lu par les lecteurs d'écran.
const live = document.createElement("p");
live.className = "visually-hidden";
live.setAttribute("role", "status");
document.body.append(live);
const say = (text) => {
  live.textContent = "";
  setTimeout(() => { live.textContent = text; }, 50);
};

// --- Copier : un texte (data-copy-text) ou le lien d'une ancre (data-copy-link) ----------------
async function copy(text, button) {
  try {
    await navigator.clipboard.writeText(text);
  } catch {
    return;
  }
  button.dataset.copied = "";
  say("Copié");
  setTimeout(() => { delete button.dataset.copied; }, 1600);
}

if (navigator.clipboard) {
  for (const button of $$("[data-copy-text], [data-copy-link]")) {
    button.hidden = false;
    button.addEventListener("click", () => {
      const text = button.dataset.copyText
        ?? new URL(button.dataset.copyLink, location.href).href;
      copy(text, button);
    });
  }
  // Un bouton « Copier » sur chaque bloc de code des fiches.
  for (const pre of $$(".prose-ui pre")) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "code-copy";
    button.textContent = "Copier";
    const source = pre.querySelector("code") || pre;
    button.addEventListener("click", () => copy(source.innerText, button));
    pre.append(button);
  }
}

// --- Fiche : filtres des pièges par sévérité et par environnement ------------------------------
const filters = document.querySelector("[data-filters]");
if (filters) {
  filters.hidden = false;
  const chosen = { severity: "", env: "" };
  const cards = $$(".gotcha[data-severity]");
  const count = document.querySelector("[data-filter-count]");
  const empty = document.querySelector("[data-filter-empty]");
  const apply = () => {
    let shown = 0;
    for (const card of cards) {
      const ok = (!chosen.severity || card.dataset.severity === chosen.severity)
        && (!chosen.env || card.dataset.env.split("|").includes(chosen.env));
      card.hidden = !ok;
      shown += ok ? 1 : 0;
    }
    if (count) count.textContent = shown === cards.length ? `${shown}` : `${shown} sur ${cards.length}`;
    if (empty) empty.hidden = shown > 0;
  };
  filters.addEventListener("click", (event) => {
    const button = event.target.closest("button[data-filter]");
    if (!button) return;
    chosen[button.dataset.filter] = button.dataset.value;
    for (const other of $$(`button[data-filter="${button.dataset.filter}"]`, filters)) {
      other.setAttribute("aria-pressed", String(other === button));
    }
    apply();
  });
}

// --- Fiche : « Ça marche encore » sans quitter la page -----------------------------------------
// Le serveur répond par une redirection vers la fiche : on y relit le piège mis à jour et on le
// remplace sur place. En cas d'erreur, on laisse le formulaire partir normalement.
for (const form of $$("form[data-inplace]")) {
  form.addEventListener("submit", async (event) => {
    if (!form.reportValidity()) return;
    event.preventDefault();
    const button = form.querySelector('button[type="submit"]');
    if (button) button.disabled = true;
    try {
      const response = await fetch(form.action, { method: "POST", body: new FormData(form) });
      const html = await response.text();
      const page = new DOMParser().parseFromString(html, "text/html");
      if (!response.ok) {
        const reason = page.querySelector(".auth__desc, .flash")?.textContent?.trim();
        throw new Error(reason || "La confirmation n'a pas pu être enregistrée.");
      }
      // Ne dire « enregistrée » que si le serveur est bien revenu sur la fiche avec ?ok=confirmation
      // (une session expirée mène à /connexion en 200). Sinon, envoi normal du formulaire.
      const confirmed = new URL(response.url).searchParams.get("ok") === "confirmation";
      const card = form.closest(".gotcha");
      const fresh = card ? page.getElementById(card.id) : null;
      if (!confirmed || (card && !fresh)) {
        form.submit();
        return;
      }
      if (card && fresh) {
        const note = document.createElement("p");
        note.className = "gotcha__done";
        note.setAttribute("role", "status");
        note.textContent = "Merci : votre confirmation est enregistrée.";
        fresh.querySelector(".gotcha__foot")?.prepend(note);
        card.replaceWith(fresh);
      } else {
        form.replaceChildren(Object.assign(document.createElement("p"), {
          className: "gotcha__done",
          textContent: "Merci : votre confirmation est enregistrée.",
        }));
      }
      say("Confirmation enregistrée");
    } catch (error) {
      if (button) button.disabled = false;
      let message = form.querySelector(".field__error");
      if (!message) {
        message = document.createElement("p");
        message.className = "field__error";
        message.setAttribute("role", "alert");
        form.append(message);
      }
      message.textContent = error.message;
    }
  });
}

// --- Recherche : relancer à chaque filtre, surligner le terme cherché ---------------------------
const searchForm = document.querySelector("form[data-autosubmit]");
if (searchForm) {
  for (const select of $$("select", searchForm)) {
    select.addEventListener("change", () => searchForm.requestSubmit());
  }
}

const highlight = document.querySelector("[data-highlight]");
const words = (highlight?.dataset.highlight || "").trim().split(/\s+/).filter((w) => w.length > 1);
if (highlight && words.length) {
  const escape = (w) => w.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  const pattern = new RegExp(`(${words.map(escape).join("|")})`, "gi");
  for (const target of $$(".row__title, .row__text", highlight)) {
    const walker = document.createTreeWalker(target, NodeFilter.SHOW_TEXT);
    const nodes = [];
    while (walker.nextNode()) nodes.push(walker.currentNode);
    for (const node of nodes) {
      const parts = node.textContent.split(pattern);
      if (parts.length < 2) continue;
      node.replaceWith(...parts.map((part, i) => {
        if (i % 2 === 0) return document.createTextNode(part);
        const mark = document.createElement("mark");
        mark.textContent = part;
        return mark;
      }));
    }
  }
}

// --- Formulaires : compteur de caractères sous chaque zone de texte limitée -------------------
for (const area of $$(".box textarea[maxlength]")) {
  const max = Number(area.maxLength);
  const counter = document.createElement("p");
  counter.className = "field__count";
  counter.setAttribute("aria-live", "polite");
  const update = () => {
    counter.textContent = `${area.value.length} / ${max}`;
    counter.dataset.near = String(area.value.length > max * 0.9);
  };
  area.addEventListener("input", update);
  update();
  area.closest(".field")?.append(counter);
}

// --- Contribuer : barre Markdown, aperçu, alerte de secret en direct ---------------------------
// Les motifs reprennent ceux de app/security/secrets.py ; le serveur refait la vérification.
const SECRETS = [
  ["une clé privée", /-----BEGIN (?:[A-Z]+ )*PRIVATE KEY-----/],
  ["un jeton JWT", /\beyJ[A-Za-z0-9_-]{8,}\.eyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}/],
  ["une clé AWS", /\b(?:AKIA|ASIA)[0-9A-Z]{16}\b/],
  ["un jeton GitHub", /\bgh[pousr]_[A-Za-z0-9]{36,}\b/],
  ["une clé secrète Flutterwave", /\bFLWSECK(?:_TEST)?-[A-Za-z0-9]{20,}/],
  ["une clé secrète Paystack ou Stripe", /\b(?:sk|rk)_(?:live|test)_[A-Za-z0-9]{16,}/],
  ["une clé d'API Wave", /\bwave_[a-z]{2}_(?:prod|dev|test)_[A-Za-z0-9_-]{16,}/],
  ["une clé d'abonnement MTN", /ocp-apim-subscription-key["']?\s*[:=]\s*["']?[0-9a-f]{32}\b/i],
  ["un en-tête Authorization", /\bauthorization["']?\s*[:=]\s*["']?(?:bearer|basic)\s+(?![xX*]{6,}|<|\{|\$\{)[A-Za-z0-9+/=._-]{16,}/i],
];

const INSERTS = {
  bold: ["**", "**", "texte important"],
  code: ["`", "`", "X-Target-Environment"],
  block: ["\n```\n", "\n```\n", "le code ou la réponse de l'API"],
  list: ["\n- ", "", "élément"],
  link: ["[", "](https://)", "titre de la source"],
};
const TEMPLATE = "## Symptôme\n\n\n## Cause\n\n\n## Solution\n\n\n## Pistes qui ont échoué\n\n\n## Preuve\nVersions, étapes, résultat obtenu.\n";

// Aperçu : un sous-ensemble sûr du Markdown (titres, listes, code, gras, liens), texte échappé.
function renderMarkdown(source) {
  const esc = (t) => t.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;").replace(/'/g, "&#39;");
  const inline = (t) => esc(t)
    .replace(/`([^`]+)`/g, "<code>$1</code>")
    .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>")
    .replace(/\[([^\]]+)\]\((https?:\/\/[^)\s]+)\)/g, '<a href="$2" rel="noopener noreferrer nofollow">$1</a>');
  const out = [];
  let list = false;
  const blocks = source.split(/```/);
  blocks.forEach((block, index) => {
    if (index % 2 === 1) {
      if (list) { out.push("</ul>"); list = false; }
      out.push(`<pre><code>${esc(block.replace(/^\w*\n/, ""))}</code></pre>`);
      return;
    }
    for (const line of block.split("\n")) {
      const heading = line.match(/^(#{1,4})\s+(.*)/);
      const item = line.match(/^\s*[-*]\s+(.*)/);
      if (!item && list) { out.push("</ul>"); list = false; }
      if (heading) out.push(`<h4>${inline(heading[2])}</h4>`);
      else if (item) {
        if (!list) { out.push("<ul>"); list = true; }
        out.push(`<li>${inline(item[1])}</li>`);
      } else if (line.trim()) out.push(`<p>${inline(line)}</p>`);
    }
  });
  if (list) out.push("</ul>");
  return out.join("");
}

for (const tools of $$("[data-md-for]")) {
  const area = document.getElementById(tools.dataset.mdFor);
  const preview = document.querySelector(`[data-md-preview="${tools.dataset.mdFor}"]`);
  if (!area) continue;
  tools.hidden = false;

  tools.addEventListener("click", (event) => {
    const insert = event.target.closest("[data-md-insert]")?.dataset.mdInsert;
    const tab = event.target.closest("[data-md-tab]");
    if (insert) {
      const { selectionStart: start, selectionEnd: end, value } = area;
      if (insert === "template") {
        if (value.trim() && !value.includes("## Symptôme")) area.value = `${TEMPLATE}\n${value}`;
        else if (!value.trim()) area.value = TEMPLATE;
        area.focus();
        area.setSelectionRange(14, 14);
      } else {
        const [before, after, sample] = INSERTS[insert];
        const chosen = value.slice(start, end) || sample;
        area.setRangeText(before + chosen + after, start, end, "end");
        area.focus();
        const at = start + before.length;
        area.setSelectionRange(at, at + chosen.length);
      }
      area.dispatchEvent(new Event("input"));
    }
    if (tab && preview) {
      const showPreview = tab.dataset.mdTab === "preview";
      for (const t of $$("[data-md-tab]", tools)) t.setAttribute("aria-selected", String(t === tab));
      preview.innerHTML = showPreview
        ? (renderMarkdown(area.value) || "<p>Rien à afficher pour l'instant.</p>")
        : "";
      preview.hidden = !showPreview;
      area.closest(".field").hidden = showPreview;
    }
  });
}

for (const warn of $$("[data-secret-warn]")) {
  const area = document.getElementById(warn.dataset.secretWarn);
  if (!area) continue;
  const text = warn.querySelector("span");
  const check = () => {
    const found = SECRETS.find(([, pattern]) => pattern.test(area.value));
    warn.hidden = !found;
    if (found) text.textContent = `Ce texte semble contenir ${found[0]}. Remplacez cette valeur par <VOTRE_CLE> avant d'envoyer, sinon l'envoi sera refusé.`;
  };
  area.addEventListener("input", check);
  check();
}

// --- Signaler une panne : symptômes fréquents en un clic -----------------------------------------
for (const quick of $$("[data-quick-for]")) {
  const area = document.getElementById(quick.dataset.quickFor);
  if (!area) continue;
  quick.hidden = false;
  quick.addEventListener("click", (event) => {
    const button = event.target.closest("[data-quick]");
    if (!button) return;
    const text = button.dataset.quick;
    area.value = area.value.trim() ? `${area.value.trim()}\n${text}` : text;
    area.focus();
    area.dispatchEvent(new Event("input"));
  });
}

// --- Pannes : durée écoulée lisible à côté de la date de début ---------------------------------
const since = (date) => {
  const minutes = Math.max(0, Math.round((Date.now() - date.getTime()) / 60000));
  if (minutes < 60) return `${minutes} min`;
  const hours = Math.round(minutes / 60);
  if (hours < 48) return `${hours} h`;
  return `${Math.round(hours / 24)} jours`;
};
for (const time of $$("time[data-since]")) {
  const date = new Date(time.dateTime);
  if (Number.isNaN(date.getTime())) continue;
  const label = document.createElement("span");
  label.className = "since";
  label.textContent = ` (depuis ${since(date)})`;
  time.after(label);
}

// --- Relecture : liste de contrôle avant d'approuver, motif obligatoire pour refuser ----------
for (const form of $$("form[data-review]")) {
  const checks = form.previousElementSibling?.matches("[data-review-checks]")
    ? form.previousElementSibling : null;
  const approve = form.querySelector('button[value="approve"]');
  const note = form.querySelector('input[name="note"]');
  if (checks && approve) {
    checks.hidden = false;
    const boxes = $$("input[data-check]", checks);
    const update = () => { approve.disabled = !boxes.every((b) => b.checked); };
    for (const box of boxes) box.addEventListener("change", update);
    update();
  }
  form.addEventListener("submit", (event) => {
    if (event.submitter?.value === "reject" && note && !note.value.trim()) {
      event.preventDefault();
      note.setCustomValidity("Indiquez le motif du refus : le contributeur le recevra.");
      note.reportValidity();
      note.addEventListener("input", () => note.setCustomValidity(""), { once: true });
    }
  });
}

// --- Glossaire : filtre instantané ---------------------------------------------------------------
const termFilter = document.querySelector("[data-term-filter]");
if (termFilter) {
  termFilter.hidden = false;
  const input = termFilter.querySelector("input");
  const terms = $$(".term");
  const count = document.querySelector("[data-filter-count]");
  const empty = document.querySelector("[data-filter-empty]");
  const fold = (t) => t.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();
  input.addEventListener("input", () => {
    const query = fold(input.value.trim());
    let shown = 0;
    for (const term of terms) {
      const ok = !query || fold(term.textContent).includes(query);
      term.hidden = !ok;
      shown += ok ? 1 : 0;
    }
    if (count) count.textContent = query ? `${shown} sur ${terms.length}` : `${terms.length}`;
    if (empty) empty.hidden = shown > 0;
  });
}

// Raccourci « / » ou Ctrl+K (Cmd+K) : aller au champ de recherche, ou à la page Recherche.
document.addEventListener("keydown", (event) => {
  const typing = event.target.closest("input, textarea, select, [contenteditable]");
  const slash = event.key === "/" && !typing;
  const k = event.key.toLowerCase() === "k" && (event.ctrlKey || event.metaKey);
  if (!slash && !k) return;
  const field = document.querySelector('input[type="search"]');
  event.preventDefault();
  if (field) field.focus();
  else location.href = "/recherche";
});
