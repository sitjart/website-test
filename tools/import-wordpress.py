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


def main(src: str):
    items = ET.parse(src).getroot().find('channel').findall('item')
    attachments = {text(i, 'wp:post_id'): text(i, 'wp:attachment_url')
                   for i in items if text(i, 'wp:post_type') == 'attachment'}
    published = [i for i in items if text(i, 'wp:status') == 'publish']

    def of_type(t):
        return [i for i in published if text(i, 'wp:post_type') == t]

    def cats(item, domain):
        return [c.text for c in item.findall('category') if c.get('domain') == domain]

    # ---- News ----
    news_dir = ROOT / 'src/content/news'
    news_dir.mkdir(parents=True, exist_ok=True)
    for old in news_dir.glob('*.md'):
        old.unlink()
    for i in of_type('post'):
        m = meta(i)
        body = clean_html(text(i, 'content:encoded'))
        standfirst = m.get('additional_content_post_subtitle') or text(i, 'excerpt:encoded') or strip_tags(body)[:220]
        fm = [
            f'title: {yaml_str(html.unescape(text(i, "title")))}',
            f'date: {text(i, "wp:post_date")[:10]}',
            f'standfirst: {yaml_str(strip_tags(standfirst))}',
            f'category: {yaml_str((cats(i, "category") or ["News"])[0])}',
        ]
        if attachments.get(m.get('_thumbnail_id', '')):
            fm.append(f'image: {yaml_str(attachments[m["_thumbnail_id"]])}')
        (news_dir / f'{text(i, "wp:post_name")}.md').write_text('---\n' + '\n'.join(fm) + '\n---\n\n' + body + '\n', encoding='utf8')

    # ---- Events ----
    ev_dir = ROOT / 'src/content/events'
    ev_dir.mkdir(parents=True, exist_ok=True)
    for old in ev_dir.glob('*.md'):
        old.unlink()
    for i in of_type('event'):
        m = meta(i)
        fm = [
            f'title: {yaml_str(html.unescape(text(i, "title")))}',
            f'start: {wp_date(m.get("event_start_date"))}',
            f'type: {yaml_str((cats(i, "type-of-event") or ["Event"])[0])}',
            f'online: {"true" if m.get("event_format") == "OnlineEventAttendanceMode" else "false"}',
        ]
        if wp_date(m.get('event_end_date')):
            fm.append(f'end: {wp_date(m.get("event_end_date"))}')
        for key, field in (('event_start_time', 'startTime'), ('event_end_time', 'endTime'),
                           ('event_venue_name', 'venue'), ('event_locality', 'locality'),
                           ('registration_link', 'registration')):
            if m.get(key):
                fm.append(f'{field}: {yaml_str(m[key][:5] if "time" in key else m[key])}')
        if attachments.get(m.get('_thumbnail_id', '')):
            fm.append(f'image: {yaml_str(attachments[m["_thumbnail_id"]])}')
        body = clean_html(text(i, 'content:encoded'))
        (ev_dir / f'{text(i, "wp:post_name")}.md').write_text('---\n' + '\n'.join(fm) + '\n---\n\n' + body + '\n', encoding='utf8')

    # ---- Services and members (stand-ins until they come from Baserow) ----
    def org(i):
        m = meta(i)
        return {
            'slug': text(i, 'wp:post_name'),
            'name': html.unescape(text(i, 'title')),
            'website': m.get('website', ''),
            'logo': attachments.get(m.get('logo', '')) or attachments.get(m.get('organisation_logo', '')) or '',
            'description': strip_tags(m.get('description', '')),
            'status': (cats(i, 'status-of-service') or [''])[0],
        }

    data_dir = ROOT / 'src/data'
    services = sorted((org(i) for i in of_type('service')), key=lambda s: s['name'].lower())
    members = sorted((org(i) for i in of_type('member')), key=lambda s: s['name'].lower())
    (data_dir / 'services.json').write_text(json.dumps(services, indent=2, ensure_ascii=False) + '\n', encoding='utf8')
    (data_dir / 'members.json').write_text(json.dumps(members, indent=2, ensure_ascii=False) + '\n', encoding='utf8')

    print(f'news: {len(of_type("post"))}, events: {len(of_type("event"))}, '
          f'services: {len(services)}, members: {len(members)}')


if __name__ == '__main__':
    main(sys.argv[1])
