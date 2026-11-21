// Page: activities
const chips = document.querySelectorAll("[data-type]:is(button)");
const items = document.querySelectorAll(".eu li");
chips.forEach((c) => c.addEventListener("click", () => {
  const t = c.dataset.type ?? "";
  items.forEach((li) => li.hidden = !!t && li.dataset.type !== t);
  chips.forEach((x) => {
    const on = x === c;
    x.classList.toggle("is-active", on);
    x.setAttribute("aria-pressed", String(on));
  });
}));
