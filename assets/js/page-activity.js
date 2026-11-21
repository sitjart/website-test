// Page: activity
document.querySelectorAll("[data-more-people]").forEach((b) => b.addEventListener("click", () => {
  (b.previousElementSibling ?? b.parentElement)?.querySelectorAll("li[hidden]").forEach((li) => li.hidden = false);
  b.remove();
}));
