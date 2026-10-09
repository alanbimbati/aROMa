"""Static build of the public part of the web app, for a static host such as Vercel.

The catalogue, every character sheet, the pictures, the badge images and the share pages need no database, so they
can live on a CDN: fast, free, up even when the server is off. Everything private (/api/me/*, /login, season,
dungeons, Nostr) is forwarded by the generated vercel.json to the real server, API_ORIGIN.

    API_ORIGIN=https://api.example.org WEBAPP_URL=https://aroma.example.org python -m webapp.export_static
    cd webapp/dist && npx vercel --prod

It reads the same game data as the server (the character files, and the season for the active content pack), so
run it where the database is reachable, e.g. `docker compose run --rm web python -m webapp.export_static`.
"""
import json
import os
import shutil
import sys
from html import escape

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from webapp import app as server  # noqa: E402
from webapp import data  # noqa: E402

STATIC_DIR = os.path.join(BASE_DIR, 'webapp', 'static')
DIST = os.environ.get('EXPORT_DIR', os.path.join(BASE_DIR, 'webapp', 'dist'))


def write(path, content, mode='w'):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, mode, **({} if 'b' in mode else {'encoding': 'utf-8'})) as f:
        f.write(content)


def build(api_origin, public_url):
    if os.path.isdir(DIST):
        shutil.rmtree(DIST)
    shutil.copytree(STATIC_DIR, os.path.join(DIST, 'static'), ignore=shutil.ignore_patterns('index.html'))
    shutil.copyfile(os.path.join(STATIC_DIR, 'index.html'), os.path.join(DIST, 'index.html'))

    catalogue = data.catalog()
    write(os.path.join(DIST, 'data', 'characters.json'), json.dumps(catalogue, ensure_ascii=False))
    for c in catalogue:
        detail = data.character_detail(c['id'])
        write(os.path.join(DIST, 'data', 'characters', f"{c['id']}.json"), json.dumps(detail, ensure_ascii=False))
        title = f"{c['name']} · Lv. {c['level']} · aROMa"
        desc = f"{c['attack']['name']}: {c['attack']['damage']} danni. {c['description']}"
        write(os.path.join(DIST, 'p', f"{c['id']}.html"),
              f'<!doctype html><html lang="it"><head><meta charset="utf-8"><title>{escape(title)}</title>'
              f'<meta property="og:title" content="{escape(title)}"><meta property="og:description" content="{escape(desc)}">'
              f'<meta property="og:image" content="{public_url}/img/{escape(c["img"])}/512.webp">'
              f'<meta name="twitter:card" content="summary_large_image">'
              f'<meta http-equiv="refresh" content="0; url=/#/personaggio/{c["id"]}"></head>'
              f'<body><a href="/#/personaggio/{c["id"]}">{escape(title)}</a></body></html>')

    # pictures: the same three widths the server makes on demand, under the same addresses
    names = {c['img'] for c in catalogue} | {'default'}
    made = 0
    for name in sorted(names):
        for width in server.THUMB_WIDTHS:
            try:
                thumb = server.make_thumbnail(name, width)
            except Exception as e:
                print(f"  skipped {name}/{width}: {e}")
                continue
            if thumb:
                os.makedirs(os.path.join(DIST, 'img', name), exist_ok=True)
                shutil.copyfile(thumb, os.path.join(DIST, 'img', name, f"{width}.webp"))
                made += 1

    badges = server.BADGE_DIR
    if os.path.isdir(badges):
        shutil.copytree(badges, os.path.join(DIST, 'badges'))

    long_cache = [{"key": "Cache-Control", "value": "public, max-age=31536000, immutable"}]
    config = {
        "cleanUrls": True,
        "rewrites": [
            {"source": "/api/characters", "destination": "/data/characters.json"},
            {"source": "/api/characters/:id", "destination": "/data/characters/:id.json"},
            {"source": "/api/:path*", "destination": f"{api_origin}/api/:path*"},
            {"source": "/login", "destination": f"{api_origin}/login"},
        ],
        "headers": [
            {"source": "/img/(.*)", "headers": long_cache},
            {"source": "/badges/(.*)", "headers": long_cache},
            {"source": "/data/(.*)", "headers": [{"key": "Cache-Control", "value": "public, max-age=300, s-maxage=300"}]},
        ],
    }
    write(os.path.join(DIST, 'vercel.json'), json.dumps(config, indent=2))
    return len(catalogue), made


if __name__ == '__main__':
    api_origin = os.environ.get('API_ORIGIN', '').rstrip('/')
    public_url = os.environ.get('WEBAPP_URL', '').rstrip('/')
    if not api_origin or not public_url:
        sys.exit("Set API_ORIGIN (where the real server answers) and WEBAPP_URL (the public address, e.g. the Vercel domain).")
    characters, pictures = build(api_origin, public_url)
    size = sum(os.path.getsize(os.path.join(r, f)) for r, _, fs in os.walk(DIST) for f in fs) / 1e6
    print(f"{characters} characters, {pictures} pictures, {size:.0f} MB in {DIST}")
    print("Deploy:  cd", DIST, "&& npx vercel --prod")
