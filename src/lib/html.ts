// Cleans WordPress HTML for this site, at build time:
// - internal links get the site base and the new route names; links with no page here go to the live site
// - WordPress counter shortcodes become live figures
import { getCollection } from 'astro:content';
import { DIRECTORY } from './graph';
import { nodeStats } from './stats';
import { localAsset } from './assets';
import { url } from './url';

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

export async function cleanHtml(html: string): Promise<string> {
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
