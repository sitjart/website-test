"""Step 3 of the build, after Jekyll: finish the pages and check them.

    python3 tools/finish.py

1. Adds the site's base path to internal links (only needed on the test address, /website-test/).
   Templates and content write plain addresses such as /news/my-story/.
2. Stamps stylesheet and script addresses with the build number, so visitors get the new versions.
   Gives every <h2> an id, so "On this page" links and shared #links work.
3. Replaces WordPress counters ([member_counter] …) with today's figures.
4. Builds the search index (Pagefind).
5. Checks every internal link and image in the built site:
   - a broken link made by a template stops the build – nothing is published;
   - a broken link inside text written in the CMS is listed as a warning, so it can be fixed in the content.
"""
import json
import os
import pathlib
import re
import subprocess
import sys
from collections import defaultdict

from bs4 import BeautifulSoup

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from sitebuild.common import BASEURL, GEN, ROOT, plain, slugify  # noqa: E402

SITE = ROOT / '_site'
ATTR = re.compile(r'\b(href|src|poster|action)="(/(?!/)[^"]*)"')
H2 = re.compile(r'<h2(?![^>]*\sid=)([^>]*)>(.*?)</h2>', re.S)


VERSION = os.environ.get('GITHUB_RUN_ID') or str(int(__import__('time').time()))


def finish_page(html, stats):
    # A new address for the stylesheet and scripts on every build, so browsers don't keep an old copy
    html = re.sub(r'((?:href|src)="/assets/(?:css|js)/[^"?]+)"', rf'\1?v={VERSION}"', html)
    if BASEURL:
        html = ATTR.sub(lambda m: m.group(0) if m.group(2).startswith(BASEURL + '/') else f'{m.group(1)}="{BASEURL}{m.group(2)}"', html)
    html = H2.sub(lambda m: f'<h2{m.group(1)} id="{slugify(plain(m.group(2)))}">{m.group(2)}</h2>' if plain(m.group(2)) else m.group(0), html)
    for code, key in [('member_counter', 'members'), ('people_counter', 'people'), ('service_counter', 'services'), ('project_counter', 'projects')]:
        html = html.replace(f'[{code}]', f'<span class="wp-stat">{stats[key]}</span>')
    return html


def target_exists(path):
    path = path.split('#')[0].split('?')[0]  # ignores ?v= build stamps
    if BASEURL and path.startswith(BASEURL + '/'):
        path = path[len(BASEURL):]
    f = SITE / path.lstrip('/')
    return f.is_file() or (f / 'index.html').is_file()


def main():
    stats = json.loads((GEN / 'site.json').read_text())['stats']
    pages = sorted(SITE.rglob('*.html'))
    for p in pages:
        p.write_text(finish_page(p.read_text(), stats))

    subprocess.run([sys.executable, '-m', 'pagefind', '--site', str(SITE)], check=True)

    errors, warnings = defaultdict(set), defaultdict(set)
    leftovers = []
    for p in pages:
        if p.is_relative_to(SITE / 'pagefind'):
            continue
        html = p.read_text()
        page = '/' + str(p.relative_to(SITE)).replace('index.html', '')
        soup = BeautifulSoup(html, 'lxml')
        if re.search(r'Liquid (syntax )?error|\{\{|\{%', soup.get_text()):
            leftovers.append(page)
        for el in soup.select('a[href], img[src], link[href], script[src]'):
            url = (el.get('href') if el.name in ('a', 'link') else el.get('src')) or ''
            if url.strip() == '':
                (warnings if el.find_parent(attrs={'data-content': True}) else errors)['(empty link)'].add(page)
                continue
            if not url.startswith('/') or url.startswith('//') or url.startswith(f'{BASEURL}/pagefind/') or url.startswith('/pagefind/'):
                continue
            if target_exists(url):
                continue
            bucket = warnings if el.find_parent(attrs={'data-content': True}) else errors
            bucket[url].add(page)

    lines = ['## Checks on the built site', f'- {len(pages)} pages checked']
    if leftovers:
        lines += ['', '### Unprocessed template code on these pages', *[f'- {x}' for x in leftovers]]
    if errors:
        lines += ['', f'### {len(errors)} broken links made by templates – nothing was published',
                  *[f'- {u} (on {", ".join(sorted(ps)[:3])}{" …" if len(ps) > 3 else ""})' for u, ps in sorted(errors.items())]]
    if warnings:
        lines += ['', f'### {len(warnings)} broken links inside content written in the CMS – please fix',
                  *[f'- {u} (on {", ".join(sorted(ps)[:3])}{" …" if len(ps) > 3 else ""})' for u, ps in sorted(warnings.items())]]
    text = '\n'.join(lines) + '\n'
    print(text)
    if os.environ.get('GITHUB_STEP_SUMMARY'):
        with open(os.environ['GITHUB_STEP_SUMMARY'], 'a') as f:
            f.write(text)
    return 1 if errors or leftovers else 0


if __name__ == '__main__':
    sys.exit(main())
