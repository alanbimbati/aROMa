"""Box art for the games catalogue, from the libretro thumbnail database (public, no key).

    python scripts/fetch_game_covers.py [--limit N]

Matches each game of data/games_catalog.csv to a picture by title and platform, saves a 320px webp as
cache/game_covers/<id>.webp and records where it came from in data/games_covers.csv. A game with no confident
match gets no picture (the page shows a placeholder): a wrong cover is worse than none. Resumable.
"""
import csv
import difflib
import html
import io
import json
import os
import re
import sys
import unicodedata
import urllib.parse
import urllib.request

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from PIL import Image  # noqa: E402

CATALOG = os.path.join(BASE_DIR, 'data', 'games_catalog.csv')
OUT_DIR = os.path.join(BASE_DIR, 'cache', 'game_covers')
INDEX = os.path.join(BASE_DIR, 'data', 'games_covers.csv')
ROOT = 'https://thumbnails.libretro.com/'
SYSTEMS = {
    'PS1': 'Sony - PlayStation', 'PS2': 'Sony - PlayStation 2', 'PSP': 'Sony - PlayStation Portable',
    'PS3': 'Sony - PlayStation 3', 'Nintendo DS': 'Nintendo - Nintendo DS', 'Game Boy Advance': 'Nintendo - Game Boy Advance',
    'Nintendo 64': 'Nintendo - Nintendo 64', 'GameCube': 'Nintendo - GameCube', 'Wii': 'Nintendo - Wii',
    'SNES': 'Nintendo - Super Nintendo Entertainment System', 'Game Boy Color': 'Nintendo - Game Boy Color',
    'Game Boy': 'Nintendo - Game Boy', 'NES': 'Nintendo - Nintendo Entertainment System',
    'Nintendo 3DS': 'Nintendo - Nintendo 3DS',
}
REGION_RANK = {'europe': 0, 'world': 1, 'usa': 2, 'japan': 4}
ROMAN = {'ii': '2', 'iii': '3', 'iv': '4', 'v': '5', 'vi': '6', 'vii': '7', 'viii': '8', 'ix': '9', 'x': '10'}


def norm(title):
    t = unicodedata.normalize('NFD', title.lower())
    t = ''.join(c for c in t if unicodedata.category(c) != 'Mn')
    t = re.sub(r'\(.*?\)|\[.*?\]', ' ', t).replace('&', ' and ')
    t = re.sub(r"[^a-z0-9 ]", ' ', t.replace("'", ''))
    words = [ROMAN.get(w, w) for w in t.split() if w not in ('the', 'a')]
    return ' '.join(words)


def numbers(text):
    return re.findall(r'\d+', text)


def listing(system):
    cache = os.path.join(BASE_DIR, 'cache', 'libretro_' + re.sub(r'\W+', '_', system) + '.json')
    if os.path.exists(cache):
        return json.load(open(cache))
    url = ROOT + urllib.parse.quote(system) + '/Named_Boxarts/'
    page = urllib.request.urlopen(url, timeout=60).read().decode('utf-8', 'replace')
    names = [html.unescape(urllib.parse.unquote(h))[:-4] for h in re.findall(r'href="([^"]+\.png)"', page)]
    os.makedirs(os.path.dirname(cache), exist_ok=True)
    json.dump(names, open(cache, 'w'))
    return names


def region_rank(name):
    low = name.lower()
    return min((r for k, r in REGION_RANK.items() if k in low), default=3)


class Matcher:
    def __init__(self, names):
        self.by_norm = {}
        for n in names:
            if '(demo' in n.lower() or '(beta' in n.lower() or '(proto' in n.lower():
                continue
            self.by_norm.setdefault(norm(n), []).append(n)
        self.keys = list(self.by_norm)

    def find(self, title):
        key = norm(title)
        if not key:
            return None
        hit = self.by_norm.get(key)
        if not hit:
            # same numbers (sequels), and almost the same words
            close = [k for k in difflib.get_close_matches(key, self.keys, n=3, cutoff=0.9) if numbers(k) == numbers(key)]
            hit = self.by_norm[close[0]] if close else None
        return min(hit, key=region_rank) if hit else None


def main():
    limit = int(sys.argv[sys.argv.index('--limit') + 1]) if '--limit' in sys.argv else None
    os.makedirs(OUT_DIR, exist_ok=True)
    games = list(csv.DictReader(open(CATALOG, newline='', encoding='utf-8')))
    done = {}
    if os.path.exists(INDEX):
        done = {r['id']: r for r in csv.DictReader(open(INDEX, newline='', encoding='utf-8'))}
    matchers = {}
    fetched = 0
    for g in games:
        if g['id'] in done and (done[g['id']]['source'] == '' or os.path.exists(os.path.join(OUT_DIR, g['id'] + '.webp'))):
            continue
        row = {'id': g['id'], 'source': ''}
        for p in json.loads(g['platforms']):
            system = SYSTEMS.get(p)
            if not system:
                continue
            if system not in matchers:
                matchers[system] = Matcher(listing(system))
            name = matchers[system].find(g['title'])
            if name:
                row['source'] = f"{system}/Named_Boxarts/{name}.png"
                break
        if row['source']:
            try:
                data = urllib.request.urlopen(ROOT + urllib.parse.quote(row['source']), timeout=30).read()
                im = Image.open(io.BytesIO(data)).convert('RGB')
                im.thumbnail((320, 320))
                im.save(os.path.join(OUT_DIR, g['id'] + '.webp'), 'WEBP', quality=82)
                fetched += 1
            except Exception as e:
                print(f"  skipped {g['title']}: {e}")
                row['source'] = ''
        done[g['id']] = row
        if limit and fetched >= limit:
            break
    with open(INDEX, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=['id', 'source'])
        w.writeheader()
        w.writerows(sorted(done.values(), key=lambda r: int(r['id'])))
    have = sum(1 for r in done.values() if r['source'])
    print(f"{have}/{len(games)} games have a cover ({fetched} downloaded now)")


if __name__ == '__main__':
    main()
