// Page: home
const dlg = document.getElementById("story-video");
document.querySelectorAll("[data-video]").forEach((b) => b.addEventListener("click", () => {
  if (!dlg) return;
  dlg.querySelector(".video-dialog__frame").innerHTML = `<iframe src="https://www.youtube-nocookie.com/embed/${b.dataset.video}?autoplay=1&rel=0" title="ELIXIR-UK \u2013 our story" allow="autoplay; encrypted-media; picture-in-picture; fullscreen" allowfullscreen></iframe>`;
  dlg.showModal();
}));
const close = () => {
  if (!dlg) return;
  dlg.close();
  dlg.querySelector(".video-dialog__frame").innerHTML = "";
};
dlg?.querySelector("[data-close]")?.addEventListener("click", close);
dlg?.addEventListener("click", (e) => {
  if (e.target === dlg) close();
});
dlg?.addEventListener("cancel", () => setTimeout(close));
