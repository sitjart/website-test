"""Shared helpers: paths, settings, text and date formatting, and the build report."""
import datetime as dt
import html
import json
import os
import pathlib
import re
import unicodedata
from zoneinfo import ZoneInfo

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
DATA = ROOT / '_data'
GEN = DATA / 'gen'                    # everything this step writes for the templates (not committed)
STUBS = ROOT / 'collections'          # generated page stubs go in collections/_<kind>/ (not committed)
CONFIG = yaml.safe_load((ROOT / '_config.yml').read_text())
BASEURL = os.environ.get('BASEURL', CONFIG.get('baseurl', '') or '').rstrip('/')
UK = ZoneInfo('Europe/London')
TODAY = dt.datetime.now(UK).date()

KINDS = ['services', 'members', 'projects', 'activities', 'collaborations', 'area']


def load_json(path):
    return json.loads(pathlib.Path(path).read_text())


def write_json(path, data):
    path = pathlib.Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=None, separators=(',', ':'), default=str))


# ---------------------------------------------------------------------------
# Problems found while preparing the data.
# Errors stop the build (the site would be wrong); warnings are listed in the build summary.
# ---------------------------------------------------------------------------
class Report:
    def __init__(self):
        self.errors, self.warnings, self.notes = [], [], []

    def error(self, where, msg):
        self.errors.append(f'{where}: {msg}')

    def warn(self, where, msg):
        self.warnings.append(f'{where}: {msg}')

    def note(self, msg):
        self.notes.append(msg)


REPORT = Report()


# ---------------------------------------------------------------------------
# Text
# ---------------------------------------------------------------------------
def slugify(s: str) -> str:
    s = unicodedata.normalize('NFKD', s or '')
    s = ''.join(c for c in s if not unicodedata.combining(c))
    return re.sub(r'(^-|-$)', '', re.sub(r'[^a-z0-9]+', '-', s.lower()))


def t(s) -> str:
    """Plain text ready to print in HTML: entities decoded once, then escaped once."""
    return html.escape(html.unescape(str(s or '')), quote=True)


def plain(s) -> str:
    """Plain text without escaping, for JSON-LD and lengths."""
    return html.unescape(re.sub(r'<[^>]+>', ' ', str(s or ''))).replace('\xa0', ' ').strip()


def first_sentence(s: str, limit: int = 220) -> str:
    """First full sentence(s) of a summary, never cut mid-word."""
    s = plain(s)
    m = re.match(r'^.{20,}?[.!?](?=\s|$)', s, re.S)
    if m and len(m.group(0)) <= limit:
        return m.group(0)
    if len(s) <= limit:
        return s
    return s[: s.rfind(' ', 0, limit)] + '…'


def needs_stop(title: str) -> bool:
    """Orange full stop after display titles, unless the title already ends in punctuation."""
    return not re.search(r'[.!?…]$', plain(title))


def surname_key(name: str) -> str:
    return plain(name).split(' ')[-1].lower()


# ---------------------------------------------------------------------------
# Dates – British format, UK time
# ---------------------------------------------------------------------------
def to_date(v):
    if v is None or v == '':
        return None
    if isinstance(v, dt.datetime):
        return v.date()
    if isinstance(v, dt.date):
        return v
    return dt.date.fromisoformat(str(v)[:10])


def date_parts(d):
    """Every way the templates show a date, worked out once here."""
    if not d:
        return None
    return {
        'iso': d.isoformat(),
        'long': f'{d.day} {d:%B %Y}',                 # 14 October 2026
        'short': f'{d.day} {d:%b %Y}',                # 14 Oct 2026
        'day': str(d.day),
        'month': f'{d:%b}',
        'year': str(d.year),
        'weekday': f'{d:%a}',
        'full': f'{d:%A} {d.day} {d:%B %Y}',          # Wednesday 14 October 2026
    }
