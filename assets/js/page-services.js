// Page: services
const chips = document.querySelectorAll("[data-label]");
const items = document.querySelectorAll(".scards li");
const apply = (label) => {
  items.forEach((li) => li.hidden = !!label && !(li.dataset.labels ?? "").split(" ").includes(label));
  document.querySelectorAll(".sgroup").forEach((g) => g.hidden = !g.querySelector("li:not([hidden])"));
  document.querySelectorAll("[data-explain]").forEach((e) => e.hidden = e.dataset.explain !== label);
  chips.forEach((c) => {
    const on = c.dataset.label === label;
    c.classList.toggle("is-active", on);
    c.setAttribute("aria-pressed", String(on));
  });
};
chips.forEach((c) => c.addEventListener("click", () => {
  const l = c.dataset.label ?? "";
  history.replaceState(null, "", l ? `#${l}` : location.pathname);
  apply(l);
}));
const start = decodeURIComponent(location.hash.slice(1));
if ([...chips].some((c) => c.dataset.label === start)) apply(start);
