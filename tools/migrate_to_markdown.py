"""One-off: convert the cleaned WordPress HTML in collections/ to Markdown. Already run; kept as a record.

- Most text becomes plain Markdown.
- Buttons become   [Label](link){: .btn}   and note panels a quote marked   {: .wp-note}
  (kramdown's attribute syntax, which the editor keeps as written).
- Accordions and tabs become blocks in the front matter (blocks: …), edited as fields in the CMS.
- Only what Markdown cannot express stays HTML: figures with captions and embedded videos.

Run from the repository root:  python3 tools/migrate_to_markdown.py
"""
import pathlib
import re

import yaml
from bs4 import BeautifulSoup, NavigableString, Tag
from markdownify import MarkdownConverter

ROOT = pathlib.Path(__file__).resolve().parent.parent
FRONT = re.compile(r'^---\n(.*?)\n---\n?(.*)$', re.S)


class Converter(MarkdownConverter):
    def convert_svg(self, el, text, *args, **kw):
        return ''                                   # decorative WordPress icons

    def convert_iframe(self, el, text, *args, **kw):
        return f'\n\n{el}\n\n'

    def convert_figure(self, el, text, *args, **kw):
        if el.find('figcaption') or el.find('iframe'):
            for img in el.find_all('img'):         # WordPress size attributes are not needed
                for a in ['class', 'srcset', 'sizes', 'decoding', 'loading', 'style']:
                    img.attrs.pop(a, None)
            return f'\n\n{el}\n\n'
        return text

    def convert_aside(self, el, text, *args, **kw):
        if 'wp-note' in (el.get('class') or []):
            inner = text.strip()
            quoted = '\n'.join('> ' + line if line else '>' for line in inner.split('\n'))
            return f'\n\n{quoted}\n{{: .wp-note}}\n\n'
        return text

    def convert_div(self, el, text, *args, **kw):
        if 'wp-block-buttons' in (el.get('class') or []):
            links = [f'[{a.get_text(strip=True)}]({a.get("href")}){{: .btn}}' for a in el.find_all('a')]
            return '\n\n' + '\n'.join(links) + '\n\n'
        return text


def md(html):
    out = Converter(heading_style='ATX', bullets='-', escape_underscores=False, escape_misc=False, strip=['span']).convert(html)
    out = re.sub(r'[ \t]+\n', '\n', out)
    out = re.sub(r'([^\n])\n(<(?:figure|iframe))', r'\1\n\n\2', out)      # HTML blocks need blank lines around them
    out = re.sub(r'(</(?:figure|iframe)>)\n([^\n])', r'\1\n\n\2', out)
    out = re.sub(r'\n{3,}', '\n\n', out)
    return out.strip()


def is_special(node):
    if not isinstance(node, Tag):
        return False
    cls = node.get('class') or []
    return 'acc-group' in cls or 'wp-tabs' in cls or (node.name == 'details' and 'acc' in cls)


def contains_special(node):
    return isinstance(node, Tag) and (is_special(node) or node.select_one('.acc-group, .wp-tabs, details.acc') is not None)


def accordion_items(nodes):
    items = []
    for d in nodes:
        if not isinstance(d, Tag) or d.name != 'details':
            continue
        summary = d.find('summary')
        body = d.select_one('.acc__body')
        items.append({'title': summary.get_text(' ', strip=True) if summary else '', 'body': md(body.decode_contents() if body else '')})
    return items


def blocks_from(nodes):
    """Walk the page in order: text between accordions and tabs becomes Markdown text blocks."""
    blocks, buffer = [], []

    def flush():
        text = md(''.join(str(n) for n in buffer))
        if text:
            blocks.append({'type': 'text', 'body': text})
        buffer.clear()

    i = 0
    nodes = list(nodes)
    while i < len(nodes):
        n = nodes[i]
        if isinstance(n, Tag) and 'acc-group' in (n.get('class') or []):
            flush()
            blocks.append({'type': 'accordion', 'items': accordion_items(n.find_all('details', recursive=False) or n.find_all('details'))})
        elif isinstance(n, Tag) and n.name == 'details' and 'acc' in (n.get('class') or []):
            flush()
            run = []
            while i < len(nodes) and (isinstance(nodes[i], NavigableString) and not nodes[i].strip() or (isinstance(nodes[i], Tag) and nodes[i].name == 'details')):
                run.append(nodes[i])
                i += 1
            blocks.append({'type': 'accordion', 'items': accordion_items(run)})
            continue
        elif isinstance(n, Tag) and 'wp-tabs' in (n.get('class') or []):
            flush()
            labels = [b.get_text(strip=True) for b in n.select('[role=tab]')]
            panels = n.select('[role=tabpanel]')
            tabs = []
            for label, p in zip(labels, panels):
                for h in p.select('.wp-tabs__print'):
                    h.decompose()
                tabs.append({'title': label, 'body': md(p.decode_contents())})
            blocks.append({'type': 'tabs', 'items': tabs})
        elif contains_special(n):
            flush()
            blocks.extend(blocks_from(n.children))   # unwrap layout containers around accordions
        else:
            buffer.append(n)
        i += 1
    flush()
    return blocks


class Literal(str):
    pass


yaml.add_representer(Literal, lambda d, s: d.represent_scalar('tag:yaml.org,2002:str', s, style='|'))


def literal(x):
    if isinstance(x, dict):
        return {k: literal(v) for k, v in x.items()}
    if isinstance(x, list):
        return [literal(v) for v in x]
    if isinstance(x, str) and '\n' in x:
        return Literal(x)
    return x


def main():
    for folder in ['_news', '_events', '_webpages']:
        for f in sorted((ROOT / 'collections' / folder).glob('*.html')):
            m = FRONT.match(f.read_text())
            front, body = m.group(1), m.group(2)
            soup = BeautifulSoup(body, 'html.parser')
            if soup.select_one('.acc-group, .wp-tabs, details.acc'):
                data = yaml.safe_load(front) or {}
                data['blocks'] = literal(blocks_from(soup.children))
                front = yaml.dump(data, allow_unicode=True, sort_keys=False, width=1000).strip()
                text = ''
            else:
                text = md(body)
            f.with_suffix('.md').write_text(f'---\n{front}\n---\n\n{text}\n' if text else f'---\n{front}\n---\n')
            f.unlink()


if __name__ == '__main__':
    main()
