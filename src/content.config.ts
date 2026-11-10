import { defineCollection } from 'astro:content';
import { glob } from 'astro/loaders';
import { z } from 'astro/zod';
import { fetchRows, selectValue, slugify } from './lib/baserow';

// ---------------------------------------------------------------------------
// Page sections: the building blocks a page is made of, in order.
// Each one matches a section type on the current WordPress home page.
// ---------------------------------------------------------------------------
const button = z.object({ label: z.string(), href: z.string() });
const reveal = z.enum(['fade-up', 'fade-down', 'fade-left', 'fade-right', 'fade-up-blur', 'fade-down-blur', 'zoom-in', 'none']);
const background = z.enum(['page', 'white', 'grey', 'navy']);

const section = z.discriminatedUnion('type', [
  // Full-width video or image with navy overlay and page title
  z.object({
    type: z.literal('hero'),
    heading: z.string(),
    text: z.string().optional(),
    video: z.string().optional(),
    image: z.string().optional(),
    buttons: z.array(button).default([]),
  }),
  // Row of cards; "overlap" pulls them up over the hero, as on the home page
  z.object({
    type: z.literal('cards'),
    heading: z.string().optional(),
    overlap: z.boolean().default(false),
    background: background.default('page'),
    reveal: reveal.default('fade-up'),
    items: z.array(z.object({ title: z.string(), text: z.string().optional(), href: z.string().optional() })),
  }),
  // "What's new": featured story plus smaller cards, pulled from the news collection
  z.object({
    type: z.literal('latestNews'),
    heading: z.string().default('What’s new'),
    label: z.string().default('Latest stories'),
    count: z.number().int().default(3),
    background: background.default('grey'),
  }),
  // "Coming up": next events, pulled from the events collection
  z.object({
    type: z.literal('upcomingEvents'),
    heading: z.string().default('Coming up'),
    label: z.string().default('Upcoming events'),
    count: z.number().int().default(3),
    background: background.default('grey'),
  }),
  // Big number with text, button and either an image or a scrolling logo strip
  z.object({
    type: z.literal('stat'),
    text: z.string(),
    value: z.string(), // a number, or "members" / "services" to count the records
    label: z.string(),
    button,
    image: z.string().optional(),
    logos: z.enum(['services', 'members']).optional(),
    background: background.default('page'),
  }),
  // Plain text block
  z.object({
    type: z.literal('text'),
    heading: z.string().optional(),
    body: z.string(),
    background: background.default('page'),
  }),
  // Closing call to action
  z.object({
    type: z.literal('cta'),
    heading: z.string(),
    text: z.string().optional(),
    button,
    background: background.default('navy'),
  }),
]);

const pages = defineCollection({
  loader: glob({ pattern: '**/*.md', base: './src/content/pages' }),
  schema: z.object({
    title: z.string(),
    description: z.string().optional(),
    sections: z.array(section).default([]),
  }),
});

const related = z.record(z.string(), z.array(z.string())).optional();

// ---------------------------------------------------------------------------
// Editorial content imported from WordPress (decision on news vs Baserow pending)
// ---------------------------------------------------------------------------
const news = defineCollection({
  loader: glob({ pattern: '**/*.md', base: './src/content/news' }),
  schema: z.object({
    title: z.string(),
    date: z.coerce.date(),
    standfirst: z.string(),
    category: z.string().default('News'),
    image: z.string().optional(),
    related,
  }),
});

const events = defineCollection({
  loader: glob({ pattern: '**/*.md', base: './src/content/events' }),
  schema: z.object({
    title: z.string(),
    start: z.coerce.date(),
    end: z.coerce.date().optional(),
    startTime: z.string().optional(),
    endTime: z.string().optional(),
    type: z.string(),
    online: z.boolean().default(false),
    venue: z.string().optional(),
    locality: z.string().optional(),
    registration: z.string().optional(),
    recording: z.string().optional(),
    slides: z.string().optional(),
    image: z.string().optional(),
    related,
  }),
});

// ---------------------------------------------------------------------------
// People: always from Baserow at build time, never stored in the repo.
// Only rows with consent given are published. The mock-up uses invented people.
// ---------------------------------------------------------------------------
const people = defineCollection({
  loader: async () => {
    const rows = await fetchRows(process.env.BASEROW_PEOPLE_TABLE, 'people.json');
    return rows
      .filter((r) => selectValue(r['Website status']) === 'Consent given')
      .map((r) => {
        const name = `${r['First name']} ${r['Last name']}`;
        const list = (v: unknown) => (Array.isArray(v) ? v.map((x) => (typeof x === 'object' && x && 'value' in x ? String(x.value) : String(x))) : []);
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
          related: (r['Related'] as Record<string, string[]>) ?? {},
        };
      });
  },
  schema: z.object({
    name: z.string(),
    role: z.string(),
    institution: z.string(),
    bio: z.string(),
    orcid: z.string().optional(),
    website: z.string().optional(),
    linkedin: z.string().optional(),
    photo: z.string().optional(),
    governance: z.array(z.string()).default([]),
    related: z.record(z.string(), z.array(z.string())).default({}),
  }),
});

export const collections = { pages, news, events, people };
