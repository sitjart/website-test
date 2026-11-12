// The site's knowledge graph: every record and every link between records,
// in both directions, built once per build from the directory data, news and events.
import { getCollection } from 'astro:content';
import services from '../data/directory/services.json';
import members from '../data/directory/members.json';
import projects from '../data/directory/projects.json';
import activities from '../data/directory/activities.json';
import collaborations from '../data/directory/collaborations.json';
import areas from '../data/directory/area.json';
import { slugify } from './baserow';

export type Kind = 'services' | 'members' | 'projects' | 'activities' | 'collaborations' | 'area' | 'news' | 'events' | 'people';

export interface DirectoryRecord {
  slug: string;
  name: string;
  website: string;
  logo: string;
  summary: string;
  body: string;
  tags: string[];
  status: string;
  start: string | null;
  end: string | null;
  joinLink: string;
  excerpt?: string;
  leadIds?: number[];
  peopleIds?: number[];
  display?: { hide?: string[]; show?: string[] };
  related: Partial<Record<Kind, string[]>>;
}

export const DIRECTORY: Record<Exclude<Kind, 'news' | 'events' | 'people'>, { title: string; singular: string; records: DirectoryRecord[]; intro?: string }> = {
  services: { title: 'Services', singular: 'Service', records: services as DirectoryRecord[], intro: 'Open-access services for the life sciences community, endorsed by ELIXIR-UK.' },
  members: { title: 'Members', singular: 'Member', records: members as DirectoryRecord[], intro: 'UK research-performing organisations that make up ELIXIR-UK.' },
  projects: { title: 'Projects', singular: 'Project', records: projects as DirectoryRecord[] },
  activities: { title: 'Communities of practice', singular: 'Activity', records: activities as DirectoryRecord[] },
  collaborations: { title: 'Collaborations', singular: 'Collaborator', records: collaborations as DirectoryRecord[] },
  area: { title: 'Thematic areas', singular: 'Thematic area', records: areas as DirectoryRecord[] },
};

// Tab labels, matching the "smart tabs" on the live profile pages
export const LABELS: Record<Kind, string> = {
  news: 'Articles', activities: 'Communities', services: 'Services', projects: 'Projects', events: 'Events',
  members: 'Members', collaborations: 'Collaborators', area: 'Thematic areas', people: 'People',
};
export const TAB_ORDER: Kind[] = ['news', 'activities', 'services', 'projects', 'events', 'members', 'people', 'collaborations', 'area'];

export const tagSlug = (t: string) => slugify(t);

export interface Node { kind: Kind; slug: string; name: string; date?: Date; label?: string; summary?: string }

let cache: { nodes: Map<string, Node>; edges: Map<string, Set<string>> } | null = null;
const key = (kind: Kind, slug: string) => `${kind}/${slug}`;

async function build() {
  if (cache) return cache;
  const nodes = new Map<string, Node>();
  const edges = new Map<string, Set<string>>();
  const link = (a: string, b: string) => {
    if (a === b) return;
    if (!edges.has(a)) edges.set(a, new Set());
    if (!edges.has(b)) edges.set(b, new Set());
    edges.get(a)!.add(b);
    edges.get(b)!.add(a);
  };
  const pending: [string, Partial<Record<Kind, string[]>> | undefined][] = [];

  for (const [kind, { records }] of Object.entries(DIRECTORY) as [Kind, { records: DirectoryRecord[] }][]) {
    for (const r of records) {
      nodes.set(key(kind, r.slug), { kind, slug: r.slug, name: r.name, summary: r.summary, label: r.tags[0] });
      pending.push([key(kind, r.slug), r.related]);
    }
  }
  for (const n of await getCollection('news')) {
    nodes.set(key('news', n.id), { kind: 'news', slug: n.id, name: n.data.title, date: n.data.date, label: n.data.category, summary: n.data.standfirst });
    pending.push([key('news', n.id), n.data.related]);
  }
  for (const e of await getCollection('events')) {
    nodes.set(key('events', e.id), { kind: 'events', slug: e.id, name: e.data.title, date: e.data.start, label: e.data.type });
    pending.push([key('events', e.id), e.data.related]);
  }
  for (const p of await getCollection('people')) {
    nodes.set(key('people', p.id), { kind: 'people', slug: p.id, name: p.data.name, summary: p.data.role, label: p.data.institution });
    pending.push([key('people', p.id), p.data.related]);
  }
  for (const [from, rel] of pending) {
    for (const [kind, slugs] of Object.entries(rel ?? {}) as [Kind, string[]][]) {
      for (const s of slugs) if (nodes.has(key(kind, s))) link(from, key(kind, s));
    }
  }
  cache = { nodes, edges };
  return cache;
}

/** Everything linked to a record, grouped by kind; news and events newest first. */
export async function linksFor(kind: Kind, slug: string) {
  const { nodes, edges } = await build();
  const groups: Partial<Record<Kind, Node[]>> = {};
  for (const k of edges.get(key(kind, slug)) ?? []) {
    const n = nodes.get(k)!;
    (groups[n.kind] ??= []).push(n);
  }
  for (const list of Object.values(groups)) {
    list!.sort((a, b) => (b.date && a.date ? b.date.getTime() - a.date.getTime() : a.name.localeCompare(b.name)));
  }
  return groups;
}

// ---------------------------------------------------------------------------
// Display rules: which links a page shows (src/data/display-rules.json).
// Links stay two-way; this only decides whether this page lists them.
// ---------------------------------------------------------------------------
import rules from '../data/display-rules.json';
export type Display = { hide?: string[]; show?: string[] };
export async function shownLinks(kind: Kind, slug: string, display?: Display) {
  const groups = await linksFor(kind, slug);
  const hiddenKinds = new Set([...((rules as Record<string, { hide?: string[] }>)[kind]?.hide ?? []), ...(display?.hide ?? []).filter((h) => !h.includes('/'))]);
  const hiddenOnes = new Set((display?.hide ?? []).filter((h) => h.includes('/')));
  const forced = new Set(display?.show ?? []);
  const out: typeof groups = {};
  for (const [k, list] of Object.entries(groups) as [Kind, Node[]][]) {
    const keep = list.filter((n) => {
      const id = `${n.kind}/${n.slug}`;
      if (forced.has(id) || forced.has(n.kind)) return true;
      return !hiddenKinds.has(k) && !hiddenOnes.has(id);
    });
    if (keep.length) out[k] = keep;
  }
  return out;
}
