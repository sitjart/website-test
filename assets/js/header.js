// Header
const header = document.querySelector("[data-header]");
const onScroll = () => header.classList.toggle("is-stuck", window.scrollY > 40);
window.addEventListener("scroll", onScroll, { passive: true });
onScroll();
const toggle = document.querySelector("[data-nav-toggle]");
toggle?.addEventListener("click", () => {
  const open = toggle.getAttribute("aria-expanded") === "true";
  toggle.setAttribute("aria-expanded", String(!open));
  header.classList.toggle("nav-open", !open);
});
const desktop = matchMedia("(min-width: 1025px)");
const btns = [...header.querySelectorAll("[data-mega-btn]")];
const scrim = header.querySelector("[data-mega-scrim]");
let closeTimer = 0;
const setOpen = (btn) => {
  btns.forEach((b) => {
    const on = b === btn;
    b.setAttribute("aria-expanded", String(on));
    b.closest("li")?.classList.toggle("is-open", on);
  });
  scrim.hidden = !btn || !desktop.matches;
  header.classList.toggle("mega-open", !!btn);
};
btns.forEach((b) => {
  const li = b.closest("li");
  b.addEventListener("click", () => setOpen(b.getAttribute("aria-expanded") === "true" ? null : b));
  let openTimer = 0;
  li.addEventListener("mouseenter", () => {
    if (!desktop.matches) return;
    clearTimeout(closeTimer);
    openTimer = window.setTimeout(() => setOpen(b), 120);
  });
  li.addEventListener("mouseleave", () => {
    if (!desktop.matches) return;
    clearTimeout(openTimer);
    closeTimer = window.setTimeout(() => setOpen(null), 220);
  });
});
scrim.addEventListener("click", () => setOpen(null));
document.addEventListener("keydown", (e) => {
  if (e.key !== "Escape") return;
  const open = btns.find((b) => b.getAttribute("aria-expanded") === "true");
  if (open) {
    setOpen(null);
    open.focus();
  } else if (header.classList.contains("nav-open")) {
    toggle?.click();
    toggle?.focus();
  }
});
header.addEventListener("focusout", (e) => {
  if (desktop.matches && !header.contains(e.relatedTarget)) setOpen(null);
});
