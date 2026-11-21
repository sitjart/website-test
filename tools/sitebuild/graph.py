"""The site's knowledge graph: every record and every link between records, in both directions.

A link can be written on either side (a story lists a service, or a person lists a story);
both pages then show it. Three rules shape what each page shows:

1. The organisation rule. When a story or event is tagged with a person AND with that person's
   organisation, the organisation tag is dropped: the organisation is there because of the person.
   Keep it by listing the organisation under `about:` in the story or event – it is then about the
   organisation itself. An organisation's own page still lists stories and events about its people.
2. Display rules (_data/display-rules.json and per-record `display:`) decide which kinds of links a
   page lists. Links stay two-way; hiding only stops one side listing them.
3. corrections.json removes people from leads or governance roles until the source data is fixed.
"""
from collections import defaultdict

from .common import DATA, KINDS, REPORT, load_json

ORG_RULE_KINDS = ('news', 'events')          # where the organisation rule applies
ORG_KINDS = ('members', 'collaborations')
LABELS = {'news': 'Articles', 'activities': 'Communities', 'services': 'Services', 'projects': 'Projects', 'events': 'Events',
          'members': 'Members', 'collaborations': 'Collaborators', 'area': 'Thematic areas', 'people': 'People'}
RULES = load_json(DATA / 'display-rules.json')
TAB_ORDER = ['news', 'activities', 'services', 'projects', 'events', 'members', 'people', 'collaborations', 'area']


class Graph:
    def __init__(self, directory, news, events, people):
        self.nodes = {}                      # 'kind/slug' -> record
        self.edges = defaultdict(set)
        self.about = {}                      # 'kind/slug' -> set of 'kind/slug' the item is about
        pending = []
        for kind in KINDS:
            for r in directory[kind]:
                self._add(kind, r['slug'], r, r['related'], r.get('about'), pending)
        for n in news:
            self._add('news', n['slug'], n, n['related'], n['about'], pending)
        for e in events:
            self._add('events', e['slug'], e, e['related'], e['about'], pending)
        for p in people:
            self._add('people', p['id'], p, p['related'], None, pending)
        # People are tagged by number (their WordPress, later Baserow, id), so no names are stored in content
        by_number = {str(p['wpId']): p['id'] for p in people if p.get('wpId')}
        dangling = defaultdict(list)
        for src, related in pending:
            for kind, slugs in related.items():
                for s in slugs:
                    if kind == 'people':
                        s = by_number.get(str(s), s)
                    key = f'{kind}/{s}'
                    if key in self.nodes:
                        self._link(src, key)
                    elif kind != 'people':      # people without a published profile are expected
                        dangling[src].append(key)
        for src, keys in dangling.items():
            REPORT.warn(src, f'links to records that do not exist: {", ".join(sorted(set(keys)))}')
        self._organisation_rule()

    def _add(self, kind, slug, record, related, about, pending):
        key = f'{kind}/{slug}'
        self.nodes[key] = {'kind': kind, 'slug': slug, 'record': record}
        self.about[key] = {f'{k}/{s}' for k, ss in (about or {}).items() for s in ss}
        pending.append((key, related or {}))

    def _link(self, a, b):
        if a != b:
            self.edges[a].add(b)
            self.edges[b].add(a)

    def _unlink(self, a, b):
        self.edges[a].discard(b)
        self.edges[b].discard(a)

    def _organisation_rule(self):
        dropped = 0
        for key, node in self.nodes.items():
            if node['kind'] not in ORG_RULE_KINDS:
                continue
            people = [self.nodes[k]['record'] for k in self.edges[key] if k.startswith('people/')]
            via_people = {f"{p['institutionKind']}/{p['institutionSlug']}" for p in people if p.get('institutionSlug')}
            for org in [k for k in self.edges[key] if k.split('/')[0] in ORG_KINDS]:
                if org in via_people and org not in self.about[key]:
                    self._unlink(key, org)
                    dropped += 1
        REPORT.note(f'Organisation rule: {dropped} organisation tags dropped from stories and events because one of their people is tagged')

    # ------------------------------------------------------------------
    def links(self, kind, slug):
        """Everything linked to a record, grouped by kind; news and events newest first, the rest by name."""
        groups = defaultdict(list)
        for k in self.edges[f'{kind}/{slug}']:
            n = self.nodes[k]
            groups[n['kind']].append(n['slug'])
        for k, slugs in groups.items():
            recs = {s: self.nodes[f'{k}/{s}']['record'] for s in slugs}
            if k == 'news':
                slugs.sort(key=lambda s: recs[s]['date'], reverse=True)
            elif k == 'events':
                slugs.sort(key=lambda s: recs[s]['start'], reverse=True)
            else:
                slugs.sort(key=lambda s: (recs[s].get('name') or recs[s].get('title') or '').lower())
        return dict(groups)

    def shown(self, kind, slug, display):
        """links() minus what the display rules hide on this kind of page."""
        hidden_kinds = set((RULES.get(kind) or {}).get('hide') or []) | {h for h in display['hide'] if '/' not in h}
        hidden_ones = {h for h in display['hide'] if '/' in h}
        forced = set(display['show'])
        out = {}
        for k, slugs in self.links(kind, slug).items():
            keep = [s for s in slugs if f'{k}/{s}' in forced or k in forced or (k not in hidden_kinds and f'{k}/{s}' not in hidden_ones)]
            if keep:
                out[k] = keep
        return out
