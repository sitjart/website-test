"""One-off clean-up of HTML imported from WordPress. Already run; kept as a record.

The Astro site repeated this on every build. Doing it once, at source, means the content files
hold plain, clean HTML that the CMS can edit, and the build has nothing to repair.

What it does:
- Greenshift accordions  -> native <details class="acc"> accordions
- Greenshift tabs        -> accessible tabs (assets/js/base.js makes them work)
- animated counters      -> the final figure
- info boxes             -> <aside class="wp-note"> panels
- links to old WordPress addresses -> the new addresses; links with no page here -> the live WordPress site
- uploads already copied into assets/wp -> the local copy
- content files renamed .md -> .html, so no Markdown processor touches the HTML

Run from the repository root:  python3 tools/migrate_wordpress_html.py
"""
import json
import pathlib
import re

from bs4 import BeautifulSoup

ROOT = pathlib.Path(__file__).resolve().parent.parent
LOCAL = {p.name for p in (ROOT / 'assets/wp').iterdir()}
RENAME = {'service': 'services', 'project': 'projects', 'collaborator': 'collaborations', 'event': 'events',
          'stories': 'news', 'blog': 'news', 'uncategorized': 'news', 'news-and-stories': 'news', 'activity': 'activities'}
KINDS = ['services', 'members', 'projects', 'activities', 'collaborations', 'area']


def known_routes():
    s = {'/', '/news/', '/events/', '/people/', '/about/', '/search/'}
    for c in ['_news', '_events']:
        for f in (ROOT / 'collections' / c).iterdir():
            s.add(f'/{c[1:]}/{f.stem}/')
    for f in (ROOT / 'collections/_webpages').iterdir():
        s.add(f'/{f.stem}/')
    for k in KINDS:
        s.add(f'/{k}/')
        for r in json.loads((ROOT / f'_data/directory/{k}.json').read_text()):
            s.add(f"/{k}/{r['slug']}/")
    return s


ROUTES = known_routes()


def rebuild_widgets(html: str) -> str:
    if not re.search(r'gs-accordion-item|gspb-tabs|gs-counter|gspb_infoBox', html):
        return html
    soup = BeautifulSoup(html, 'html.parser')

    def frag(s):
        return BeautifulSoup(s, 'html.parser')

    for box in soup.select('.gspb_infoBox'):
        text = box.select_one('.gs-box-text')
        box.replace_with(frag(f'<aside class="wp-note">{text.decode_contents() if text else box.decode_contents()}</aside>'))
    for c in soup.select('.gs-counterwrap'):
        n = c.select_one('.gs-counter')
        num = (n.get('data-end') or n.get_text()) if n else ''
        label = c.select_one('.gs-counterlabel')
        c.replace_with(frag(f'<div class="wp-counter"><b>{num}</b><span>{label.decode_contents() if label else ""}</span></div>'))
    for item in soup.select('.gs-accordion-item'):
        h = item.select_one('.gs-accordion-item__heading') or item.select_one('.gs-accordion-item__title')
        title = h.decode_contents().strip() if h else ''
        b = item.select_one('.gs-accordion-item__text') or item.select_one('.gs-accordion-item__content')
        item.replace_with(frag(f'<details class="acc"><summary>{title}</summary><div class="acc__body">{b.decode_contents() if b else ""}</div></details>'))
    for box in soup.select('.gs-accordion'):
        box['class'] = ['acc-group']
    for t, tabs in enumerate(soup.select('.gspb-tabs')):
        labels = [b.get_text().strip() for b in tabs.select('.t-btn')]
        panels = []
        for p in tabs.select('.t-panel'):
            inner = p.select_one('.wp-block-greenshift-blocks-tab')
            panels.append(inner.decode_contents() if inner else p.decode_contents())
        tid = f'wpt{t}'
        nav = ''.join(f'<button type="button" role="tab" id="{tid}-t{i}" aria-controls="{tid}-p{i}" aria-selected="{"true" if i == 0 else "false"}" tabindex="{0 if i == 0 else -1}">{l}</button>' for i, l in enumerate(labels))
        body = ''.join(f'<div role="tabpanel" id="{tid}-p{i}" aria-labelledby="{tid}-t{i}" tabindex="0"{" hidden" if i else ""}><h2 class="wp-tabs__print">{labels[i] if i < len(labels) else ""}</h2>{p}</div>' for i, p in enumerate(panels))
        tabs.replace_with(frag(f'<div class="wp-tabs" data-wp-tabs><div class="wp-tabs__nav" role="tablist">{nav}</div>{body}</div>'))
    return str(soup)


LINK = re.compile(r'(href|src)="((?:https?://(?:www\.)?elixiruknode\.org)?(/[^"#?]*)?)([^"]*)"')


def fix_link(m):
    attr, full, path, rest = m.group(1), m.group(2), m.group(3), m.group(4)
    if path is None or not path.startswith('/') or path.startswith('//'):
        return m.group(0)
    if path.startswith('/wp-content/'):
        name = path.rsplit('/', 1)[-1]
        return f'{attr}="/assets/wp/{name}{rest}"' if name in LOCAL else f'{attr}="https://elixiruknode.org{path}{rest}"'
    p = path if path.endswith('/') else path + '/'
    seg = [s for s in p.split('/') if s]
    if len(seg) == 2 and seg[0] in RENAME:
        p = f'/{RENAME[seg[0]]}/{seg[1]}/'
    if len(seg) == 1 and p not in ROUTES and f'/news/{seg[0]}/' in ROUTES:
        p = f'/news/{seg[0]}/'
    # People are not stored in the repo; their pages are checked after the build instead
    if p in ROUTES or (len(seg) == 2 and seg[0] == 'people'):
        return f'{attr}="{p}{rest}"'
    return f'{attr}="https://elixiruknode.org{path}{rest}"'


def clean(html: str) -> str:
    html = rebuild_widgets(html or '')
    html = html.replace('<a class="gspb-containerlink"', '<a class="gspb-containerlink" tabindex="-1" aria-hidden="true"')
    return LINK.sub(fix_link, html)


def main():
    for c in ['_news', '_events', '_webpages']:
        for f in sorted((ROOT / 'collections' / c).glob('*.md')):
            text = f.read_text()
            m = re.match(r'(---\n.*?\n---\n)(.*)', text, re.S)
            f.with_suffix('.html').write_text(m.group(1) + clean(m.group(2)).strip() + '\n')
            f.unlink()
    for k in KINDS:
        p = ROOT / f'_data/directory/{k}.json'
        rows = json.loads(p.read_text())
        for r in rows:
            r['body'] = clean(r['body']) if r['body'] else ''
        p.write_text(json.dumps(rows, indent=1, ensure_ascii=False) + '\n')


if __name__ == '__main__':
    main()
