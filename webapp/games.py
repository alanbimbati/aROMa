"""The games catalogue: search, filters, sorting and counts over data/games_catalog.csv (descriptions only)."""
import csv
import json
import os
import unicodedata
from functools import lru_cache

COVERS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'cache', 'game_covers')
DATA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'games_catalog.csv')
SORTS = {
    'titolo': lambda g: g['title'].lower(),
    'anno': lambda g: (g['year'] is None, -(g['year'] or 0), g['title'].lower()),
    'recenti': lambda g: -g['id'],
}


def fold(text):
    """Lower case without accents, so 'pokemon' finds 'Pokémon'."""
    return ''.join(c for c in unicodedata.normalize('NFD', text.lower()) if unicodedata.category(c) != 'Mn')


@lru_cache(maxsize=1)
def load():
    if not os.path.exists(DATA):
        return []
    with open(DATA, newline='', encoding='utf-8') as f:
        games = []
        for r in csv.DictReader(f):
            g = dict(id=int(r['id']), title=r['title'], platforms=json.loads(r['platforms']), genres=json.loads(r['genres']),
                     description=r['description'], languages=json.loads(r['languages']),
                     multilanguage=r['multilanguage'] == '1', regions=json.loads(r['regions']),
                     year=int(r['year']) if r['year'] else None,
                     developer=r.get('developer', ''), publisher=r.get('publisher', ''))
            g['_search'] = fold(' '.join([g['title'], *g['platforms'], *g['genres'], g['developer'], g['publisher'], g['description']]))
            games.append(g)
    return games


def count_by(games, key):
    counts = {}
    for g in games:
        for v in (g[key] if isinstance(g[key], list) else [g[key]]):
            if v:
                counts[v] = counts.get(v, 0) + 1
    return sorted(counts.items(), key=lambda kv: (-kv[1], str(kv[0])))


def search(q='', platform=None, genre=None, language=None, region=None, sort='titolo', page=1, per_page=48):
    games = load()
    terms = fold(q).split()
    def keep(g):
        return (all(t in g['_search'] for t in terms)
                and (not platform or platform in g['platforms'])
                and (not genre or genre in g['genres'])
                and (not language or language in g['languages'])
                and (not region or region in g['regions']))
    found = sorted((g for g in games if keep(g)), key=SORTS.get(sort, SORTS['titolo']))
    per_page = max(1, min(per_page, 100))
    page = max(1, page)
    items = [{k: v for k, v in g.items() if not k.startswith('_')} for g in found[(page - 1) * per_page:page * per_page]]
    for it in items:
        it['description'] = it['description'][:280]
        it['cover'] = os.path.isfile(os.path.join(COVERS, f"{it['id']}.webp"))
    return {'total': len(found), 'page': page, 'per_page': per_page, 'items': items,
            # the counts follow the other filters, so a filter never offers a choice that finds nothing
            'facets': {k: count_by(found, k) for k in ('platforms', 'genres', 'languages', 'regions')}}


def detail(game_id):
    for g in load():
        if g['id'] == game_id:
            return {**{k: v for k, v in g.items() if not k.startswith('_')},
                    'cover': os.path.isfile(os.path.join(COVERS, f"{game_id}.webp"))}
    return None
