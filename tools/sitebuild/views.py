"""What each page shows, worked out in Python so the templates only have to print it.

One function per kind of page. Every value a template uses is always present (None when empty),
so the strict templates never meet a missing field.
"""
import datetime as dt
import math
import re
import urllib.parse

from .common import BASEURL, DATA, KINDS, TODAY, UK, date_parts, first_sentence, load_json, needs_stop, plain, slugify, surname_key, t
from .graph import LABELS, TAB_ORDER
from .images import local_asset
from .people import is_current

HOME = load_json(DATA / 'home.json')
LABELS_SVC = load_json(DATA / 'service-labels.json')
LOCATIONS = load_json(DATA / 'member-locations.json')
CORRECTIONS = load_json(DATA / 'corrections.json')
NAV = load_json(DATA / 'navigation.json')
SINGULAR = {'services': 'Service', 'members': 'Member', 'projects': 'Project', 'activities': 'Activity', 'collaborations': 'Collaborator', 'area': 'Thematic area'}
PLURAL = {'services': 'Services', 'members': 'Members', 'projects': 'Projects', 'activities': 'Communities of practice', 'collaborations': 'Collaborations', 'area': 'Thematic areas'}
COMMUNITY_TYPES = ['Club', 'Community', 'Focus Group', 'Platform']


def year(d):
    return str(d.year) if d else ''


def initials(name):
    words = re.sub(r'\(.*?\)', '', plain(name)).split()
    return ''.join(w[0] for w in words)[:2].upper()


def asset(file):
    return f'/assets/wp/{file}' if file else None


def fmt_where(e):
    if e['format'] == 'online':
        return 'Online'
    if e['format'] == 'hybrid':
        return f"Hybrid · {e['locality']}" if e['locality'] else 'Hybrid'
    return e['locality'] or 'In person'


def is_upcoming(e):
    return (e['end'] or e['start']) >= TODAY


