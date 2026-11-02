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
