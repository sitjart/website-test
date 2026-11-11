// People are never stored in this repo. At build time they come from:
//   1. Baserow (when BASEROW_TOKEN is set) – the long-term source, consent-gated;
//   2. otherwise the live WordPress REST API – only published profiles, which the current
//      Baserow → WordPress sync already gates on consent;
//   3. otherwise (offline / local work) the invented sample people.
import wpIds from '../data/wp-ids.json';
import members from '../data/directory/members.json';
import { fetchRows, selectValue, slugify } from './baserow';

export interface Person {
  id: string;
  name: string;
  role: string;
  institution: string;
  institutionSlug?: string;
  bio: string;
  orcid?: string;
  website?: string;
  linkedin?: string;
  photo?: string;
  governance: string[];
  status: string;
  tags: string[];
  related: Record<string, string[]>;
}

const WP = process.env.WP_URL ?? 'https://elixiruknode.org';
const ids = wpIds as Record<string, [string, string]>;
const memberBySlug = new Map((members as { slug: string; name: string }[]).map((m) => [m.slug, m.name]));

// Taxonomy term slugs as they appear in WordPress class names -> display names
const TERMS: Record<string, string> = {
  'governance-role-coordination-office': 'Coordination office',
  'governance-role-heads-of-node': 'Heads of Node',
  'governance-role-management-cmte': 'Management Committee',
  'governance-role-scientific-development-group': 'Scientific Development Group',
  'governance-role-scientific-and-industry-advisory-board': 'Scientific and Industry Advisory Board',
  'governance-role-steering-cmte': 'Steering Committee',
  'people-status-current-member': 'Current member',
  'people-status-alumni': 'Alumni',
  'people-status-collaborator': 'Collaborator',
  'people-tag-dash-fellow': 'DaSH Fellow',
  'people-tag-dash-mentor': 'DaSH Mentor',
};

const asIds = (v: unknown): string[] =>
  v === '' || v == null ? [] : (Array.isArray(v) ? v : [v]).map((x) => String(typeof x === 'object' && x && 'ID' in x ? (x as { ID: number }).ID : x));

const stripTags = (html: string) => html.replace(/<[^>]+>/g, ' ').replace(/&nbsp;/g, ' ').replace(/&#8217;/g, '’').replace(/&amp;/g, '&').replace(/\s+/g, ' ').trim();

async function fromWordPress(): Promise<Person[]> {
  const out: Person[] = [];
  for (let page = 1; page < 20; page++) {
    const res = await fetch(`${WP}/wp-json/wp/v2/people?per_page=100&page=${page}&_embed=wp:featuredmedia&_fields=slug,title,content,acf,class_list,_links,_embedded`, {
      signal: AbortSignal.timeout(20000),
    });
    if (res.status === 400) break; // past the last page
    if (!res.ok) throw new Error(`WordPress people: ${res.status}`);
    const rows = (await res.json()) as any[];
    for (const r of rows) {
      const acf = r.acf ?? {};
      const related: Record<string, string[]> = {};
      for (const key of ['people_related_member', 'people_related_organisation', 'people_related_projects', 'people_related_activities', 'people_related_services', 'people_related_posts', 'people_related_events']) {
        for (const id of asIds(acf[key])) {
          const hit = ids[id];
          if (hit) (related[hit[0]] ??= []).includes(hit[1]) || related[hit[0]].push(hit[1]);
        }
      }
      const memberSlug = related.members?.[0];
      const classes: string[] = r.class_list ?? [];
      const terms = classes.map((c) => TERMS[c]).filter(Boolean);
      const media = r._embedded?.['wp:featuredmedia']?.[0];
      out.push({
        id: r.slug,
        name: stripTags(r.title?.rendered ?? ''),
        role: stripTags(acf.title ?? ''),
        institution: memberSlug ? memberBySlug.get(memberSlug) ?? '' : '',
        institutionSlug: memberSlug,
        bio: stripTags(acf.people_description || r.content?.rendered || ''),
        orcid: acf.orcid_id || undefined,
        website: acf.website || undefined,
        linkedin: acf.linkedin_account || undefined,
        photo: media?.media_details?.sizes?.medium?.source_url ?? media?.source_url ?? undefined,
        governance: terms.filter((t) => classes.some((c) => c.startsWith('governance-role') && TERMS[c] === t)),
        status: terms.find((t) => ['Current member', 'Alumni', 'Collaborator'].includes(t)) ?? '',
        tags: terms.filter((t) => t.startsWith('DaSH')),
        related,
      });
    }
    if (rows.length < 100) break;
  }
  return out;
}

async function fromBaserowOrSample(): Promise<Person[]> {
  const rows = await fetchRows(process.env.BASEROW_PEOPLE_TABLE, 'people.json');
  const list = (v: unknown) => (Array.isArray(v) ? v.map((x) => (typeof x === 'object' && x && 'value' in x ? String((x as any).value) : String(x))) : []);
  return rows
    .filter((r) => selectValue(r['Website status']) === 'Consent given')
    .map((r) => {
      const name = `${r['First name']} ${r['Last name']}`;
      return {
        id: slugify(name),
        name,
        role: String(r['Job title'] ?? ''),
        institution: String(r['Institution'] ?? ''),
        bio: String(r['Bio'] ?? ''),
        orcid: (r['ORCID'] as string) || undefined,
        website: (r['Website'] as string) || undefined,
        linkedin: (r['LinkedIn'] as string) || undefined,
        photo: (r['Photo URL'] as string) || undefined,
        governance: list(r['Governance roles']),
        status: 'Current member',
        tags: [],
        related: (r['Related'] as Record<string, string[]>) ?? {},
      };
    });
}

export async function loadPeople(): Promise<Person[]> {
  if (process.env.BASEROW_TOKEN) return fromBaserowOrSample();
  if (process.env.PEOPLE_SOURCE !== 'sample') {
    try {
      const people = await fromWordPress();
      if (people.length) {
        console.log(`[people] ${people.length} published profiles from WordPress`);
        return people;
      }
    } catch (e) {
      console.warn(`[people] WordPress not reachable (${(e as Error).message}); using sample people`);
    }
  }
  return fromBaserowOrSample();
}
