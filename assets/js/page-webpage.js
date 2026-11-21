// Page: webpage
const links = [...document.querySelectorAll(".toc a")];
if (links.length && "IntersectionObserver" in window) {
  const io = new IntersectionObserver((entries) => entries.forEach((e) => {
    if (e.isIntersecting) links.forEach((l) => l.classList.toggle("is-current", l.hash === `#${e.target.id}`));
  }), { rootMargin: "0px 0px -70% 0px" });
  links.forEach((l) => {
    const h = document.getElementById(l.hash.slice(1));
    if (h) io.observe(h);
  });
}
