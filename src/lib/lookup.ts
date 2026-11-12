// Display details for any linked record, so related items can be shown as the right kind of card.
import { getCollection } from 'astro:content';
import { DIRECTORY, type Kind } from './graph';
import home from '../data/home.json';
import { url } from './url';

export interface Card {
  kind: Kind; slug: string; href: string; title: string;
  image?: string; imageKind: 'photo' | 'logo' | 'icon' | 'avatar' | 'art' | 'none';
  date?: Date; meta?: string; text?: string; honorific?: string;
}

let cache: Map<string, Card> | null = null;
async function all() {
  if (cache) return cache;
  const m = new Map<string, Card>();
  const put = (c: Card) => m.set(`${c.kind}/${c.slug}`, c);
  (await getCollection('news')).forEach((n) => put({ kind: 'news', slug: n.id, href: url(`/news/${n.id}/`), title: n.data.title, image: n.data.image, imageKind: n.data.image ? 'photo' : 'none', date: n.data.date, meta: n.data.category, text: n.data.excerpt || n.data.standfirst }));
  (await getCollection('events')).forEach((e) => put({ kind: 'events', slug: e.id, href: url(`/events/${e.id}/`), title: e.data.title, imageKind: 'none', date: e.data.start, meta: `${e.data.type} · ${e.data.format === 'in-person' ? e.data.locality || 'In person' : e.data.format === 'hybrid' ? 'Hybrid' : 'Online'}` }));
  (await getCollection('people')).forEach((p) => put({ kind: 'people', slug: p.id, href: url(`/people/${p.id}/`), title: p.data.name, honorific: p.data.honorific, image: p.data.photo, imageKind: 'avatar', meta: p.data.role || p.data.institution }));
  const art = home.areaIllustrations as Record<string, string>;
  for (const [k, v] of Object.entries(DIRECTORY)) {
    v.records.forEach((r) => put({
      kind: k as Kind, slug: r.slug, href: url(`/${k}/${r.slug}/`), title: r.name,
      image: k === 'area' ? (art[r.slug] ? url(`/assets/wp/${art[r.slug]}`) : r.logo) : r.logo,
      imageKind: k === 'activities' ? 'icon' : k === 'area' ? 'art' : r.logo ? 'logo' : 'none',
      meta: k === 'projects' ? [r.start?.slice(0, 4), r.end?.slice(0, 4)].filter(Boolean).join('–') : k === 'activities' ? r.tags.find((t) => ['Club', 'Community', 'Focus Group', 'Platform'].includes(t)) : r.status || undefined,
      text: r.excerpt || r.summary,
    }));
  }
  cache = m;
  return m;
}
export async function cardFor(kind: Kind, slug: string) { return (await all()).get(`${kind}/${slug}`); }
export async function cardsFor(kind: Kind, slugs: string[]) {
  const m = await all();
  return slugs.map((s) => m.get(`${kind}/${s}`)).filter(Boolean) as Card[];
}
