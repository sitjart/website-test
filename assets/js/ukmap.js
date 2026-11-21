// UkMap
document.querySelectorAll(".ukmap").forEach((fig) => {
  const tpl = fig.querySelector("template.ukmap__data");
  const pop = fig.querySelector(".ukmap__pop");
  const svg = fig.querySelector("svg");
  if (!tpl || !pop || !svg) return;
  const data = JSON.parse(tpl.innerHTML);
  const filtering = fig.hasAttribute("data-filter");
  let pinned = false;
  const show = (i, pin = false) => {
    const d = data[i];
    const vb = svg.viewBox.baseVal;
    const box = svg.getBoundingClientRect();
    const fb = fig.getBoundingClientRect();
    const x = d.x / vb.width * box.width + box.left - fb.left;
    const y = d.y / vb.height * box.height + box.top - fb.top;
    pop.innerHTML = `<p class="ukmap__city">${d.city}</p>` + (d.members.length === 1 ? `<a href="${d.members[0].href}">${d.members[0].name}</a>` : `<ul>${d.members.map((m) => `<li><a href="${m.href}">${m.name}</a></li>`).join("")}</ul>`);
    pop.style.left = `${x}px`;
    pop.style.top = `${y}px`;
    pop.classList.toggle("is-left", x > fb.width * 0.55);
    pop.hidden = false;
    pinned = pin;
  };
  const hide = () => {
    if (!pinned) pop.hidden = true;
  };
  fig.querySelectorAll(".ukmap__dot").forEach((a) => {
    const i = Number(a.dataset.i);
    const multi = data[i].members.length > 1;
    a.addEventListener("mouseenter", () => show(i));
    a.addEventListener("mouseleave", () => setTimeout(() => {
      if (!pop.matches(":hover") && !a.matches(":hover")) hide();
    }, 400));
    a.addEventListener("focus", () => show(i));
    a.addEventListener("blur", () => setTimeout(() => {
      if (!pop.contains(document.activeElement)) {
        pinned = false;
        hide();
      }
    }, 50));
    a.addEventListener("click", (e) => {
      if (filtering) {
        e.preventDefault();
        fig.querySelectorAll(".ukmap__dot").forEach((d) => d.classList.toggle("is-picked", d === a));
        fig.dispatchEvent(new CustomEvent("ukmap:select", { bubbles: true, detail: { city: data[i].city, slugs: data[i].members.map((m) => m.slug) } }));
        show(i, true);
      } else if (multi) {
        e.preventDefault();
        show(i, true);
        pop.querySelector("a")?.focus();
      }
    });
  });
  pop.addEventListener("mouseleave", () => setTimeout(hide, 300));
  fig.addEventListener("ukmap:clear", () => {
    fig.querySelectorAll(".ukmap__dot").forEach((d) => d.classList.remove("is-picked"));
    pinned = false;
    pop.hidden = true;
  });
  document.addEventListener("click", (e) => {
    if (!fig.contains(e.target)) {
      pinned = false;
      pop.hidden = true;
    }
  });
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") {
      pinned = false;
      pop.hidden = true;
    }
  });
});
