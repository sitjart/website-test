// Page: people
const q = document.querySelector("#q");
const chips = document.querySelectorAll("[data-g]:is(button)");
const items = document.querySelectorAll(".people-grid li");
const status = document.querySelector(".status");
let group = "";
const apply = () => {
  const v = q.value.trim().toLowerCase();
  let n = 0;
  items.forEach((li) => {
    const ok = (!v || (li.dataset.q ?? "").includes(v)) && (!group || (li.dataset.g ?? "").split(" ").includes(group));
    li.hidden = !ok;
    if (ok) n++;
  });
  status.textContent = v || group ? `${n} ${n === 1 ? "person" : "people"}` : "";
};
q.addEventListener("input", apply);
chips.forEach((c) => c.addEventListener("click", () => {
  group = c.dataset.g ?? "";
  chips.forEach((x) => {
    const on = x === c;
    x.classList.toggle("is-active", on);
    x.setAttribute("aria-pressed", String(on));
  });
  history.replaceState(null, "", group ? `#${group}` : location.pathname);
  apply();
}));
const start = location.hash.slice(1);
const hit = [...chips].find((c) => c.dataset.g === start);
if (hit) hit.click();
