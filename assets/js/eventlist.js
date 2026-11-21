// EventList
const chips = document.querySelectorAll("[data-type]:is(button)");
const rows = document.querySelectorAll(".past li");
chips.forEach((ch) => ch.addEventListener("click", () => {
  const t = ch.dataset.type ?? "";
  chips.forEach((c) => {
    const on = c === ch;
    c.classList.toggle("is-active", on);
    c.setAttribute("aria-pressed", String(on));
  });
  rows.forEach((r) => r.hidden = !!t && r.dataset.type !== t);
  document.querySelectorAll("[data-year]").forEach((y) => y.hidden = !y.querySelector("li:not([hidden])"));
}));
