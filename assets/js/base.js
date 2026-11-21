// Every page: scroll reveal and tabs rebuilt from WordPress content
const els = document.querySelectorAll("[data-reveal]");
if (!("IntersectionObserver" in window)) {
  els.forEach((el) => el.classList.add("is-visible"));
} else {
  const io = new IntersectionObserver(
    (entries) => entries.forEach((e) => {
      if (e.isIntersecting) {
        e.target.classList.add("is-visible");
        io.unobserve(e.target);
      }
    }),
    { rootMargin: "0px 0px -10% 0px" }
  );
  els.forEach((el) => io.observe(el));
}
document.querySelectorAll("[data-wp-tabs]").forEach((box) => {
  const tabs = [...box.querySelectorAll("[role=tab]")];
  const show = (t) => tabs.forEach((b) => {
    const on = b === t;
    b.setAttribute("aria-selected", String(on));
    b.tabIndex = on ? 0 : -1;
    const p = document.getElementById(b.getAttribute("aria-controls"));
    if (p) p.hidden = !on;
  });
  tabs.forEach((b, i) => {
    b.addEventListener("click", () => show(b));
    b.addEventListener("keydown", (e) => {
      const d = e.key === "ArrowRight" ? 1 : e.key === "ArrowLeft" ? -1 : 0;
      if (d) {
        const n = tabs[(i + d + tabs.length) % tabs.length];
        n.focus();
        show(n);
      }
    });
  });
});
