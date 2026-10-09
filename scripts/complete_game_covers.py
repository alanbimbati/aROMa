"""Give every game of the catalogue a picture: Steam box art for the PC ones, a title card for what no database knows.

    python scripts/complete_game_covers.py [--no-steam] [--retry-generated]

Runs after fetch_game_covers.py and only touches games that have no cover yet. The Steam match must be close
(a wrong cover is worse than none). Ports of PC games on other consoles (Switch, PS3, PS4) use the same Steam art when
the title matches, with --retry-generated looking again at games that only had a generated card. Whatever stays unmatched gets a generated card in the colour of its platform,
recorded as 'generated' in data/games_covers.csv so it can be replaced when a real picture turns up.
"""
import csv
import difflib
import io
import json
import os
import re
import sys
import textwrap
import unicodedata
import urllib.parse
import urllib.request

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
from PIL import Image, ImageDraw, ImageFont  # noqa: E402

CATALOG = os.path.join(BASE_DIR, 'data', 'games_catalog.csv')
OUT_DIR = os.path.join(BASE_DIR, 'cache', 'game_covers')
INDEX = os.path.join(BASE_DIR, 'data', 'games_covers.csv')
SEARCH = 'https://store.steampowered.com/api/storesearch/?l=english&cc=us&term='
ART = 'https://shared.akamai.steamstatic.com/store_item_assets/steam/apps/%d/%s'
FONT = '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
PORTS = {'Switch', 'PS3', 'PS4'}
COLOUR = {'PS1': '#5b606b', 'PS2': '#1b2a6b', 'PS3': '#23262e', 'PS4': '#0b3d91', 'PSP': '#59606e', 'Nintendo DS': '#6d6d6d',
          'Nintendo 3DS': '#c8102e', 'Game Boy Advance': '#4b2e83', 'GameCube': '#4c3b8f', 'Wii': '#3a8fb7', 'Switch': '#e60012',
          'SNES': '#7d7aa8', 'PC': '#2f3a4a', 'PC (DOS)': '#2f3a4a', 'Xbox': '#107c10', 'Xbox 360': '#4d8a00'}


def norm(title):
    t = unicodedata.normalize('NFKD', title).encode('ascii', 'ignore').decode().lower()
    return re.sub(r'\s+', ' ', re.sub(r'[^a-z0-9]+', ' ', t)).strip()


def steam_cover(title):
    """Image bytes of the best Steam match for this title, or None."""
    try:
        found = json.load(urllib.request.urlopen(SEARCH + urllib.parse.quote(title[:80]), timeout=20)).get('items', [])
    except Exception:
        return None
    wanted = norm(title)
    best = max(((difflib.SequenceMatcher(None, wanted, norm(i['name'])).ratio(), i) for i in found if i.get('type') == 'app'),
               key=lambda x: x[0], default=(0, None))
    if best[0] < 0.88:
        return None
    for name in ('library_600x900.jpg', 'header.jpg'):
        try:
            return urllib.request.urlopen(ART % (best[1]['id'], name), timeout=20).read()
        except Exception:
            continue
    return None


def title_card(title, platforms):
    w, h = 320, 440
    colour = next((COLOUR[p] for p in platforms if p in COLOUR), '#3a3f47')
    base = Image.new('RGB', (w, h), colour)
    shade = Image.new('RGB', (w, h), '#000000')
    mask = Image.linear_gradient('L').resize((w, h))
    card = Image.composite(shade, base, mask.point(lambda v: int(v * 0.55)))
    d = ImageDraw.Draw(card)
    d.rectangle((0, 0, w, 34), fill='#111111')
    d.text((12, 8), ' · '.join(platforms)[:30], fill='#dddddd', font=ImageFont.truetype(FONT, 15))
    size = 30
    while True:
        font = ImageFont.truetype(FONT, size)
        lines = textwrap.wrap(title, width=max(8, int(w / (size * 0.62))))[:6]
        if size <= 16 or (len(lines) * (size + 6) < h - 120 and max(d.textlength(x, font=font) for x in lines) < w - 28):
            break
        size -= 2
    y = (h - len(lines) * (size + 6)) // 2
    for line in lines:
        d.text(((w - d.textlength(line, font=font)) / 2, y), line, fill='#ffffff', font=font)
        y += size + 6
    return card


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    games = list(csv.DictReader(open(CATALOG, newline='', encoding='utf-8')))
    index = {r['id']: r for r in csv.DictReader(open(INDEX, newline='', encoding='utf-8'))} if os.path.exists(INDEX) else {}
    steam = generated = 0
    for g in games:
        path = os.path.join(OUT_DIR, g['id'] + '.webp')
        platforms = json.loads(g['platforms'])
        retry = '--retry-generated' in sys.argv and index.get(g['id'], {}).get('source') == 'generated'
        if os.path.exists(path) and not retry:
            continue
        im = None
        source = 'generated'
        if '--no-steam' not in sys.argv and any(p.startswith('PC') or p in PORTS for p in platforms):
            data = steam_cover(g['title'])
            if data:
                im, source = Image.open(io.BytesIO(data)).convert('RGB'), 'steam'
                im.thumbnail((320, 440))
        if im is None:
            if retry:
                continue  # keep the card it already has
            im = title_card(g['title'], platforms)
        im.save(path, 'WEBP', quality=82)
        index[g['id']] = {'id': g['id'], 'source': source}
        steam += source == 'steam'
        generated += source == 'generated'
    with open(INDEX, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=['id', 'source'])
        w.writeheader()
        w.writerows(sorted(index.values(), key=lambda r: int(r['id'])))
    print(f"{steam} from Steam, {generated} generated; {len(os.listdir(OUT_DIR))}/{len(games)} games have a cover")


if __name__ == '__main__':
    main()
