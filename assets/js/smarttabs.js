// SmartTabs
document.querySelectorAll("[data-more]").forEach((b) => b.addEventListener("click", () => {
  b.previousElementSibling?.querySelectorAll("[data-extra]").forEach((li) => li.hidden = false);
  b.remove();
}));
document.querySelectorAll("[data-smart-tabs]").forEach((box) => {
  const buttons = box.querySelectorAll(".smart-tab-btn");
  if (!buttons.length) return;
  box.classList.add("is-enhanced");
  const show = (id) => {
    buttons.forEach((b) => {
      const on = b.dataset.tab === id;
      b.classList.toggle("active", on);
      b.setAttribute("aria-selected", String(on));
      b.tabIndex = on ? 0 : -1;
    });
    box.querySelectorAll(".tab-panel").forEach((p) => p.classList.toggle("active", p.dataset.panel === id));
  };
  buttons.forEach((b, i) => {
    b.addEventListener("click", () => show(b.dataset.tab));
    b.addEventListener("keydown", (e) => {
      const step = e.key === "ArrowRight" ? 1 : e.key === "ArrowLeft" ? -1 : 0;
      if (!step) return;
      const next = buttons[(i + step + buttons.length) % buttons.length];
      next.focus();
      show(next.dataset.tab);
    });
  });
});
