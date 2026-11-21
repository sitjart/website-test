// DirectoryList
const bar = document.querySelector("[data-member-filter]");
const cardsM = document.querySelectorAll(".members__list li");
document.addEventListener("ukmap:select", (ev) => {
  const { city, slugs } = ev.detail;
  cardsM.forEach((li) => li.hidden = !slugs.includes(li.dataset.slug ?? ""));
  if (bar) {
    bar.hidden = false;
    bar.querySelector("span").textContent = `${slugs.length} ${slugs.length === 1 ? "member" : "members"} in ${city}.`;
  }
});
document.querySelector("[data-member-clear]")?.addEventListener("click", () => {
  cardsM.forEach((li) => li.hidden = false);
  if (bar) bar.hidden = true;
  document.querySelector(".members__map .ukmap")?.dispatchEvent(new CustomEvent("ukmap:clear"));
});
const chips = document.querySelectorAll("[data-filter]");
const items = document.querySelectorAll(".dir-item");
const empty = document.querySelector(".filters__empty");
const status = document.querySelector(".filters__status");
const apply = (tag) => {
  let shown = 0;
  items.forEach((c) => {
    const ok = !tag || (c.dataset.tags ?? "").split(" ").includes(tag);
    c.hidden = !ok;
    if (ok) shown++;
  });
  chips.forEach((ch) => {
    const on = ch.dataset.filter === tag;
    ch.classList.toggle("is-active", on);
    ch.setAttribute("aria-pressed", String(on));
  });
  if (empty) empty.hidden = shown > 0 || !items.length;
  if (status) status.textContent = tag ? `Showing ${shown} of ${items.length}` : "";
};
chips.forEach((ch) => ch.addEventListener("click", () => {
  const tag = ch.dataset.filter ?? "";
  history.replaceState(null, "", tag ? `#${tag}` : location.pathname);
  apply(tag);
}));
if (items.length) apply(decodeURIComponent(location.hash.slice(1)));
