// People are never stored in this repo. At build time they come from:
//   1. Baserow (when BASEROW_TOKEN is set) – the long-term source, consent-gated;
//   2. otherwise the live WordPress REST API – only published profiles, which the current
//      Baserow → WordPress sync already gates on consent;
//   3. otherwise (offline / local work) the invented sample people.
import wpIds from '../data/wp-ids.json';
import members from '../data/directory/members.json';
import { fetchRows, selectValue, slugify } from './baserow';
import corrections from '../data/corrections.json';
const removedLeads = corrections.removeLeads as Record<string, string[]>;

export interface Person {
  id: string;
  wpId?: number;
  honorific: string; // Dr, Prof – shown small above the name
  name: string;
  leads: string[];   // slugs of communities this person leads
  email?: string;    // only shown for Club co-leads, as a contact
  role: string;
  institution: string;
  institutionSlug?: string;
  institutionKind?: 'members' | 'collaborations';
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
import collaborators from '../data/directory/collaborations.json';
const collabBySlug = new Map((collaborators as { slug: string; name: string }[]).map((m) => [m.slug, m.name]));

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

// Governance roles, statuses and tags are WordPress taxonomies: fetch their names once.
const NAME_FIX: Record<string, string> = { 'Management Cmte': 'Management Committee', 'Steering Cmte': 'Steering Committee' };
async function terms(tax: string): Promise<Map<number, string>> {
  const res = await fetch(`${WP}/wp-json/wp/v2/${tax}?per_page=100&_fields=id,name`, { signal: AbortSignal.timeout(20000) });
  if (!res.ok) return new Map();
  const list = (await res.json()) as { id: number; name: string }[];
  return new Map(list.map((t) => [t.id, NAME_FIX[t.name] ?? t.name.replace(/&amp;/g, '&')]));
}

async function fromWordPress(): Promise<Person[]> {
  const out: Person[] = [];
  const [govT, statusT, tagT] = await Promise.all([terms('governance-role'), terms('people-status'), terms('people-tag')]);
  for (let page = 1; page < 20; page++) {
    const res = await fetch(`${WP}/wp-json/wp/v2/people?per_page=100&page=${page}&_embed=wp:featuredmedia&_fields=id,slug,title,content,acf,class_list,governance-role,people-status,people-tag,_links,_embedded`, {
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
      const collabSlug = related.collaborations?.[0];
      const classes: string[] = r.class_list ?? [];
      const terms = classes.map((c) => TERMS[c]).filter(Boolean);
      const media = r._embedded?.['wp:featuredmedia']?.[0];
      const leads = asIds(acf.people_activity_leadership).map((id) => ids[id]).filter((h) => h?.[0] === 'activities').map((h) => h![1]);
      out.push({
        id: r.slug,
        wpId: r.id,
        honorific: stripTags(acf.title ?? ''),
        name: stripTags(r.title?.rendered ?? '').replace(/^(Dr|Prof|Professor)\.?\s+/i, ''),
        leads: leads.filter((a) => !(removedLeads[a] ?? []).includes(r.slug)),
        email: acf.email || undefined,
        role: stripTags(acf.uk_node_role ?? ''),
        institution: memberSlug ? memberBySlug.get(memberSlug) ?? '' : collabSlug ? collabBySlug.get(collabSlug) ?? '' : '',
        institutionSlug: memberSlug ?? collabSlug,
        institutionKind: memberSlug ? 'members' : collabSlug ? 'collaborations' : undefined,
        bio: stripTags(acf.people_description || r.content?.rendered || ''),
        orcid: acf.orcid_id || undefined,
        website: acf.website || undefined,
        linkedin: acf.linkedin_account || undefined,
        photo: media?.media_details?.sizes?.medium?.source_url ?? media?.source_url ?? undefined,
        governance: ((r['governance-role'] ?? []) as number[]).map((id) => govT.get(id)).filter(Boolean) as string[],
        status: (((r['people-status'] ?? []) as number[]).map((id) => statusT.get(id)).filter(Boolean)[0] as string) ?? terms.find((t) => ['Current member', 'Alumni', 'Collaborator'].includes(t)) ?? '',
        tags: [], // DaSH Fellow/Mentor/Coordinator tags are no longer used on the site
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
        honorific: String(r['Title'] ?? ''),
        name,
        leads: [],
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

/** Who appears in lists: not alumni; collaborators only if they hold a governance role (e.g. SIAB).
 *  Everyone keeps their own profile page. */
export const isCurrent = (p: { data: { status: string; governance: string[] } }) =>
  p.data.status !== 'Alumni' && (p.data.status !== 'Collaborator' || p.data.governance.length > 0);