class Views:
    def __init__(self, directory, news, events, people, pages, graph, images):
        self.d, self.news, self.events, self.people, self.pages, self.g, self.img = directory, news, events, people, pages, graph, images
        self.rec = {k: {r['slug']: r for r in directory[k]} for k in KINDS}
        self.news_by = {n['slug']: n for n in news}
        self.events_by = {e['slug']: e for e in events}
        self.people_by = {p['id']: p for p in people}
        self.people_by_wp = {p['wpId']: p for p in people if p['wpId']}
        self.current = [p for p in people if is_current(p)]
        self.news_sorted = sorted(news, key=lambda n: n['date'], reverse=True)
        self.upcoming = sorted([e for e in events if is_upcoming(e)], key=lambda e: e['start'])

    # ------------------------------------------------------------------ building blocks
    def icon(self, r):
        """Community or platform icon (always an SVG copied into the repo)."""
        return {'src': local_asset(r['logo']) if r['logo'] else None, 'letter': plain(r['name'])[:1]}

    def person(self, p, email=False):
        """One person in a list: photo, name, organisation or role."""
        return {
            'href': f"/people/{p['id']}/", 'name': t(p['name']), 'honorific': t(p['honorific']),
            'role': t(p['role']), 'institution': t(p['institution']),
            'sub': t(p['institution'] or p['role']),
            'photo': self.img.get(p['photo'], 'person'), 'initials': initials(p['name']),
            'email': p['email'] if email else None,
        }

    def card(self, kind, slug):
        """Display details for any record, so related items can be shown as the right kind of card."""
        if kind == 'news':
            n = self.news_by.get(slug)
            if not n:
                return None
            text = n['excerpt'] or n['standfirst']
            return {'kind': kind, 'style': 'story', 'href': f'/news/{slug}/', 'title': t(n['title']), 'image': self.img.get(n['image'], 'photo'),
                    'initials': '', 'date': date_parts(n['date']), 'meta': t(n['category']), 'text': t(first_sentence(text, 140)) if text else None}
        if kind == 'events':
            e = self.events_by.get(slug)
            if not e:
                return None
            return {'kind': kind, 'style': 'event', 'href': f'/events/{slug}/', 'title': t(e['title']), 'image': None, 'initials': '',
                    'date': date_parts(e['start']), 'meta': t(f"{e['type']} · {'Hybrid' if e['format'] == 'hybrid' else 'Online' if e['format'] == 'online' else e['locality'] or 'In person'}"), 'text': None}
        if kind == 'people':
            p = self.people_by.get(slug)
            if not p or not is_current(p):
                return None
            return {'kind': kind, 'style': 'person', 'href': f'/people/{slug}/', 'title': t(p['name']), 'image': self.img.get(p['photo'], 'person'),
                    'initials': initials(p['name']), 'date': None, 'meta': t(p['role'] or p['institution']) or None, 'text': None}
        r = self.rec[kind].get(slug)
        if not r:
            return None
        text = r['excerpt'] or r['summary']
        if kind == 'activities':
            style, image = 'icon', {'small': {'src': local_asset(r['logo']), 'w': None, 'h': None}, 'large': {'src': local_asset(r['logo']), 'w': None, 'h': None}} if r['logo'] else None
            meta = next((x for x in r['tags'] if x in COMMUNITY_TYPES), None)
        elif kind == 'area':
            art = HOME['areaIllustrations'].get(slug)
            style, image = 'art', {'small': {'src': asset(art) if art else r['logo'], 'w': None, 'h': None}, 'large': {'src': asset(art) if art else r['logo'], 'w': None, 'h': None}}
            meta = None
        else:
            style, image = ('project' if kind == 'projects' else 'logo'), self.img.get(r['logo'], 'logo')
            meta = '–'.join(x for x in [year(r['start']), year(r['end'])] if x) if kind == 'projects' else (r['status'] or None)
        return {'kind': kind, 'style': style, 'href': f'/{kind}/{slug}/', 'title': t(r['name']), 'image': image, 'initials': plain(r['name'])[:1],
                'date': None, 'meta': t(meta) if meta else None, 'text': t(first_sentence(text, 140)) if text else None}

    def cards(self, kind, slugs):
        return [c for c in (self.card(kind, s) for s in slugs) if c]

    def tabs(self, kind, slug, display, skip=(), heading=None):
        """'Related' tabs: one tab per kind of linked record, empty tabs left out."""
        groups = self.g.shown(kind, slug, display)
        panels = []
        for k in TAB_ORDER:
            if k in skip or k not in groups:
                continue
            cs = self.cards(k, groups[k])
            if cs:
                panels.append({'id': k, 'label': LABELS[k], 'count': len(cs), 'cards': cs})
        return {'uid': f'tabs-{kind}-{slug}', 'heading': heading, 'panels': panels}

    def involved(self, kind, r):
        """Who is involved in a record, split into leads and everyone else – each person once."""
        pool = [p for p in self.people if (p['status'] != 'Alumni' if kind == 'collaborations' else is_current(p))]
        linked = set(self.g.links(kind, r['slug']).get('people', []))
        removed = set(CORRECTIONS.get('removeLeads', {}).get(r['slug'], []))

        def is_lead(p):
            return p['id'] not in removed and ((kind == 'activities' and r['slug'] in p['leads']) or (p['wpId'] and p['wpId'] in r['leadIds']))

        def is_in(p):
            return p['id'] in linked or (p['wpId'] and p['wpId'] in r['peopleIds']) or r['slug'] in (p['related'].get(kind) or [])

        leads = sorted([p for p in pool if is_lead(p)], key=lambda p: surname_key(p['name']))
        others = sorted([p for p in pool if not is_lead(p) and is_in(p)], key=lambda p: surname_key(p['name']))
        return leads, others

    def people_of(self, org_kind, slug):
        return [p for p in self.current if p['institutionKind'] == org_kind and p['institutionSlug'] == slug]

    # ------------------------------------------------------------------ site-wide pieces
    def stats(self):
        members = self.d['members']
        years = sorted({e['start'].year for e in self.events if e['start'].year >= 2024})
        acts = self.d['activities']
        return {
            'members': len(members),
            'services': sum(1 for s in self.d['services'] if s['status'] == 'Selected'),
            'communities': len(acts),
            'leading': sum(1 for a in acts if 'Leading' in a['tags']),
            'projects': len(self.d['projects']),
            'people': len(self.people),
            'events_total': sum(1 for e in self.events if e['start'].year >= 2024),
            'events_since': years[0] if years else TODAY.year,
        }

    def ukmap(self):
        """Member map: one dot per city. Projection fitted to the outline (see tools/geo)."""
        A, B, C, D = 62.68, 520.7, -3656.72, 4739.31
        merc = lambda lat: math.log(math.tan(math.pi / 4 + lat * math.pi / 360))
        cities = {}
        for m in self.d['members']:
            loc = LOCATIONS.get(m['slug'])
            if not loc:
                continue
            c = cities.setdefault(loc['city'], {'city': loc['city'], 'x': round(A * loc['lon'] + B, 2), 'y': round(C * merc(loc['lat']) + D, 2), 'members': []})
            c['members'].append({'slug': m['slug'], 'name': t(m['name']), 'href': f"/members/{m['slug']}/", 'abs': f"{BASEURL}/members/{m['slug']}/"})
        out = []
        for i, c in enumerate(sorted(cities.values(), key=lambda c: c['y'])):
            n = len(c['members'])
            r = 11 + min(n, 6) * 2.2 if n > 1 else 10
            names = ', '.join(plain(m['name']) for m in c['members'])
            out.append({**c, 'i': i, 'n': n, 'r': round(r, 1), 'hit': round(r + 14, 1), 'halo': round(r + 16, 1), 'ty': round(c['y'] + 6, 2),
                        'single_href': c['members'][0]['href'] if n == 1 else None,
                        'label': t(f"{plain(c['members'][0]['name'])}, {c['city']}" if n == 1 else f"{c['city']}: {n} members – {names}")})
        data = [{'city': c['city'], 'x': c['x'], 'y': c['y'], 'members': [{'name': plain(m['name']), 'slug': m['slug'], 'href': m['abs']} for m in c['members']]} for c in out]
        return {'cities': out, 'city_of': {m: l['city'] for m, l in LOCATIONS.items()}, 'popup_data': data,
                'outline': (DATA.parent / 'tools/geo/uk-outline.txt').read_text().strip()}

    def orbit(self):
        """Hero art: Platforms, then Clubs and UK-led Communities, then the rest, orbiting the logo mark."""
        acts = [a for a in self.d['activities'] if a['logo'] and a['logo'].lower().endswith('.svg') and a['slug'] != 'fellowship']
        platforms = [a for a in acts if 'Platform' in a['tags']]
        led = [a for a in acts if a not in platforms and ('Club' in a['tags'] or 'Leading' in a['tags'])]
        others = [a for a in acts if a not in platforms and a not in led]
        spec = [(26, 9.5, 120, platforms, 'ELIXIR Platforms'), (39, 8.5, 170, led, 'ELIXIR-UK Clubs and UK-led Communities'),
                (51, 7.5, 230, others, 'ELIXIR Communities and Focus Groups')]
        rings = []
        for k, (r, size, dur, items, label) in enumerate(spec):
            nodes = []
            for j in range(6):
                a = j / 6 * math.pi * 2 + k * 0.5 + 0.26
                nodes.append({'cx': round(50 + r * math.cos(a), 3), 'cy': round(50 + r * math.sin(a), 3), 'r': 0.7 if k == 0 else 0.5})
            rings.append({'k': k, 'r': r, 'size': size, 'dur': dur, 'dir': 'reverse' if k % 2 else 'normal', 'label': label, 'nodes': nodes,
                          'items': [{'href': f"/activities/{a['slug']}/", 'name': t(a['name']), 'icon': local_asset(a['logo']),
                                     'deg': round(i / len(items) * 360 + k * 17, 3)} for i, a in enumerate(items)]})
        return {'rings': rings, 'mark': (DATA.parent / 'tools/geo/logo-mark.txt').read_text().strip()}

    def header(self):
        clubs = [a for a in self.d['activities'] if 'Club' in a['tags']]
        items = []
        for i, item in enumerate(NAV):
            mega = item.get('mega')
            hrefs = [item['href']] + ([l['href'] for c in mega['columns'] for l in c['links']] if mega else [])
            items.append({**item, 'i': i, 'cta': bool(item.get('cta')), 'mega': mega and {
                'intro': mega['intro'], 'cta': mega['cta'], 'feature': mega.get('feature'), 'has_columns': len(mega['columns']) > 0,
                'columns': [{'heading': c['heading'], 'links': [{'label': l['label'], 'href': l['href'], 'desc': l.get('desc')} for l in c['links']]} for c in mega['columns']],
            }, 'section_hrefs': [h for h in hrefs if h != '/']})
        return {
            'items': items,
            'next_events': [{'href': f"/events/{e['slug']}/", 'day': str(e['start'].day), 'month': f"{e['start']:%b}", 'type': t(e['type']),
                             'format': {'in-person': 'In person', 'hybrid': 'Hybrid'}.get(e['format'], 'Online'), 'title': t(e['title'])} for e in self.upcoming[:3]],
            'latest': [{'href': f"/news/{n['slug']}/", 'image': self.img.get(n['image'], 'photo'), 'category': t(n['category']),
                        'date': date_parts(n['date'])['long'], 'title': t(n['title'])} for n in self.news_sorted[:3]],
            'clubs': [{'href': f"/activities/{c['slug']}/", 'name': t(c['name']), 'icon': self.icon(c)} for c in clubs],
            'members': len(self.d['members']),
        }

    # ------------------------------------------------------------------ pages
    def home(self, stats):
        yt = re.search(r'(?:youtu\.be/|v=|embed/)([A-Za-z0-9_-]{11})', HOME.get('storyVideo') or '')
        names = {'services': 'services', 'projects': 'projects', 'activities': 'communities', 'events': 'events'}
        areas = []
        for slug in HOME['thematic']:
            r = self.rec['area'][slug]
            links = self.g.links('area', slug)
            counts = [{'n': len(links[k]), 'label': names[k]} for k in ['services', 'projects', 'activities', 'events'] if links.get(k)][:3]
            areas.append({'href': f'/area/{slug}/', 'name': t(r['name']), 'art': asset(HOME['areaIllustrations'].get(slug)), 'counts': counts})
        leads = [a for a in self.d['activities'] if 'Leading' in a['tags'] or 'Club' in a['tags']]
        services = [s for s in self.d['services'] if s['status'] == 'Selected']
        news = []
        for n in self.news_sorted[:3]:
            news.append({'href': f"/news/{n['slug']}/", 'image': self.img.get(n['image'], 'photo'), 'meta': f"{t(n['category'])} · {date_parts(n['date'])['long']}",
                         'title': t(n['title']), 'sum': t(first_sentence(n['standfirst'], 140)) if n['standfirst'] else None})
        return {
            'intro': t(HOME['intro']), 'video': yt.group(1) if yt else None, 'stats': stats,
            'mission': [{'title': m['title'], 'text': m['text'], 'href': m['href'], 'art': asset(m['illustration']), 'highlight': bool(m.get('highlight')), 'draft': bool(m.get('draft'))} for m in HOME['mission']],
            'areas': areas,
            'leads': [{'href': f"/activities/{a['slug']}/", 'name': t(a['name']), 'icon': self.icon(a), 'kind': 'ELIXIR-UK Club' if 'Club' in a['tags'] else 'ELIXIR Community'} for a in leads],
            'leads_abroad': sum(1 for a in leads if 'Club' not in a['tags']),
            'news': news,
            'upcoming': [{'href': f"/events/{e['slug']}/", 'day': str(e['start'].day), 'month': f"{e['start']:%b}", 'type': t(e['type']) + (' · Online' if e['format'] == 'online' else ''), 'title': t(e['title'])} for e in self.upcoming[:4]],
            'services_count': len(services),
            'services': [{'href': f"/services/{s['slug']}/", 'name': t(s['name']), 'logo': self.img.get(s['logo'], 'logo')} for s in services if s['logo']][:15],
            'jsonld': {'@context': 'https://schema.org', '@type': 'Organization', 'name': 'ELIXIR-UK', 'url': 'https://elixiruknode.org',
                       'parentOrganization': {'@type': 'Organization', 'name': 'ELIXIR', 'url': 'https://elixir-europe.org'},
                       'member': [{'@type': 'Organization', 'name': plain(m['name'])} for m in self.d['members']]},
        }

    def about(self, stats):
        order = ['Heads of Node', 'Coordination office', 'Management Committee', 'Scientific Development Group', 'Scientific and Industry Advisory Board']
        gov = []
        for g in order:
            ps = sorted([p for p in self.current if g in p['governance']], key=lambda p: surname_key(p['name']))
            if ps:
                gov.append({'name': g, 'people': [self.person(p) for p in ps]})
        # Distributed ELIXIR diagram: Nodes placed loosely on a jittered grid, each linked to its three
        # nearest neighbours; the Hub coordinates; ELIXIR-UK highlighted with its member organisations.
        seed = [11]

        def rnd():
            seed[0] = seed[0] * 16807 % 2147483647
            return seed[0] / 2147483647
        nodes = []
        for gy in range(5):
            for gx in range(5):
                if (gx == 2 and gy == 2) or rnd() < 0.12:
                    continue
                nodes.append({'x': 40 + gx * 55 + (rnd() - 0.5) * 30, 'y': 40 + gy * 55 + (rnd() - 0.5) * 30, 'uk': False})
        uk = min(nodes, key=lambda n: math.hypot(n['x'] - 70, n['y'] - 85))
        uk['uk'] = True
        mesh = set()
        for i, n in enumerate(nodes):
            near = sorted([(math.hypot(n['x'] - m['x'], n['y'] - m['y']), j) for j, m in enumerate(nodes) if j != i])[:3]
            for _, j in near:
                mesh.add((min(i, j), max(i, j)))
        r2 = lambda v: round(v, 2)
        members = [{'x': r2(uk['x'] + (26 + (i % 2) * 6) * math.cos(i / 10 * math.pi * 2)), 'y': r2(uk['y'] + (26 + (i % 2) * 6) * math.sin(i / 10 * math.pi * 2))} for i in range(10)]
        return {
            'stats': stats, 'gov': gov,
            'diagram': {
                'hub': {'x': 150, 'y': 150},
                'nodes': [{'x': r2(n['x']), 'y': r2(n['y']), 'r': 11 if n['uk'] else 7, 'uk': n['uk']} for n in nodes],
                'mesh': [{'x1': r2(nodes[i]['x']), 'y1': r2(nodes[i]['y']), 'x2': r2(nodes[j]['x']), 'y2': r2(nodes[j]['y'])} for i, j in sorted(mesh)],
                'uk': {'x': r2(uk['x']), 'y': r2(uk['y']), 'label_y': r2(uk['y'] - 42)},
                'uk_members': members,
            },
        }

    def activities_index(self):
        acts = sorted([r for r in self.d['activities'] if r['slug'] != 'fellowship'], key=lambda r: plain(r['name']).lower())
        clubs = [r for r in acts if 'Club' in r['tags']]
        europe = [r for r in acts if r not in clubs]
        type_of = lambda r: next((x for x in r['tags'] if x in ('Platform', 'Community', 'Focus Group')), 'Community')
        text = lambda r: t(r['excerpt'] or first_sentence(r['summary'], 160))
        types = [('Platform', 'Platforms', 'overarching areas, such as data, tools or training, that span the work of many Communities.'),
                 ('Community', 'Communities', 'established groups focused on a specific life science domain.'),
                 ('Focus Group', 'Focus Groups', 'newer groups working on a specific topic for a set period, after which they either become a Community or close.')]
        return {
            'count': len(acts),
            'clubs': [{'href': f"/activities/{r['slug']}/", 'name': t(r['name']), 'icon': self.icon(r), 'text': text(r)} for r in clubs],
            'europe': [{'href': f"/activities/{r['slug']}/", 'name': t(r['name']), 'icon': self.icon(r), 'type': type_of(r), 'leading': 'Leading' in r['tags'], 'text': text(r)} for r in europe],
            'types': [{'key': k, 'label': l, 'text': x, 'n': sum(1 for r in europe if type_of(r) == k)} for k, l, x in types],
        }

    def activity(self, r):
        links = self.g.links('activities', r['slug'])
        events = [self.events_by[s] for s in links.get('events', []) if s in self.events_by]
        upcoming = sorted([e for e in events if is_upcoming(e)], key=lambda e: e['start'])
        past = sorted([e for e in events if not is_upcoming(e)], key=lambda e: e['start'], reverse=True)
        leads, others = self.involved('activities', r)
        fellowship = r['slug'] == 'fellowship'
        kind = 'Fellowship' if fellowship else next((x for x in r['tags'] if x in COMMUNITY_TYPES), 'Community')
        club = kind == 'Club'
        nxt = upcoming[0] if upcoming else None
        call = nxt and nxt['type'] == 'Community Call'
        lead_ids = {p['id'] for p in leads}
        ev = lambda e: {'href': f"/events/{e['slug']}/", 'date': date_parts(e['start'])['short'], 'title': t(e['title']),
                        'meta': fmt_where(e) + (f" · {e['startTime']}" if e['startTime'] else ''), 'recording': bool(e['recording'])}
        return {
            'name': t(r['name']), 'stop': needs_stop(r['name']), 'club': club, 'fellowship': fellowship,
            'kind_label': {'Club': 'ELIXIR-UK Club', 'Community': 'ELIXIR Community', 'Focus Group': 'ELIXIR Focus Group', 'Platform': 'ELIXIR Platform', 'Fellowship': 'ELIXIR-UK Fellowship'}[kind],
            'leading': 'Leading' in r['tags'],
            'lead_text': t(r['excerpt'] or first_sentence(r['summary'], 260)) or None,
            'join': r['joinLink'] or None,
            'website': r['website'] if r['website'] and 'elixiruknode.org' not in r['website'] else None,
            'icon': self.icon(r),
            'next': nxt and {'href': f"/events/{nxt['slug']}/", 'label': 'Next call' if call else 'Next event',
                             'when': date_parts(nxt['start'])['long'] + (f", {nxt['startTime']}" if nxt['startTime'] else ''),
                             'title': t(nxt['title']), 'go': 'Join in' if call else 'Register'},
            'fellows': [{**self.person(p), 'badge': 'Lead' if p['id'] in lead_ids else None} for p in leads + [o for o in others if o['id'] not in lead_ids]] if fellowship else [],
            'body': r['body'] or f"<p>{t(r['summary'])}</p>",
            'leads': [self.person(p, email=club) for p in leads],
            'others': [self.person(p) for p in others],
            'stories': self.cards('news', links.get('news', [])),
            'stories_heading': 'Stories from the ' + ('Club' if club else 'Fellowship' if fellowship else 'community'),
            'tabs': self.tabs('activities', r['slug'], r['display'], skip=('news', 'events', 'people'), heading='Also linked'),
            'events_heading': 'Community Calls' if club else 'Events',
            'has_events': len(events) > 0,
            'upcoming': [ev(e) for e in upcoming], 'past': [ev(e) for e in past],
            'none_text': 'Nothing scheduled yet' + (' – join to hear about the next one.' if r['joinLink'] else '.'),
            'join_text': 'Joining is free. You’ll get invitations to every Community Call and news from the Club.' if club else 'Find out how to take part.',
            'join_label': 'Join the Club' if club else 'Join in',
        }

    def member(self, r):
        links = self.g.links('members', r['slug'])
        here = self.people_of('members', r['slug'])
        linked = set(links.get('people', []))
        people = [p for p in self.current if p in here or p['id'] in linked]
        reps = [p for p in people if 'Steering Committee' in p['governance']]
        crew = [p for p in people if p not in reps]
        # Stories and events: about the organisation itself, plus those its people are part of
        news_ids, event_ids = set(links.get('news', [])), set(links.get('events', []))
        acts = {}
        for p in here:
            pl = self.g.links('people', p['id'])
            news_ids |= set(pl.get('news', []))
            event_ids |= set(pl.get('events', []))
            mine = set(p['related'].get('activities') or []) | set(p['leads']) | set(pl.get('activities', []))
            mine |= {a['slug'] for a in self.d['activities'] if p['wpId'] and p['wpId'] in a['peopleIds'] + a['leadIds']}
            for s in mine:
                acts[s] = acts.get(s, 0) + 1
        stories = sorted([self.news_by[s] for s in news_ids if s in self.news_by], key=lambda n: n['date'], reverse=True)
        evs = sorted([self.events_by[s] for s in event_ids if s in self.events_by], key=lambda e: e['start'], reverse=True)
        act_cards = self.cards('activities', list(acts))
        for c in act_cards:
            n = acts[c['href'].split('/')[2]]
            c['meta'] = t(f"{n} {'person' if n == 1 else 'people'} from {plain(r['name'])}")
        act_cards.sort(key=lambda c: (-acts[c['href'].split('/')[2]], c['title']))
        city = (LOCATIONS.get(r['slug']) or {}).get('city')
        crew_view = lambda p: {**self.person(p)}
        return {
            'name': t(r['name']), 'stop': needs_stop(r['name']), 'slug': r['slug'],
            'logo': self.img.get(r['logo'], 'logo'), 'initials': initials(r['name']),
            'city': city, 'since': year(r['start']) or None, 'summary': t(r['summary']) or None, 'website': r['website'] or None,
            'reps': [self.person(p) for p in reps],
            'reps_plural': len(reps) > 1,
            'crew': [crew_view(p) for p in crew[:10]], 'crew_count': len(crew),
            'services': self.cards('services', links.get('services', [])),
            'communities': act_cards,
            'projects': [{'href': f'/projects/{s}/', 'name': t(self.rec['projects'][s]['name']), 'meta': t((self.rec['projects'][s]['tags'] or [None])[0]) or None} for s in links.get('projects', [])],
            'events': self.cards('events', [e['slug'] for e in evs]),
            'news': self.cards('news', [n['slug'] for n in stories]),
            'jsonld': {'@context': 'https://schema.org', '@type': 'Organization', 'name': plain(r['name']), 'url': r['website'] or None, 'logo': r['logo'] or None,
                       'memberOf': {'@type': 'Organization', 'name': 'ELIXIR-UK'}},
        }

    def record(self, kind, r):
        """Single service, project, collaborator or thematic area."""
        links = self.g.links(kind, r['slug'])
        hosts = [self.rec['members'][s] for s in links.get('members', []) if s in self.rec['members']]
        leads, others = self.involved(kind, r)
        status = next((s for s in LABELS_SVC['statuses'] if s['tag'] == r['status']), None)
        recognitions = [x for x in LABELS_SVC['recognitions'] if x['tag'] in r['tags']]
        facts = []
        if kind == 'services' and status:
            facts.append({'k': 'Status', 'v': status['title'].replace(' services', '')})
        if kind == 'services' and r['start']:
            facts.append({'k': 'Endorsed since', 'v': year(r['start'])})
        if kind == 'projects' and r['start']:
            facts.append({'k': 'Dates', 'v': year(r['start']) + (f"–{year(r['end'])}" if r['end'] and year(r['end']) != year(r['start']) else '')})
        if kind == 'projects' and [x for x in r['tags'] if x != 'Leading']:
            facts.append({'k': 'Type', 'v': ' · '.join(x for x in r['tags'] if x != 'Leading')})
        if 'Leading' in r['tags']:
            facts.append({'k': 'Role', 'v': 'Led or coordinated by ELIXIR-UK'})
        art = HOME['areaIllustrations'].get(r['slug']) if kind == 'area' else None
        schema = {'services': 'SoftwareApplication', 'collaborations': 'Organization', 'projects': 'ResearchProject', 'area': 'Thing'}[kind]
        return {
            'kind': kind, 'singular': SINGULAR[kind], 'plural': PLURAL[kind],
            'name': t(r['name']), 'stop': needs_stop(r['name']),
            'status': status['title'].replace(' services', '') if status else None,
            'lead_text': t(r['excerpt'] or (first_sentence(r['summary'], 240) if not r['body'] else '')) or None,
            'recognitions': [{'slug': slugify(x['tag']), 'short': x['short'], 'text': x['text']} for x in recognitions],
            'website': r['website'] or None, 'join': r['joinLink'] or None,
            'art': asset(art), 'logo': self.img.get(r['logo'], 'logo'),
            'body': r['body'] or None, 'summary': t(r['summary']) or 'No description yet.',
            'facts': facts, 'is_service': kind == 'services',
            'hosts': [{'href': f"/members/{m['slug']}/", 'name': t(m['name']), 'logo': self.img.get(m['logo'], 'logo')} for m in hosts],
            'hosts_label': 'Run by' if kind == 'services' else 'Members involved',
            'leads': [self.person(p) for p in leads], 'others': [self.person(p) for p in others],
            'tabs': self.tabs(kind, r['slug'], r['display'], skip=('people',) + (('members',) if hosts else ()), heading='Related'),
            'jsonld': {'@context': 'https://schema.org', '@type': schema, 'name': plain(r['name']), 'url': r['website'] or None, 'logo': r['logo'] or None,
                       'description': plain(r['excerpt'] or r['summary']) or None},
        }

    def directory_list(self, kind):
        recs = sorted(self.d[kind], key=lambda r: plain(r['name']).lower())
        href = lambda r: f"/{kind}/{r['slug']}/"
        sum_ = lambda r, n: t(r['excerpt'] or first_sentence(r['summary'], n)) or None
        out = {'count': len(recs), 'members': [], 'collaborations': [], 'areas': [], 'project_groups': []}
        if kind == 'members':
            out['members'] = [{'slug': r['slug'], 'href': href(r), 'name': t(r['name']), 'logo': self.img.get(r['logo'], 'logo'), 'letter': plain(r['name'])[:1],
                               'meta': ' · '.join(x for x in [(LOCATIONS.get(r['slug']) or {}).get('city'), f"since {year(r['start'])}" if r['start'] else ''] if x)} for r in recs]
        if kind == 'collaborations':
            out['collaborations'] = [{'href': href(r), 'name': t(r['name']), 'logo': self.img.get(r['logo'], 'logo'), 'letter': plain(r['name'])[:1],
                                      'sum': t(first_sentence(r['summary'], 110)) if r['summary'] else None} for r in recs]
        if kind == 'area':
            out['areas'] = [{'href': href(r), 'name': t(r['name']), 'art': asset(HOME['areaIllustrations'].get(r['slug'])) or (local_asset(r['logo']) if r['logo'] else None),
                             'sum': t(first_sentence(r['summary'], 140)) if r['summary'] else None} for r in recs]
        if kind == 'projects':
            by_start = lambda r: r['start'] or dt.date(1900, 1, 1)
            leading = sorted([r for r in recs if 'Leading' in r['tags']], key=by_start, reverse=True)
            groups = [('leading', 'Led or coordinated by ELIXIR-UK', 'Projects ELIXIR-UK leads or coordinates.', leading),
                      ('elixir', 'ELIXIR projects', 'Funded within ELIXIR: Platform-led, Community-led and strategic projects.',
                       sorted([r for r in recs if r not in leading and 'ELIXIR Project' in r['tags']], key=by_start, reverse=True)),
                      ('eu-national', 'EU and national projects', 'European and UK projects with ELIXIR-UK members as partners.',
                       sorted([r for r in recs if r not in leading and 'ELIXIR Project' not in r['tags']], key=by_start, reverse=True))]
            out['project_groups'] = [{'id': i, 'title': ti, 'text': tx, 'items': [{
                'href': href(r), 'name': t(r['name']), 'sum': sum_(r, 160),
                'years': year(r['start']) + (f"–{year(r['end'])}" if r['end'] and year(r['end']) != year(r['start']) else ''),
                'tags': [x for x in r['tags'] if x not in ('ELIXIR Project', 'Leading')][:2]} for r in items]} for i, ti, tx, items in groups if items]
        return out

    def services_index(self):
        recs = self.d['services']
        groups = []
        for s in LABELS_SVC['statuses']:
            items = sorted([r for r in recs if r['status'] == s['tag']], key=lambda r: plain(r['name']).lower())
            if items:
                groups.append({'tag': s['tag'], 'id': s['tag'].lower(), 'title': s['title'], 'text': s['text'], 'draft': bool(s.get('draft')), 'items': [{
                    'href': f"/services/{r['slug']}/", 'name': t(r['name']), 'logo': self.img.get(r['logo'], 'logo'),
                    'sum': t(r['excerpt'] or first_sentence(r['summary'], 130)) or None,
                    'labels': ' '.join(slugify(x) for x in r['tags']),
                    'badges': [{'short': x['short'], 'text': x['text']} for x in LABELS_SVC['recognitions'] if x['tag'] in r['tags']]} for r in items]})
        return {
            'all': len(recs), 'selected': sum(1 for r in recs if r['status'] == 'Selected'), 'groups': groups,
            'recognitions': [{'slug': slugify(x['tag']), 'short': x['short'], 'text': x['text'], 'n': sum(1 for r in recs if x['tag'] in r['tags'])} for x in LABELS_SVC['recognitions']],
            'statuses': [{'title': s['title'], 'text': s['text'], 'draft': bool(s.get('draft'))} for s in LABELS_SVC['statuses']],
        }

    def people_index(self):
        order = ['Heads of Node', 'Coordination office', 'Management Committee', 'Steering Committee', 'Scientific Development Group', 'Scientific and Industry Advisory Board']
        ps = sorted(self.current, key=lambda p: surname_key(p['name']))
        return {
            'groups': [{'name': g, 'slug': slugify(g), 'n': sum(1 for p in ps if g in p['governance'])} for g in order if any(g in p['governance'] for p in ps)],
            'people': [{**self.person(p), 'q': t(f"{p['name']} {p['role']} {p['institution']}".lower()), 'g': ' '.join(slugify(x) for x in p['governance']),
                        'gov': t(' · '.join(p['governance'])) or None} for p in ps],
        }

    def person_page(self, p):
        kind = p['institutionKind'] or 'members'
        org = self.rec[kind].get(p['institutionSlug']) if p['institutionSlug'] else None
        links = []
        if p['orcid']:
            links.append({'label': 'ORCID', 'icon': 'iD', 'href': p['orcid'] if p['orcid'].startswith('http') else f"https://orcid.org/{p['orcid']}"})
        if p['linkedin']:
            links.append({'label': 'LinkedIn', 'icon': 'in', 'href': p['linkedin']})
        if p['website']:
            links.append({'label': 'Website', 'icon': '↗', 'href': p['website']})
        leads = [self.rec['activities'][s] for s in p['leads'] if s in self.rec['activities']]
        tabs = self.tabs('people', p['id'], {'hide': [], 'show': []}, skip=('members',))
        return {
            **self.person(p), 'photo': self.img.get(p['photo'], 'person'),
            'org': org and {'href': f"/{kind}/{org['slug']}/", 'name': t(org['name']), 'logo': self.img.get(org['logo'], 'logo')},
            'links': links, 'governance': p['governance'],
            'leads': [{'href': f"/activities/{a['slug']}/", 'name': t(a['name']), 'icon': self.icon(a)} for a in leads],
            'bio': t(p['bio']) or None, 'tabs': tabs,
            'jsonld': {'@context': 'https://schema.org', '@type': 'Person', 'name': plain(p['name']), 'honorificPrefix': p['honorific'] or None,
                       'jobTitle': p['role'] or None, 'affiliation': {'@type': 'Organization', 'name': plain(p['institution'])} if p['institution'] else None,
                       'sameAs': [l['href'] for l in links], 'memberOf': {'@type': 'Organization', 'name': 'ELIXIR-UK'}},
        }

    def news_list(self, items):
        items = sorted(items, key=lambda n: n['date'], reverse=True)
        first, rest = (items[0], items[1:]) if items else (None, [])
        cats = {}
        for n in rest:
            cats[n['category']] = cats.get(n['category'], 0) + 1
        row = lambda n: {'href': f"/news/{n['slug']}/", 'image': self.img.get(n['image'], 'photo'), 'category': t(n['category']), 'cat': slugify(n['category']),
                         'date': date_parts(n['date'])['long'], 'title': t(n['title']), 'sum': t(n['excerpt'] or first_sentence(n['standfirst'], 150)) or None}
        return {
            'feature': first and {**row(first), 'sum': t(first['excerpt'] or first['standfirst']) or None},
            'cats': [{'name': c, 'slug': slugify(c), 'n': n} for c, n in sorted(cats.items(), key=lambda x: -x[1])] if len({n['category'] for n in items}) > 1 else [],
            'items': [row(n) for n in rest], 'count': len(rest), 'page': 18,
        }

    def story(self, n):
        links = self.g.shown('news', n['slug'], n['display'])
        words = len(plain(n['body']).split())
        page_url = f"https://elixiruknode.org/news/{n['slug']}/"
        q = urllib.parse.quote
        acts = set(links.get('activities', []))
        more = [x for x in self.news_sorted if x['slug'] != n['slug'] and acts & set(x['related'].get('activities') or [])][:3]
        if not more:
            more = [x for x in self.news_sorted if x['slug'] != n['slug']][:3]
        return {
            'date': date_parts(n['date']), 'minutes': max(1, round(words / 220)), 'stop': needs_stop(n['title']), 'standfirst': t(n['standfirst']) or None,
            'image': self.img.get(n['image'], 'photo'),
            'share': {'linkedin': f'https://www.linkedin.com/sharing/share-offsite/?url={q(page_url, safe="")}',
                      'bluesky': f'https://bsky.app/intent/compose?text={q(plain(n["title"]) + " " + page_url, safe="")}',
                      'email': f'mailto:?subject={q(plain(n["title"]), safe="")}&body={q(page_url, safe="")}'},
            'people': [self.person(self.people_by[s]) for s in links.get('people', []) if s in self.people_by],
            'communities': [{'href': f'/activities/{s}/', 'name': t(self.rec['activities'][s]['name']), 'icon': self.icon(self.rec['activities'][s])} for s in links.get('activities', [])],
            'members': [{'href': f'/members/{s}/', 'name': t(self.rec['members'][s]['name'])} for s in links.get('members', [])],
            'tabs': self.tabs('news', n['slug'], n['display'], skip=('people', 'members', 'news'), heading='Related'),
            'more': self.cards('news', [x['slug'] for x in more]),
            'description': plain(n['excerpt'] or n['standfirst']) or None,
            'jsonld': {'@context': 'https://schema.org', '@type': 'NewsArticle', 'headline': plain(n['title']), 'datePublished': n['date'].isoformat(),
                       'image': n['image'], 'description': plain(n['standfirst']) or None, 'publisher': {'@type': 'Organization', 'name': 'ELIXIR-UK'}},
        }

    def event_list(self, items):
        up = sorted([e for e in items if is_upcoming(e)], key=lambda e: e['start'])
        past = sorted([e for e in items if not is_upcoming(e)], key=lambda e: e['start'], reverse=True)
        types = {}
        for e in past:
            types[e['type']] = types.get(e['type'], 0) + 1
        years = []
        for e in past:
            if not years or years[-1]['year'] != e['start'].year:
                years.append({'year': e['start'].year, 'items': []})
            years[-1]['items'].append({'href': f"/events/{e['slug']}/", 'day': str(e['start'].day), 'month': f"{e['start']:%b}", 'title': t(e['title']),
                                       'type': t(e['type']), 'type_slug': slugify(e['type']), 'where': fmt_where(e), 'recording': bool(e['recording']), 'slides': bool(e['slides'])})
        return {
            'upcoming': [{'href': f"/events/{e['slug']}/", 'month': f"{e['start']:%b}", 'day': str(e['start'].day), 'weekday': f"{e['start']:%a}",
                          'type': t(e['type']), 'title': t(e['title']), 'where': fmt_where(e) + (f" · {e['startTime']} UK time" if e['startTime'] else '')} for e in up],
            'past_count': len(past), 'types': [{'name': k, 'slug': slugify(k), 'n': v} for k, v in sorted(types.items(), key=lambda x: -x[1])],
            'years': years,
        }

    def event(self, e):
        past = not is_upcoming(e)
        multi = e['end'] and e['end'] != e['start']
        when = f"{date_parts(e['start'])['long']} – {date_parts(e['end'])['long']}" if multi else date_parts(e['start'])['long']
        time = f"{e['startTime']}{'–' + e['endTime'] if e['endTime'] else ''} UK time" if e['startTime'] else None
        formats = {'online': 'Online', 'in-person': 'In person', 'hybrid': 'Hybrid – in person and online'}
        place = ', '.join(x for x in [e['venue'], e['street'], e['locality'], e['postcode']] if x)
        where = None if e['format'] == 'online' else (place or None)
        cost = f"{'£' if e['currency'] == 'GBP' else e['currency'] + ' '}{e['cost']:,.0f}" if e['cost'] > 0 else 'Free'
        cancelled = e['status'] == 'cancelled'
        call = e['type'] == 'Community Call'
        links = self.g.shown('events', e['slug'], e['display'])
        org = self.rec['activities'].get((links.get('activities') or [None])[0])
        speakers = [self.people_by_wp[i] for i in e['speakerIds'] if i in self.people_by_wp]

        def iso(d, tm):
            if not tm:
                return d.isoformat()
            h, m = map(int, tm.split(':'))
            return dt.datetime(d.year, d.month, d.day, h, m, tzinfo=UK).isoformat()
        ymd = lambda d: d.strftime('%Y%m%d')
        hm = lambda tm: tm.replace(':', '') + '00'
        end_d = e['end'] or e['start']
        dates = f"{ymd(e['start'])}T{hm(e['startTime'])}/{ymd(end_d)}T{hm(e['endTime'] or e['startTime'])}" if e['startTime'] else f"{ymd(e['start'])}/{ymd(end_d + dt.timedelta(days=1))}"
        cal = f"https://calendar.google.com/calendar/render?action=TEMPLATE&text={urllib.parse.quote(plain(e['title']))}&dates={dates}&ctz=Europe/London" + (f"&location={urllib.parse.quote(where)}" if where else '')
        virtual = {'@type': 'VirtualLocation', 'url': e['registration'] or f"https://elixiruknode.org/events/{e['slug']}/"}
        physical = {'@type': 'Place', 'name': e['venue'] or e['locality'] or None, 'address': {'@type': 'PostalAddress', 'streetAddress': e['street'] or None,
                    'addressLocality': e['locality'] or None, 'postalCode': e['postcode'] or None, 'addressCountry': e['country'] or 'GB'}}
        also = [x for x in self.upcoming if x['slug'] != e['slug']][:3]
        return {
            'past': past, 'cancelled': cancelled, 'stop': needs_stop(e['title']), 'image': self.img.get(e['image'], 'photo'),
            'type': t(e['type']), 'type_slug': slugify(e['type']), 'format_label': formats[e['format']], 'online': e['format'] == 'online', 'hybrid': e['format'] == 'hybrid',
            'month': f"{e['start']:%b}", 'day': str(e['start'].day), 'when': when, 'when_card': when if multi else date_parts(e['start'])['full'],
            'time': time, 'where': t(where) if where else None, 'cost': cost,
            'where_card': 'Online' if e['format'] == 'online' else (t(where) + (' and online' if e['format'] == 'hybrid' else '') if where else formats[e['format']]),
            'cta': 'Join in' if call else 'Register', 'calendar': cal, 'standfirst': t(e['standfirst']) or None,
            'registration': e['registration'], 'programme': e['programme'], 'recording': e['recording'], 'slides': e['slides'],
            'speakers': [self.person(p) for p in speakers],
            'org': org and {'href': f"/activities/{org['slug']}/", 'name': t(org['name']), 'icon': self.icon(org),
                            'sum': t(first_sentence(org['summary'])) or None, 'go': 'Find out how to join →' if org['joinLink'] else 'About this community →'},
            'tabs': self.tabs('events', e['slug'], e['display'], skip=('people',), heading='Related'),
            'also': [{'href': f"/events/{x['slug']}/", 'date': date_parts(x['start'])['long'], 'title': t(x['title']), 'type': t(x['type']) + (' · Online' if x['format'] == 'online' else '')} for x in also],
            'description': plain(e['standfirst']) or None,
            'jsonld': {
                '@context': 'https://schema.org', '@type': 'Event', 'name': plain(e['title']),
                'description': plain(e['standfirst']) or re.sub(r'\s+', ' ', plain(e['body']))[:300],
                'image': [e['image']] if e['image'] else None,
                'startDate': iso(e['start'], e['startTime']), 'endDate': iso(end_d, e['endTime'] or e['startTime']),
                'eventStatus': f"https://schema.org/{'EventCancelled' if cancelled else 'EventRescheduled' if e['status'] == 'rescheduled' else 'EventScheduled'}",
                'eventAttendanceMode': f"https://schema.org/{'OnlineEventAttendanceMode' if e['format'] == 'online' else 'MixedEventAttendanceMode' if e['format'] == 'hybrid' else 'OfflineEventAttendanceMode'}",
                'location': virtual if e['format'] == 'online' else [physical, virtual] if e['format'] == 'hybrid' else physical,
                'offers': {'@type': 'Offer', 'price': e['cost'], 'priceCurrency': e['currency'], 'url': e['registration'],
                           'availability': f"https://schema.org/{'SoldOut' if past or cancelled else 'InStock'}"},
                'organizer': {'@type': 'Organization', 'name': 'ELIXIR-UK', 'url': 'https://elixiruknode.org'},
                'performer': [{'@type': 'Person', 'name': plain(p['name'])} for p in speakers] or None,
            },
        }

    def webpage(self, pg):
        art = {'what-we-do': 'illustration-isometrics-mechanisms-working.svg', 'join-in': 'illustration-isometrics-team-rowing.svg',
               'new-members': 'illustration-isometrics-construction-robots.svg', 'data-management-planning-in-life-sciences-research': 'illustration-isometrics-data-life-cycle-dmp.svg',
               'recognition-badges': 'illustration-isometrics-training-copy-2.svg', 'call-for-services': 'illustration-isometrics-big-data-cloud.svg',
               'how-our-communities-of-practice-work': 'illustration-isometrics-team-rowing.svg'}.get(pg['slug'])
        toc = []
        for attrs, inner in re.findall(r'<h2([^>]*)>(.*?)</h2>', pg['body'], re.S):
            text = plain(inner)
            if not text or 'wp-tabs__print' in attrs:
                continue
            m = re.search(r'id="([^"]+)"', attrs)
            toc.append({'id': m.group(1) if m else slugify(text), 'text': t(text)})
        return {'art': asset(art), 'legal': pg['slug'] in ('privacy-policy', 'terms-of-use'), 'toc': toc if len(toc) >= 3 else [],
                'description': pg['description'] or None, 'jsonld': None}
