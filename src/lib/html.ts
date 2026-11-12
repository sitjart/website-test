// Cleans WordPress HTML for this site, at build time:
// - internal links get the site base and the new route names; links with no page here go to the live site
// - WordPress counter shortcodes become live figures
import { getCollection } from 'astro:content';
import { DIRECTORY } from './graph';
import { nodeStats } from './stats';
import { localAsset } from './assets';
import { url } from './url';
import { parse } from 'node-html-parser';

let known: Set<string> | null = null;
async function routes() {
  if (known) return known;
  const s = new Set<string>();
  for (const c of ['news', 'events', 'people'] as const) (await getCollection(c)).forEach((e) => s.add(`/${c}/${e.id}/`));
  (await getCollection('pages')).forEach((p) => s.add(`/${p.id}/`));
  for (const [k, v] of Object.entries(DIRECTORY)) { s.add(`/${k}/`); v.records.forEach((r) => s.add(`/${k}/${r.slug}/`)); }
  ['/', '/news/', '/events/', '/people/'].forEach((p) => s.add(p));
  known = s;
  return s;
}
const RENAME: Record<string, string> = { service: 'services', project: 'projects', collaborator: 'collaborations', event: 'events', stories: 'news', blog: 'news', uncategorized: 'news', 'news-and-stories': 'news', activity: 'activities' };

// WordPress (Greenshift) accordions and tabs lose their behaviour outside WordPress.
// Rebuild them as native <details> accordions and accessible tabs.
function rebuildWidgets(html: string): string {
  if (!/gs-accordion-item|gspb-tabs|gs-counter/.test(html)) return html;
  const root = parse(html, { comment: false });
  // Animated counters start at 0 and count up with JavaScript: show the final figure instead
  root.querySelectorAll('.gs-counterwrap').forEach((c) => {
    const n = c.querySelector('.gs-counter')?.getAttribute('data-end') ?? c.querySelector('.gs-counter')?.text ?? '';
    const label = c.querySelector('.gs-counterlabel')?.innerHTML ?? '';
    c.replaceWith(`<div class="wp-counter"><b>${n}</b><span>${label}</span></div>`);
  });
  root.querySelectorAll('.gs-accordion-item').forEach((item) => {
    const title = item.querySelector('.gs-accordion-item__heading')?.innerHTML.trim() ?? item.querySelector('.gs-accordion-item__title')?.text.trim() ?? '';
    const body = item.querySelector('.gs-accordion-item__text')?.innerHTML ?? item.querySelector('.gs-accordion-item__content')?.innerHTML ?? '';
    item.replaceWith(`<details class="acc"><summary>${title}</summary><div class="acc__body">${body}</div></details>`);
  });
  root.querySelectorAll('.gs-accordion').forEach((box) => { box.setAttribute('class', 'acc-group'); });
  root.querySelectorAll('.gspb-tabs').forEach((tabs, t) => {
    const labels = tabs.querySelectorAll('.t-btn').map((b) => b.text.trim());
    const panels = tabs.querySelectorAll('.t-panel').map((p) => p.querySelector('.wp-block-greenshift-blocks-tab')?.innerHTML ?? p.innerHTML);
    const id = `wpt${t}`;
    const nav = labels.map((l, i) => `<button type="button" role="tab" id="${id}-t${i}" aria-controls="${id}-p${i}" aria-selected="${i === 0}" tabindex="${i === 0 ? 0 : -1}">${l}</button>`).join('');
    const body = panels.map((p, i) => `<div role="tabpanel" id="${id}-p${i}" aria-labelledby="${id}-t${i}" tabindex="0"${i ? ' hidden' : ''}><h2 class="wp-tabs__print">${labels[i] ?? ''}</h2>${p}</div>`).join('');
    tabs.replaceWith(`<div class="wp-tabs" data-wp-tabs><div class="wp-tabs__nav" role="tablist">${nav}</div>${body}</div>`);
  });
  return root.toString();
}

export async function cleanHtml(html: string): Promise<string> {
  html = rebuildWidgets(html);
  const ok = await routes();
  const s = await nodeStats();
  html = html
    .replace(/\[member_counter\]/g, `<span class="wp-stat">${s.members}</span>`)
    .replace(/\[people_counter\]/g, `<span class="wp-stat">${s.people}</span>`)
    .replace(/\[service_counter\]/g, `<span class="wp-stat">${s.services}</span>`)
    .replace(/\[project_counter\]/g, `<span class="wp-stat">${s.projects}</span>`);
  html = html.replace(/<a class="gspb-containerlink"/g, '<a class="gspb-containerlink" tabindex="-1" aria-hidden="true"');
  return html.replace(/(href|src)="((?:https?:\/\/(?:www\.)?elixiruknode\.org)?(\/[^"#?]*)?)([^"]*)"/g, (all, attr, _full, path: string | undefined, rest: string) => {
    if (path === undefined) return all;                         // external link
    if (!path.startsWith('/') || path.startsWith('//')) return all;
    if (path.startsWith('/wp-content/')) return `${attr}="${localAsset('https://elixiruknode.org' + path)}${rest}"`;
    let p = path.endsWith('/') ? path : `${path}/`;
    const seg = p.split('/').filter(Boolean);
    if (seg.length === 2 && RENAME[seg[0]]) p = `/${RENAME[seg[0]]}/${seg[1]}/`;
    if (seg.length === 1 && !ok.has(p) && ok.has(`/news/${seg[0]}/`)) p = `/news/${seg[0]}/`;
    if (ok.has(p)) return `${attr}="${url(p)}${rest}"`;
    return `${attr}="https://elixiruknode.org${path}${rest}"`;
  });
}
