"""People are never stored in this repository. At build time they come from:
  1. Baserow, when BASEROW_TOKEN is set – the long-term source, consent-gated;
  2. otherwise the live WordPress REST API – published profiles only (the current
     Baserow -> WordPress sync already gates them on consent);
  3. otherwise (working offline) the invented sample people in tools/sample/people.json.
"""
import json
import os
import re
import urllib.error
import urllib.request

from .common import DATA, REPORT, ROOT, load_json, plain, slugify

WP = os.environ.get('WP_URL', 'https://elixiruknode.org')
NAME_FIX = {'Management Cmte': 'Management Committee', 'Steering Cmte': 'Steering Committee'}
RELATED_KEYS = ['people_related_member', 'people_related_organisation', 'people_related_projects',
                'people_related_activities', 'people_related_services', 'people_related_posts', 'people_related_events']


def _get(url):
    req = urllib.request.Request(url, headers={'User-Agent': 'elixir-uk-site-build'})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode())


def _ids(v):
    if v in ('', None):
        return []
    v = v if isinstance(v, list) else [v]
    return [str(x['ID'] if isinstance(x, dict) and 'ID' in x else x) for x in v]


def _terms(tax):
    try:
        return {t['id']: NAME_FIX.get(t['name'], t['name'].replace('&amp;', '&')) for t in _get(f'{WP}/wp-json/wp/v2/{tax}?per_page=100&_fields=id,name')}
    except Exception:
        return {}


def from_wordpress(directory):
    corrections = load_json(DATA / 'corrections.json')
    removed_leads = corrections.get('removeLeads', {})
    removed_gov = corrections.get('removeGovernance', {})
    wp_ids = load_json(DATA / 'wp-ids.json')
    member_name = {m['slug']: m['name'] for m in directory['members']}
    collab_name = {m['slug']: m['name'] for m in directory['collaborations']}
    gov_t, status_t = _terms('governance-role'), _terms('people-status')
    out = []
    for page in range(1, 20):
        url = (f'{WP}/wp-json/wp/v2/people?per_page=100&page={page}&_embed=wp:featuredmedia'
               '&_fields=id,slug,title,content,acf,class_list,governance-role,people-status,_links,_embedded')
        try:
            rows = _get(url)
        except urllib.error.HTTPError as e:
            if e.code == 400:   # past the last page
                break
            raise
        for r in rows:
            acf = r.get('acf') or {}
            related = {}
            for key in RELATED_KEYS:
                for i in _ids(acf.get(key)):
                    hit = wp_ids.get(i)
                    if hit and hit[1] not in related.setdefault(hit[0], []):
                        related[hit[0]].append(hit[1])
            member, collab = (related.get('members') or [None])[0], (related.get('collaborations') or [None])[0]
            media = ((r.get('_embedded') or {}).get('wp:featuredmedia') or [{}])[0]
            leads = [wp_ids[i][1] for i in _ids(acf.get('people_activity_leadership')) if wp_ids.get(i, [None])[0] == 'activities']
            gov = [gov_t[i] for i in r.get('governance-role') or [] if i in gov_t]
            status = next((status_t[i] for i in r.get('people-status') or [] if i in status_t), '')
            slug = r['slug']
            out.append({
                'id': slug, 'wpId': r['id'],
                'honorific': plain(acf.get('title')),
                'name': re.sub(r'^(Dr|Prof|Professor)\.?\s+', '', plain((r.get('title') or {}).get('rendered')), flags=re.I),
                'leads': [a for a in leads if slug not in removed_leads.get(a, [])],
                'email': acf.get('email') or None,
                'role': plain(acf.get('uk_node_role')),
                'institution': member_name.get(member) or collab_name.get(collab) or '',
                'institutionSlug': member or collab,
                'institutionKind': 'members' if member else 'collaborations' if collab else None,
                'bio': re.sub(r'\s+', ' ', plain(acf.get('people_description') or (r.get('content') or {}).get('rendered'))),
                'orcid': acf.get('orcid_id') or None,
                'website': acf.get('website') or None,
                'linkedin': acf.get('linkedin_account') or None,
                'photo': ((media.get('media_details') or {}).get('sizes') or {}).get('medium', {}).get('source_url') or media.get('source_url'),
                'governance': [g for g in gov if slug not in removed_gov.get(g, [])],
                'status': status,
                'related': related,
            })
        if len(rows) < 100:
            break
    return out


def from_sample():
    rows = load_json(ROOT / 'tools/sample/people.json')
    sel = lambda v: v.get('value') if isinstance(v, dict) else v
    out = []
    for r in rows:
        if sel(r.get('Website status')) != 'Consent given':
            continue
        name = f"{r['First name']} {r['Last name']}"
        out.append({
            'id': slugify(name), 'wpId': None, 'honorific': r.get('Title') or '', 'name': name, 'leads': [],
            'email': None, 'role': r.get('Job title') or '', 'institution': r.get('Institution') or '',
            'institutionSlug': None, 'institutionKind': None, 'bio': r.get('Bio') or '',
            'orcid': r.get('ORCID') or None, 'website': r.get('Website') or None, 'linkedin': r.get('LinkedIn') or None,
            'photo': r.get('Photo URL') or None,
            'governance': [sel(g) for g in r.get('Governance roles') or []],
            'status': 'Current member', 'related': r.get('Related') or {},
        })
    return out


def load_people(directory):
    source = os.environ.get('PEOPLE_SOURCE', 'wordpress')
    if os.environ.get('BASEROW_TOKEN'):
        REPORT.warn('people', 'BASEROW_TOKEN is set but reading people from Baserow is not wired up yet; using WordPress')
    if source != 'sample':
        try:
            people = from_wordpress(directory)
            if people:
                REPORT.note(f'{len(people)} published profiles from WordPress')
                return people
        except Exception as e:  # network down, WordPress down
            if os.environ.get('CI'):
                # On the real build a missing people list would publish a site with no people: stop instead.
                REPORT.error('people', f'WordPress could not be reached ({e}); the site was not published')
                return []
            REPORT.warn('people', f'WordPress not reachable ({e}); using the invented sample people')
    people = from_sample()
    REPORT.note(f'{len(people)} sample people (invented, for local work)')
    return people


def is_current(p):
    """Who appears in lists: not alumni; collaborators only if they hold a governance role (e.g. SIAB).
    Everyone keeps their own profile page."""
    return p['status'] != 'Alumni' and (p['status'] != 'Collaborator' or len(p['governance']) > 0)
