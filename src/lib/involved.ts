// Who is involved in a record, split into leads and everyone else – each person appears once.
// A lead is also part of the community, so leads are listed first and not repeated below.
// Only published profiles are ever available here (see src/lib/people.ts).
import { getCollection, type CollectionEntry } from 'astro:content';
import { linksFor, type DirectoryRecord, type Kind } from './graph';

export async function involved(kind: Kind, r: DirectoryRecord) {
  const people = await getCollection('people');
  const links = await linksFor(kind, r.slug);
  const linked = new Set((links.people ?? []).map((n) => n.slug));
  const isLead = (p: CollectionEntry<'people'>) =>
    (kind === 'activities' && p.data.leads.includes(r.slug)) || (!!p.data.wpId && (r.leadIds ?? []).includes(p.data.wpId));
  const isIn = (p: CollectionEntry<'people'>) =>
    linked.has(p.id) || (!!p.data.wpId && (r.peopleIds ?? []).includes(p.data.wpId)) || (p.data.related[kind] ?? []).includes(r.slug);
  const bySurname = (a: CollectionEntry<'people'>, b: CollectionEntry<'people'>) => a.data.name.split(' ').at(-1)!.localeCompare(b.data.name.split(' ').at(-1)!, 'en-GB');
  const leads = people.filter(isLead).sort(bySurname);
  const others = people.filter((p) => !leads.includes(p) && isIn(p)).sort(bySurname);
  return { leads, others };
}
