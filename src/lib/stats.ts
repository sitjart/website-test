// Figures for the "Node in numbers" band, all computed from the data at build time.
import { getCollection } from 'astro:content';
import { DIRECTORY } from './graph';

export async function nodeStats() {
  const members = DIRECTORY.members.records;
  const years = members.map((m) => Number((m.start ?? '').slice(0, 4))).filter(Boolean);
  const first = Math.min(...years);
  const last = new Date().getFullYear();
  const growth: { year: number; total: number; joined: string[] }[] = [];
  for (let y = first; y <= last; y++) {
    const joined = members.filter((m) => Number((m.start ?? '').slice(0, 4)) === y).map((m) => m.name);
    growth.push({ year: y, total: (growth.at(-1)?.total ?? 0) + joined.length, joined });
  }
  const events = await getCollection('events');
  const people = await getCollection('people');
  const evYears: { year: number; count: number }[] = [];
  for (let y = 2024; y <= last; y++) evYears.push({ year: y, count: events.filter((e) => e.data.start.getUTCFullYear() === y).length });
  const communities = DIRECTORY.activities.records;
  return {
    members: members.length,
    founding: growth[0]?.total ?? 0,
    firstYear: first,
    growth,
    services: DIRECTORY.services.records.filter((s) => s.status === 'Selected').length,
    communities: communities.length,
    leading: communities.filter((c) => c.tags.includes('Leading')).length,
    projects: DIRECTORY.projects.records.length,
    people: people.length,
    events: evYears,
  };
}
