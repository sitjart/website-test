// NewsList
const grid = document.querySelector(".ngrid");
const more = document.querySelector("[data-more]");
const chips = document.querySelectorAll("[data-cat]");
if (grid && more) {
  const page = Number(grid.dataset.page);
  const all = [...grid.querySelectorAll("li")];
  let cat = "", limit = page;
  const render = () => {
    const match = all.filter((li) => !cat || li.dataset.cat === cat);
    all.forEach((li) => li.hidden = true);
    match.slice(0, limit).forEach((li) => li.hidden = false);
    more.hidden = match.length <= limit;
    more.textContent = `Show more stories (${match.length - limit} more)`;
  };
  more.addEventListener("click", () => {
    const firstNew = limit;
    limit += page;
    render();
    all.filter((li) => !li.hidden)[firstNew]?.querySelector("a")?.focus();
  });
  chips.forEach((ch) => ch.addEventListener("click", () => {
    cat = ch.dataset.cat ?? "";
    limit = page;
    chips.forEach((c) => {
      const on = c === ch;
      c.classList.toggle("is-active", on);
      c.setAttribute("aria-pressed", String(on));
    });
    render();
  }));
  render();
}
