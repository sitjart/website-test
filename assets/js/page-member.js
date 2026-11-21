// Page: member
document.querySelectorAll("[data-more]").forEach((b) => b.addEventListener("click", () => {
  b.previousElementSibling?.querySelectorAll("[data-extra]").forEach((li) => li.hidden = false);
  b.remove();
}));
