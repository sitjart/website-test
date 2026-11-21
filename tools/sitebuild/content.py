"""Loads and checks the content files (news, events, pages) and the directory records.

Each field is checked against what the site expects. A content file that is wrong
(a missing title, a date that isn't a date, an unknown event format) stops the build with
the file name, so it is fixed before the site is published rather than shown half-empty.
"""
import datetime as dt
import re

import yaml

from .common import DATA, KINDS, REPORT, ROOT, load_json, to_date

FRONT = re.compile(r'^---\n(.*?)\n---\n?(.*)$', re.S)
LINK_KINDS = set(KINDS) | {'news', 'events', 'people'}
TIME = re.compile(r'^([01]\d|2[0-3]):[0-5]\d$')


def read(path):
    m = FRONT.match(path.read_text())
    if not m:
        REPORT.error(path.relative_to(ROOT), 'no front matter (the block between --- lines at the top)')
        return None, ''
    try:
        data = yaml.safe_load(m.group(1)) or {}
    except yaml.YAMLError as e:
        REPORT.error(path.relative_to(ROOT), f'front matter is not valid YAML: {e}')
        return None, ''
    return data, m.group(2)


class Check:
    """Reads one field at a time, recording a clear error when a value is wrong."""

    def __init__(self, where, data):
        self.where, self.data = where, data

    def text(self, key, required=False, default=''):
        v = self.data.get(key)
        if v is None or v == '':
            if required:
                REPORT.error(self.where, f'"{key}" is required')
            return default
        if not isinstance(v, (str, int, float)):
            REPORT.error(self.where, f'"{key}" should be text')
            return default
        return str(v).strip()

    def date(self, key, required=False):
        v = self.data.get(key)
        if v in (None, ''):
            if required:
                REPORT.error(self.where, f'"{key}" is required (a date such as 2026-11-25)')
            return None
        try:
            return to_date(v)
        except ValueError:
            REPORT.error(self.where, f'"{key}" should be a date such as 2026-11-25, not "{v}"')
            return None

    def time(self, key):
        v = self.data.get(key)
        if v in (None, ''):
            return None
        if isinstance(v, int):          # YAML reads 09:30 as a number of minutes
            v = f'{v // 60:02d}:{v % 60:02d}'
        v = str(v).strip()
        if not TIME.match(v):
            REPORT.error(self.where, f'"{key}" should be a 24-hour time such as 09:30, not "{v}"')
            return None
        return v

    def choice(self, key, options, default):
        v = self.data.get(key, default) or default
        if v not in options:
            REPORT.error(self.where, f'"{key}" must be one of {", ".join(options)} – not "{v}"')
            return default
        return v

    def number(self, key, default=0):
        v = self.data.get(key, default)
        if v in (None, ''):
            return default
        if not isinstance(v, (int, float)):
            REPORT.error(self.where, f'"{key}" should be a number')
            return default
        return v

    def flag(self, key, default=False):
        v = self.data.get(key, default)
        return bool(v)

    def ids(self, key):
        v = self.data.get(key) or []
        if not isinstance(v, list) or not all(isinstance(x, int) for x in v):
            REPORT.error(self.where, f'"{key}" should be a list of numbers')
            return []
        return v

    def links(self, key):
        """related: / about: – a list of record slugs per kind, e.g. members: [university-of-oxford]"""
        v = self.data.get(key) or {}
        out = {}
        if not isinstance(v, dict):
            REPORT.error(self.where, f'"{key}" should list record slugs by kind, e.g. members: [university-of-oxford]')
            return out
        for kind, slugs in v.items():
            if kind not in LINK_KINDS:
                REPORT.error(self.where, f'"{key}" has an unknown kind "{kind}" (use one of {", ".join(sorted(LINK_KINDS))})')
                continue
            if isinstance(slugs, str):
                slugs = [slugs]
            out[kind] = [str(s) for s in (slugs or [])]
        return out

    def display(self):
        v = self.data.get('display') or {}
        return {'hide': list(v.get('hide') or []), 'show': list(v.get('show') or [])}


