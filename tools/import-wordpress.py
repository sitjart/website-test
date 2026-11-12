#!/usr/bin/env python3
"""One-off import of public content from a WordPress export (WXR) into the Astro site.

Usage:  python3 -I tools/import-wordpress.py path/to/export.xml

Imports only published, public post types: news posts, events, services and members.
People records are deliberately NOT imported: they come from Baserow at build time,
and the export file itself must never be committed (it contains personal data).
Images stay on the live WordPress site for now and are referenced by URL.
"""
import html
import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

NS = {
    'wp': 'http://wordpress.org/export/1.2/',
    'content': 'http://purl.org/rss/1.0/modules/content/',
    'excerpt': 'http://wordpress.org/export/1.2/excerpt/',
}
ROOT = Path(__file__).resolve().parent.parent


def text(el, path):
    found = el.find(path, NS)
    return (found.text or '') if found is not None else ''


def meta(item):
    return {text(m, 'wp:meta_key'): text(m, 'wp:meta_value') for m in item.findall('wp:postmeta', NS)}


def clean_html(html: str) -> str:
    html = re.sub(r'<!--\s*/?wp:.*?-->', '', html, flags=re.S)  # Gutenberg block markers
    html = re.sub(r'\n{3,}', '\n\n', html)
    return html.strip()


html_lib_unescape = html.unescape


def strip_tags(html: str) -> str:
    return re.sub(r'\s+', ' ', html_lib_unescape(re.sub(r'<[^>]+>', ' ', html))).strip()


def yaml_str(s: str) -> str:
    return json.dumps(s or '', ensure_ascii=False)  # JSON strings are valid YAML


def wp_date(v: str):
    v = (v or '').strip()
    if re.fullmatch(r'\d{8}', v):
        return f'{v[:4]}-{v[4:6]}-{v[6:]}'
    return v[:10] or None


def fmt(m):
    """Event attendance mode: WordPress stored it two ways (schema.org names and short names)."""
    v = (m.get('event_format') or '').lower()
    if 'mixed' in v or 'hybrid' in v:
        return 'hybrid'
    if 'online' in v:
        return 'online'
    if 'offline' in v or 'person' in v:
        return 'in-person'
    return 'online'


def person_ids(value):
    """WordPress post IDs from an ACF relationship field. IDs only – no personal data."""
    return [int(x) for x in re.findall(r's:\d+:"(\d+)"', value or '')]


