r"""Cleans an export of the games table into data/games_catalog.csv (one row per game, normalised metadata).

    python scripts/build_games_catalog.py games_raw.csv

The export has only descriptive columns (id, title, platform, genre, description, language, year, region):
no message links, no who-took-what. Export it with:
    \copy (select id,title,platform,genre,description,language,year,region from games order by id) to stdout with csv header
"""
import csv
import json
import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from webapp.games_clean import clean  # noqa: E402

OUT = os.path.join(BASE_DIR, 'data', 'games_catalog.csv')


if __name__ == '__main__':
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    with open(sys.argv[1], newline='', encoding='utf-8') as f:
        games, report = clean(list(csv.DictReader(f)))
    with open(OUT, 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(['id', 'title', 'platforms', 'genres', 'description', 'languages', 'multilanguage', 'regions', 'year', 'developer', 'publisher'])
        for g in games:
            w.writerow([g['id'], g['title'], json.dumps(g['platforms'], ensure_ascii=False), json.dumps(g['genres'], ensure_ascii=False),
                        g['description'], json.dumps(g['languages'], ensure_ascii=False), int(g['multilanguage']),
                        json.dumps(g['regions'], ensure_ascii=False), g['year'] or '', g['developer'], g['publisher']])
    print(json.dumps(report, indent=2))