def load_news():
    out = []
    for f in sorted((ROOT / 'collections/_news').glob('*.html')):
        data, body = read(f)
        if data is None:
            continue
        c = Check(f.relative_to(ROOT), data)
        out.append({
            'slug': f.stem, 'file': str(f.relative_to(ROOT)), 'body': body,
            'title': c.text('title', required=True),
            'date': c.date('date', required=True) or dt.date(1970, 1, 1),
            'standfirst': c.text('standfirst'),
            'excerpt': c.text('excerpt'),
            'category': c.text('category', default='News'),
            'image': c.text('image') or None,
            'wpId': data.get('wpId'),
            'related': c.links('related'),
            'about': c.links('about'),
            'display': c.display(),
        })
    return out


def load_events():
    out = []
    for f in sorted((ROOT / 'collections/_events').glob('*.html')):
        data, body = read(f)
        if data is None:
            continue
        c = Check(f.relative_to(ROOT), data)
        start = c.date('start', required=True) or dt.date(1970, 1, 1)
        end = c.date('end')
        if end and end < start:
            REPORT.error(c.where, f'"end" ({end}) is before "start" ({start})')
        out.append({
            'slug': f.stem, 'file': str(f.relative_to(ROOT)), 'body': body,
            'title': c.text('title', required=True),
            'start': start, 'end': end,
            'startTime': c.time('startTime'), 'endTime': c.time('endTime'),
            'type': c.text('type', required=True, default='Event'),
            'format': c.choice('format', ['online', 'in-person', 'hybrid'], 'online'),
            'status': c.choice('status', ['scheduled', 'rescheduled', 'cancelled'], 'scheduled'),
            'standfirst': c.text('standfirst'),
            'cost': c.number('cost', 0), 'currency': c.text('currency', default='GBP'),
            'venue': c.text('venue'), 'street': c.text('street'), 'locality': c.text('locality'),
            'postcode': c.text('postcode'), 'country': c.text('country'),
            'registration': c.text('registration') or None, 'programme': c.text('programme') or None,
            'recording': c.text('recording') or None, 'slides': c.text('slides') or None,
            'image': c.text('image') or None,
            'speakerIds': c.ids('speakerIds'),
            'wpId': data.get('wpId'),
            'related': c.links('related'), 'about': c.links('about'), 'display': c.display(),
        })
    return out


def load_webpages():
    out = []
    for f in sorted((ROOT / 'collections/_webpages').glob('*.html')):
        data, body = read(f)
        if data is None:
            continue
        c = Check(f.relative_to(ROOT), data)
        out.append({'slug': f.stem, 'body': body, 'title': c.text('title', required=True), 'description': c.text('description')})
    return out


DIRECTORY_FIELDS = {'slug': str, 'name': str, 'website': str, 'logo': str, 'summary': str, 'excerpt': str, 'body': str,
                    'tags': list, 'status': str, 'joinLink': str, 'leadIds': list, 'peopleIds': list, 'related': dict}


def load_directory():
    """Directory records (services, members, projects ...). Today these are JSON files in _data/directory;
    when Baserow becomes the source, the same shape comes from its API instead."""
    out = {}
    for kind in KINDS:
        rows = load_json(DATA / 'directory' / f'{kind}.json')
        seen = set()
        for r in rows:
            where = f'_data/directory/{kind}.json [{r.get("slug", "?")}]'
            for key, typ in DIRECTORY_FIELDS.items():
                if r.get(key) is None:
                    r[key] = typ()
                elif not isinstance(r[key], typ):
                    REPORT.error(where, f'"{key}" should be {typ.__name__}')
            if r['slug'] in seen:
                REPORT.error(where, 'duplicate slug')
            seen.add(r['slug'])
            r['start'], r['end'] = to_date(r.get('start')), to_date(r.get('end'))
            r['display'] = {'hide': list((r.get('display') or {}).get('hide') or []), 'show': list((r.get('display') or {}).get('show') or [])}
            r['about'] = r.get('about') or {}
        out[kind] = rows
    return out