def main(src: str):
    items = ET.parse(src).getroot().find('channel').findall('item')
    attachments = {text(i, 'wp:post_id'): text(i, 'wp:attachment_url')
                   for i in items if text(i, 'wp:post_type') == 'attachment'}
    published = [i for i in items if text(i, 'wp:status') == 'publish']

    def of_type(t):
        return [i for i in published if text(i, 'wp:post_type') == t]

    def cats(item, domain):
        return [c.text for c in item.findall('category') if c.get('domain') == domain]

    # Directory types: WordPress post type -> (URL folder, data file name)
    DIRECTORY = {
        'service': 'services',
        'member': 'members',
        'project': 'projects',
        'activity': 'activities',
        'collaborator': 'collaborations',
        'thematic-area': 'area',
    }
    # Everything that can be linked to (people are deliberately excluded)
    linkable = {'post': 'news', 'event': 'events', **DIRECTORY}
    by_id = {text(i, 'wp:post_id'): (linkable[text(i, 'wp:post_type')], text(i, 'wp:post_name'))
             for i in published if text(i, 'wp:post_type') in linkable}

    def related(item):
        """Collect links to other published records from ACF relationship fields."""
        out = {}
        own = text(item, 'wp:post_id')
        for key, value in meta(item).items():
            if key.startswith('_') or not value.startswith('a:'):
                continue
            for ref in re.findall(r's:\d+:"(\d+)"', value):
                if ref in by_id and ref != own:
                    kind, slug = by_id[ref]
                    out.setdefault(kind, [])
                    if slug not in out[kind]:
                        out[kind].append(slug)
        return out

    def related_yaml(rel):
        lines = []
        if rel:
            lines.append('related:')
            for kind, slugs in sorted(rel.items()):
                lines.append(f'  {kind}: {json.dumps(slugs)}')
        return lines

    def reset(folder):
        folder.mkdir(parents=True, exist_ok=True)
        for old in folder.glob('*.md'):
            old.unlink()
        return folder

    # ---- News ----
    news_dir = reset(ROOT / 'src/content/news')
    for i in of_type('post'):
        m = meta(i)
        body = clean_html(text(i, 'content:encoded'))
        standfirst = m.get('additional_content_post_subtitle') or text(i, 'excerpt:encoded') or strip_tags(body)[:220]
        fm = [
            f'title: {yaml_str(html.unescape(text(i, "title")))}',
            f'date: {text(i, "wp:post_date")[:10]}',
            f'standfirst: {yaml_str(strip_tags(standfirst))}',
            f'excerpt: {yaml_str(strip_tags(text(i, "excerpt:encoded")))}',
            f'category: {yaml_str((cats(i, "category") or ["News"])[0])}',
            f'wpId: {text(i, "wp:post_id")}',
        ]
        if attachments.get(m.get('_thumbnail_id', '')):
            fm.append(f'image: {yaml_str(attachments[m["_thumbnail_id"]])}')
        fm += related_yaml(related(i))
        (news_dir / f'{text(i, "wp:post_name")}.md').write_text('---\n' + '\n'.join(fm) + '\n---\n\n' + body + '\n', encoding='utf8')

    # ---- Events ----
    ev_dir = reset(ROOT / 'src/content/events')
    for i in of_type('event'):
        m = meta(i)
        fm = [
            f'title: {yaml_str(html.unescape(text(i, "title")))}',
            f'start: {wp_date(m.get("event_start_date"))}',
            f'type: {yaml_str((cats(i, "type-of-event") or ["Event"])[0])}',
            f'online: {"true" if fmt(m) == "online" else "false"}',
            f'format: {fmt(m)}',
            f'wpId: {text(i, "wp:post_id")}',
        ]
        if text(i, 'excerpt:encoded').strip():
            fm.append(f'standfirst: {yaml_str(strip_tags(text(i, "excerpt:encoded")))}')
        cost = (m.get('event_cost') or '').strip()
        fm.append(f'cost: {cost if cost.replace(".", "").isdigit() else 0}')
        fm.append(f'currency: {yaml_str(m.get("event_currency") or "GBP")}')
        status = 'cancelled' if m.get('event_cancelled') in ('1', 'true') or 'Cancelled' in m.get('event_status', '') else 'rescheduled' if 'Rescheduled' in m.get('event_status', '') else 'scheduled'
        fm.append(f'status: {status}')
        for key, field in (('event_street', 'street'), ('post_code', 'postcode'), ('event_country', 'country'), ('programme_link', 'programme')):
            if m.get(key, '').strip():
                fm.append(f'{field}: {yaml_str(m[key].strip())}')
        speakers = re.findall(r's:\d+:"(\d+)"', m.get('event_node_speakers', ''))
        if speakers:
            fm.append(f'speakerIds: {json.dumps([int(x) for x in speakers])}')
        if wp_date(m.get('event_end_date')):
            fm.append(f'end: {wp_date(m.get("event_end_date"))}')
        for key, field in (('event_start_time', 'startTime'), ('event_end_time', 'endTime'),
                           ('event_venue_name', 'venue'), ('event_locality', 'locality'),
                           ('registration_link', 'registration'), ('event_recording', 'recording'),
                           ('event_slides', 'slides')):
            if m.get(key):
                fm.append(f'{field}: {yaml_str(m[key][:5] if "time" in key else m[key])}')
        if attachments.get(m.get('_thumbnail_id', '')):
            fm.append(f'image: {yaml_str(attachments[m["_thumbnail_id"]])}')
        fm += related_yaml(related(i))
        body = clean_html(text(i, 'content:encoded'))
        (ev_dir / f'{text(i, "wp:post_name")}.md').write_text('---\n' + '\n'.join(fm) + '\n---\n\n' + body + '\n', encoding='utf8')

    # ---- Pages (About, What we do, Join in ...) ----
    skip_pages = {'home', 'test-2', 'job-test', 'events', 'news-and-stories'}
    page_dir = ROOT / 'src/content/pages'
    page_dir.mkdir(parents=True, exist_ok=True)
    for old in page_dir.glob('*.md'):
        if old.stem != 'home':
            old.unlink()
    page_count = 0
    for i in of_type('page'):
        slug = text(i, 'wp:post_name')
        if slug in skip_pages:
            continue
        fm = [f'title: {yaml_str(html.unescape(text(i, "title")))}']
        body = clean_html(text(i, 'content:encoded'))
        (page_dir / f'{slug}.md').write_text('---\n' + '\n'.join(fm) + '\n---\n\n' + body + '\n', encoding='utf8')
        page_count += 1

    # ---- Directory records (stand-ins until they come from Baserow) ----
    def record(i):
        m = meta(i)
        tags = [c.text for c in i.findall('category') if c.get('domain') not in ('category', 'post_tag')]
        body = clean_html(text(i, 'content:encoded')) or (
            f'<p>{html.escape(strip_tags(m.get("description", "")))}</p>' if m.get('description') else '')
        logo = (attachments.get(m.get('logo', '')) or attachments.get(m.get('organisation_logo', ''))
                or attachments.get(m.get('_thumbnail_id', '')) or '')
        rec = {
            'wpId': int(text(i, 'wp:post_id')),
            'slug': text(i, 'wp:post_name'),
            'name': html.unescape(text(i, 'title')),
            'website': m.get('website') or m.get('project_website') or m.get('organisation_website') or '',
            'logo': logo,
            'summary': strip_tags(text(i, 'excerpt:encoded')) or strip_tags(m.get('description', '')) or strip_tags(body)[:200],
            'excerpt': strip_tags(text(i, 'excerpt:encoded')),
            'body': body,
            'tags': tags,
            'status': (cats(i, 'status-of-service') or [''])[0],
            'start': wp_date(m.get('start_date') or m.get('year_membership_started') or m.get('year_service_selected')),
            'end': wp_date(m.get('end_date')),
            'joinLink': m.get('activity_join_in', ''),
            'leadIds': person_ids(m.get('activity_leads')),
            'peopleIds': person_ids(m.get('activity_related_people') or m.get('project_related_people') or m.get('service_related_people') or m.get('member_related_people')),
            'related': related(i),
        }
        return rec

    data_dir = ROOT / 'src/data/directory'
    data_dir.mkdir(parents=True, exist_ok=True)
    counts = {}
    for wp_type, name in DIRECTORY.items():
        recs = sorted((record(i) for i in of_type(wp_type)), key=lambda r: r['name'].lower())
        (data_dir / f'{name}.json').write_text(json.dumps(recs, indent=1, ensure_ascii=False) + '\n', encoding='utf8')
        counts[name] = len(recs)

    # WordPress post ID -> [kind, slug], used to resolve people's relationships at build time
    (ROOT / 'src/data/wp-ids.json').write_text(json.dumps({k: list(v) for k, v in by_id.items()}, indent=0) + '\n', encoding='utf8')

    print(f'news: {len(of_type("post"))}, events: {len(of_type("event"))}, pages: {page_count}, ' +
          ', '.join(f'{k}: {v}' for k, v in counts.items()))


if __name__ == '__main__':
    main(sys.argv[1])
