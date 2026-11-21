"""Step 1 of the build: get the data ready for Jekyll.

    python3 tools/prepare.py

Reads the content files, the directory records and the people; checks them; builds the
knowledge graph; resizes images; and writes:
  _data/gen/*.json           – what every page shows (the templates only print this)
  collections/_<kind>/*.md   – one small stub per generated page (members, services, people ...)
Nothing it writes is committed: it is rebuilt from the sources every time.

If anything is wrong in the content, it stops with a list of what to fix, and nothing is published.
Problems that don't stop the build (a link to a record that no longer exists, an image that
couldn't be downloaded) are listed as warnings in the build summary.
"""
import json
import os
import shutil
import sys

from sitebuild.common import BASEURL, GEN, KINDS, REPORT, ROOT, STUBS, first_sentence, plain, slugify, write_json
from sitebuild.content import load_directory, load_events, load_news, load_webpages
from sitebuild.graph import Graph
from sitebuild.images import Images
from sitebuild.people import load_people
from sitebuild.views import Views

GENERATED = {          # stub folder -> layout
    'members': 'member', 'services': 'record', 'projects': 'record', 'collaborations': 'record', 'area': 'record',
    'activities': 'activity', 'people': 'person', 'newscats': 'news-list', 'eventtypes': 'event-list',
}


def stub(folder, slug, layout, title):
    path = STUBS / f'_{folder}' / f'{slug}.md'
    path.write_text(f'---\nlayout: {layout}\ntitle: {json.dumps(plain(title), ensure_ascii=False)}\ngen: {folder}\nslug: {json.dumps(slug)}\n---\n')


def main():
    directory = load_directory()
    news, events, pages = load_news(), load_events(), load_webpages()
    people = load_people(directory)
    if REPORT.errors:
        return finish()

    graph = Graph(directory, news, events, people)
    images = Images()
    v = Views(directory, news, events, people, pages, graph, images)
    stats = v.stats()

    out = {'site': {'header': v.header(), 'map': v.ukmap(), 'orbit': v.orbit(), 'stats': stats, 'baseurl': BASEURL}}
    out['pages'] = {
        'home': v.home(stats), 'about': v.about(stats), 'activities': v.activities_index(), 'services': v.services_index(),
        'people': v.people_index(), 'news': v.news_list(news), 'events': v.event_list(events),
        **{k: v.directory_list(k) for k in ['members', 'projects', 'collaborations', 'area']},
    }
    for vm in out['pages'].values():
        vm.setdefault('description', None)
        vm.setdefault('jsonld', None)
    out['pages']['home']['description'] = plain(out['pages']['home']['intro'])

    for folder in GENERATED:
        shutil.rmtree(STUBS / f'_{folder}', ignore_errors=True)
        (STUBS / f'_{folder}').mkdir(parents=True)

    def describe(r):
        return plain(r['excerpt'] or first_sentence(r['summary'])) or None

    out['members'] = {}
    for r in directory['members']:
        vm = v.member(r)
        vm['description'] = plain(r['summary']) or f"{plain(r['name'])}, an ELIXIR-UK member organisation"
        out['members'][r['slug']] = vm
        stub('members', r['slug'], 'member', r['name'])
    for kind in ['services', 'projects', 'collaborations', 'area']:
        out[kind] = {}
        for r in directory[kind]:
            vm = v.record(kind, r)
            vm['description'] = describe(r)
            out[kind][r['slug']] = vm
            stub(kind, r['slug'], 'record', r['name'])
    out['activities'] = {}
    for r in directory['activities']:
        vm = v.activity(r)
        vm['description'] = describe(r)
        vm['jsonld'] = {'@context': 'https://schema.org', '@type': 'Organization', 'name': plain(r['name']), 'description': describe(r),
                        'logo': r['logo'] or None, 'parentOrganization': {'@type': 'Organization', 'name': 'ELIXIR-UK'}}
        out['activities'][r['slug']] = vm
        stub('activities', r['slug'], 'activity', r['name'])
    out['people'] = {}
    for p in people:
        vm = v.person_page(p)
        vm['description'] = ', '.join(x for x in [plain(p['role']), plain(p['institution'])] if x) or None
        out['people'][p['id']] = vm
        stub('people', p['id'], 'person', f"{p['honorific']} {p['name']}".strip())
    out['news'] = {n['slug']: v.story(n) for n in news}
    out['events'] = {e['slug']: v.event(e) for e in events}
    out['webpages'] = {pg['slug']: v.webpage(pg) for pg in pages}
    out['newscats'], out['eventtypes'] = {}, {}
    for cat in sorted({n['category'] for n in news}):
        slug = slugify(cat)
        out['newscats'][slug] = {**v.news_list([n for n in news if n['category'] == cat]), 'name': cat, 'description': None, 'jsonld': None}
        stub('newscats', slug, 'news-list', cat)
    for typ in sorted({e['type'] for e in events}):
        slug = slugify(typ)
        out['eventtypes'][slug] = {**v.event_list([e for e in events if e['type'] == typ]), 'name': typ, 'description': None, 'jsonld': None}
        stub('eventtypes', slug, 'event-list', typ)

    images.process()
    write_json(ROOT / 'assets/cms-index.json', v.cms_index())

    def drop_empty(x):
        # JSON-LD: leave out empty values rather than printing null
        if isinstance(x, dict):
            return {k: drop_empty(v) for k, v in x.items() if v not in (None, [], '')}
        if isinstance(x, list):
            return [drop_empty(v) for v in x]
        return x
    for group in out.values():
        for vm in group.values():
            if isinstance(vm, dict) and vm.get('jsonld'):
                vm['jsonld'] = drop_empty(vm['jsonld'])
    shutil.rmtree(GEN, ignore_errors=True)
    for name, data in out.items():
        write_json(GEN / f'{name}.json', data)
    REPORT.note(f"{len(news)} stories, {len(events)} events, {len(pages)} pages, {sum(len(directory[k]) for k in KINDS)} directory records, {len(people)} people")
    return finish()


def finish():
    lines = ['## Data step']
    lines += [f'- {n}' for n in REPORT.notes]
    if REPORT.errors:
        lines += ['', f'### {len(REPORT.errors)} problems to fix – nothing was published', *[f'- {e}' for e in REPORT.errors]]
    if REPORT.warnings:
        lines += ['', f'### {len(REPORT.warnings)} warnings', *[f'- {w}' for w in REPORT.warnings]]
    text = '\n'.join(lines) + '\n'
    print(text)
    if os.environ.get('GITHUB_STEP_SUMMARY'):
        with open(os.environ['GITHUB_STEP_SUMMARY'], 'a') as f:
            f.write(text)
    return 1 if REPORT.errors else 0


if __name__ == '__main__':
    sys.path.insert(0, str(ROOT / 'tools'))
    sys.exit(main())
