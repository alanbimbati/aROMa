"""Illustrations for every mob and boss that has none in images/, from the Pollinations image generator.

Same service and key as fetch_marvel_images.py (POLLINATIONS_API_KEY in .env; without one only a few pictures are served).
Runs resumably: a picture already in images/ is skipped. Prompts and seeds go to data/enemy_images.csv.

    python scripts/fetch_enemy_images.py              # everything still missing
    python scripts/fetch_enemy_images.py --only Doom  # a saga or a name
"""
import argparse
import csv
import io
import os
import sys
import time
import urllib.parse
import zlib

import requests
from PIL import Image

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IMAGES = os.path.join(BASE_DIR, 'images')
MANIFEST = os.path.join(BASE_DIR, 'data', 'enemy_images.csv')
API_KEY = os.getenv('POLLINATIONS_API_KEY', '')
ENDPOINT = 'https://gen.pollinations.ai/image/{prompt}' if API_KEY else 'https://image.pollinations.ai/prompt/{prompt}'
STYLE = ('single creature centered, full body, dark fantasy digital painting, dramatic lighting, '
         'highly detailed, sharp focus, no text, no logo')


def missing():
    out = []
    for kind in ('mobs', 'bosses'):
        with open(os.path.join(BASE_DIR, 'data', f'{kind}.csv'), newline='', encoding='utf-8') as f:
            for r in csv.DictReader(f, escapechar='\\'):
                name = r['nome']
                path = lambda ext: os.path.join(IMAGES, f"{name.lower().replace(' ', '_')}{ext}")  # noqa: E731
                # two enemies with one name (the two Hunters) share one file: made once
                if not any(os.path.exists(path(e)) for e in ('.png', '.jpg', '.jpeg')) and path('.png') not in [o[3] for o in out]:
                    out.append((name, r.get('series') or '', r.get('description') or '', path('.png')))
    return out


def fetch(name, series, description, retries=4):
    prompt = f"{name} from {series}, {description}, {STYLE}"
    seed = zlib.crc32(name.encode()) % 100000
    url = ENDPOINT.format(prompt=urllib.parse.quote(prompt)) + f"?width=1024&height=1024&model=flux&nologo=true&seed={seed}"
    if API_KEY:
        url += f"&key={API_KEY}"
    for attempt in range(retries):
        try:
            r = requests.get(url, timeout=120)
            if r.status_code == 200 and r.headers.get('content-type', '').startswith('image'):
                return Image.open(io.BytesIO(r.content)).convert('RGB'), prompt, seed
            print(f"  {name}: HTTP {r.status_code}", flush=True)
            if r.status_code in (401, 403):
                return None, prompt, seed
        except requests.RequestException as e:
            print(f"  {name}: {str(e)[:60]}", flush=True)
        time.sleep(8 * (attempt + 1))
    return None, prompt, seed


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--only')
    args = ap.parse_args()
    todo = [m for m in missing() if not args.only or args.only.lower() in (m[0] + ' ' + m[1]).lower()]
    print(f"{len(todo)} pictures to make", flush=True)
    done = 0
    rows = []
    for name, series, description, path in todo:
        img, prompt, seed = fetch(name, series, description)
        if img is None:
            print(f"{name}: not made", flush=True)
            continue
        img.save(path)
        rows.append((name, prompt, seed))
        done += 1
        print(f"{name}: saved", flush=True)
        time.sleep(3)
    if rows:
        new = not os.path.exists(MANIFEST)
        with open(MANIFEST, 'a', newline='', encoding='utf-8') as f:
            w = csv.writer(f)
            if new:
                w.writerow(['name', 'prompt', 'seed'])
            w.writerows(rows)
    print(f"made {done}/{len(todo)}")


if __name__ == '__main__':
    main()
