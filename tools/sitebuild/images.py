"""Image resizing. Every photo or logo the templates show goes through here.

Photos are downloaded once (cached in .cache/images), resized and converted to WebP in assets/img,
and given their real width and height, so the browser keeps their proportions and nothing is squashed.
SVGs and files already copied into assets/wp are served as they are.
If an image cannot be fetched, the original address is used and the problem is listed in the build summary.
"""
import concurrent.futures as cf
import hashlib
import pathlib
import re
import urllib.request

from PIL import Image

from .common import REPORT, ROOT

CACHE = ROOT / '.cache/images'
OUT = ROOT / 'assets/img'
LOCAL_WP = ROOT / 'assets/wp'
SIZES = {               # name: (small width, large width)
    'photo': (640, 1600),
    'person': (160, 440),
    'logo': (400, 800),
}
_local_names = {p.name for p in LOCAL_WP.iterdir()} if LOCAL_WP.exists() else set()


def local_asset(src):
    """A WordPress upload that has been copied into assets/wp -> its local address."""
    if not src:
        return src
    m = re.search(r'elixiruknode\.org/wp-content/uploads/.+/([^/?#]+)$', src)
    if m and m.group(1) in _local_names:
        return f'/assets/wp/{m.group(1)}'
    return src


class Images:
    def __init__(self):
        self.jobs = {}          # (src, kind) -> placeholder dict, filled in by process()

    def get(self, src, kind='photo'):
        """Returns {'small': {src, w, h}, 'large': {src, w, h}} – filled in once process() has run."""
        if not src:
            return None
        key = (src, kind)
        if key not in self.jobs:
            self.jobs[key] = {'small': {'src': src, 'w': None, 'h': None}, 'large': {'src': src, 'w': None, 'h': None}}
        return self.jobs[key]

    def process(self):
        OUT.mkdir(parents=True, exist_ok=True)
        CACHE.mkdir(parents=True, exist_ok=True)
        with cf.ThreadPoolExecutor(max_workers=8) as pool:
            list(pool.map(lambda item: self._one(*item), self.jobs.items()))
        REPORT.note(f'{len(self.jobs)} images prepared')

    def _one(self, key, slot):
        src, kind = key
        local = local_asset(src)
        if local.lower().endswith('.svg') or (local != src):
            # SVGs and repo copies: served as they are; rasters get their real size
            for v in ('small', 'large'):
                slot[v]['src'] = local
            path = ROOT / local.lstrip('/')
            if not local.lower().endswith('.svg') and path.exists():
                with Image.open(path) as im:
                    for v in ('small', 'large'):
                        slot[v]['w'], slot[v]['h'] = im.size
            return
        if src.startswith('/'):
            original = ROOT / src.lstrip('/')
            if not original.exists():
                REPORT.error(src, 'image file not found in the repository')
                return
        else:
            original = CACHE / hashlib.sha1(src.encode()).hexdigest()
            if not original.exists():
                try:
                    req = urllib.request.Request(src, headers={'User-Agent': 'elixir-uk-site-build'})
                    with urllib.request.urlopen(req, timeout=30) as r:
                        original.write_bytes(r.read())
                except Exception as e:
                    REPORT.warn(src, f'image could not be downloaded ({e}); using the original address')
                    return
        try:
            with Image.open(original) as im:
                im.load()
                if im.mode not in ('RGB', 'RGBA'):
                    im = im.convert('RGBA')
                name = hashlib.sha1(f'{src}'.encode()).hexdigest()[:16]
                for v, width in zip(('small', 'large'), SIZES[kind]):
                    w = min(width, im.width)
                    h = round(im.height * w / im.width)
                    out = OUT / f'{name}-{w}.webp'
                    if not out.exists():
                        im.resize((w, h), Image.LANCZOS).save(out, 'WEBP', quality=78, method=5)
                    slot[v] = {'src': f'/assets/img/{out.name}', 'w': w, 'h': h}
        except Exception as e:
            REPORT.warn(src, f'image could not be read ({e}); using the original address')
