// Page: search
const el = document.getElementById("search");
const base = el.dataset.base;
const s = document.createElement("script");
s.src = `${base}pagefind-ui.js`;
s.onload = () => {
  // baseUrl: result links need the site's base path (e.g. /website-test/) in front of them
  const ui = new PagefindUI({ element: "#search", baseUrl: base.replace(/pagefind\/$/, ""), showSubResults: true, showImages: false, resetStyles: false, translations: { placeholder: "Search people, services, communities, news and events" } });
  const q = new URLSearchParams(location.search).get("q");
  if (q) ui.triggerSearch(q);
  el.querySelector("input")?.focus();
};
document.head.appendChild(s);
