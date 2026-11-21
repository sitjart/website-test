// RelatedCards
document.querySelectorAll("[data-rc-more]").forEach((b) => b.addEventListener("click", () => {
  b.closest(".rc-wrap")?.querySelectorAll("li[hidden]").forEach((li) => li.hidden = false);
  b.remove();
}));
