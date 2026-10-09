"""Cleans the metadata of the games catalogue: one spelling per platform, genre, language and region."""
import re
from datetime import date

PLATFORMS = {
    'ps1': 'PS1', 'psx': 'PS1', 'playstation': 'PS1', 'playstation 1': 'PS1',
    'ps2': 'PS2', 'playstation 2': 'PS2', 'ps3': 'PS3', 'playstation 3': 'PS3', 'ps4': 'PS4', 'psp': 'PSP',
    'pc': 'PC', 'windows': 'PC', 'dos': 'PC (DOS)', 'pc dos': 'PC (DOS)', 'android': 'Android',
    'nintendo switch': 'Switch', 'switch': 'Switch',
    'nintendo ds': 'Nintendo DS', 'ds': 'Nintendo DS', 'nds': 'Nintendo DS',
    '3ds': 'Nintendo 3DS', 'nintendo 3ds': 'Nintendo 3DS',
    'gba': 'Game Boy Advance', 'game boy advance': 'Game Boy Advance', 'game boy advance (gba)': 'Game Boy Advance',
    'gbc': 'Game Boy Color', 'game boy color': 'Game Boy Color', 'game boy color (gbc)': 'Game Boy Color',
    'game boy': 'Game Boy', 'gb': 'Game Boy',
    'gamecube': 'GameCube', 'gc': 'GameCube', 'wii': 'Wii', 'snes': 'SNES', 'nes': 'NES',
    'n64': 'Nintendo 64', 'nintendo 64': 'Nintendo 64', 'arcade': 'Arcade',
    'nintendo wii': 'Wii', 'xbox 360': 'Xbox 360', 'xbox': 'Xbox', 'ios': 'iOS', 'cia': 'Nintendo 3DS',
}
# spellings reduced to letters and digits, so 'GameBoyAdvance', 'Game Boy (GB)' and '#3ds' all land on one name
COMPACT = {re.sub(r'[^a-z0-9]', '', k): v for k, v in PLATFORMS.items()}
COMPACT.update({'gameboyadvance': 'Game Boy Advance', 'gameboygb': 'Game Boy', 'mamemultiplearcademachineemulator': 'Arcade'})
GENRES = {
    'horror': 'Horror', 'survival horror': 'Horror', 'picchiaduro': 'Picchiaduro', 'beat em up': 'Picchiaduro',
    'rpg': 'Ruolo', 'jrpg': 'Ruolo', 'gdr': 'Ruolo', 'ruolo': 'Ruolo', 'action': 'Azione', 'adventure': 'Avventura',
    'sparatutto': 'Sparatutto', 'sparattutto': 'Sparatutto', 'corse automobilistiche': 'Guida', 'simulazione sportiva': 'Sport', 'fps': 'Sparatutto', 'racing': 'Guida', 'corse': 'Guida', 'sports': 'Sport',
    'platform': 'Piattaforma', 'puzzle': 'Puzzle', 'strategy': 'Strategia', 'simulation': 'Simulazione',
    'simulatore': 'Simulazione', 'simulazione di guida': 'Guida', 'corsa': 'Guida', 'sport': 'Sport',
}
REGIONS = [('europ', 'Europa'), ('ital', 'Europa'), ('usa', 'USA'), ('america', 'USA'), ('giappon', 'Giappone'),
           ('jap', 'Giappone'), ('austral', 'Australia')]
WORLD = ('internazional', 'global', 'multiregion', 'mondo')
LANGUAGES = [('ital', 'Italiano'), ('ingles', 'Inglese'), ('english', 'Inglese'), ('giappon', 'Giapponese'),
             ('franc', 'Francese'), ('tedesc', 'Tedesco'), ('spagnol', 'Spagnolo')]


def split(text):
    return [p.strip() for p in re.split(r'[,/;]| e ', text or '') if p.strip()]


def platforms(raw):
    out = []
    for part in split(raw):
        # '#3ds #Cia' is two tags in one field
        for tag in (re.findall(r'#\w+', part) or [part]):
            name = PLATFORMS.get(tag.lstrip('#').lower()) or COMPACT.get(re.sub(r'[^a-z0-9]', '', tag.lower()), tag.lstrip('#').strip())
            if name not in out:
                out.append(name)
    return out


def genres(raw):
    out = []
    # a note in brackets ('Avventura (punta e clicca)') is not a second genre
    text = re.sub(r'\([^)]*\)?', '', raw or '')
    for part in (re.findall(r'#(\w+)', text) or split(text)):
        name = GENRES.get(part.lower(), part[:1].upper() + part[1:].lower())
        if name not in out:
            out.append(name)
    return out


def regions(raw):
    low = re.sub(r'\([^)]*\)?', '', (raw or '')).lower()  # '(con patch in italiano)' is a note, not a region
    out = [name for key, name in REGIONS if key in low]
    if any(w in low for w in WORLD):
        out = ['Internazionale']
    return sorted(set(out), key=out.index)


def languages(raw):
    """The languages named, plus whether Italian is among them (the thing the group filters on most). 'Multilingue'
    without a list says nothing about Italian, so it stays unknown rather than guessed."""
    low = (raw or '').lower()
    out = [name for key, name in LANGUAGES if key in low]
    out = sorted(set(out), key=out.index)
    multi = 'multi' in low
    return out, multi


LEGAL = re.compile(r',?\s+(?:s\.?r\.?l\.?|inc\.?|ltd\.?|llc|co\.?|gmbh|s\.?a\.?|corp\.?|corporation|limited)$', re.I)
COMPANY = {'ea': 'Electronic Arts', 'electronic arts inc': 'Electronic Arts', 'sce': 'Sony Computer Entertainment',
           'sega corporation': 'Sega', 'konami digital entertainment': 'Konami', 'namco bandai games': 'Bandai Namco',
           'bandai namco entertainment': 'Bandai Namco', 'namco bandai': 'Bandai Namco', 'activision publishing': 'Activision',
           'ubisoft entertainment': 'Ubisoft', 'capcom co': 'Capcom'}
DEV = re.compile(r'sviluppat[oa] (?:e pubblicat[oa] )?(?:da|dalla|dal|dallo|dall\'|dai|dagli) (?:la |il |lo |l\')?([^,.;]+?)(?: e (?:pubblicat|distribuit)| ed |, |\.|;| nel | per | in collaborazione|$)')
PUB = re.compile(r'(?:pubblicat[oa]|distribuit[oa]|edit[oa]) (?:in [A-Za-z]+ )?(?:da|dalla|dal|dallo|dall\'|dai|dagli) (?:la |il |lo |l\')?([^,.;]+?)(?: nel | per | in | il |, |\.|;|$)')


def company(raw):
    name = re.sub(r'\s+', ' ', raw or '').strip(" '\"")
    name = LEGAL.sub('', name).strip()
    name = COMPANY.get(name.lower(), name)
    if name.lower() in ('aroma', 'sconosciuto', 'varie', 'vari'):  # the channel's own name or a placeholder, not a company
        return ''
    return name if 2 <= len(name) <= 40 and len(name.split()) <= 5 else ''


def credits(description):
    """(developer, publisher) as the description states them. 'Sviluppato e pubblicato da X' names X for both."""
    # 'S.r.l.', 'Inc.' and the like carry dots that would end the name early
    text = re.sub(r',?\s+(?:S\.r\.l\.|S\.R\.L\.|Inc\.|Ltd\.|Co\.|Corp\.|S\.A\.|LLC|GmbH)(?=\s|,|\.|$)', '', description or '')
    dev = DEV.search(text)
    pub = PUB.search(text)
    developer = company(dev.group(1)) if dev else ''
    publisher = company(pub.group(1)) if pub else ''
    if re.search(r'sviluppat[oa] e pubblicat[oa] da', text) and developer and not publisher:
        publisher = developer
    return developer, publisher


def year(raw, today=None):
    try:
        y = int(str(raw).strip())
    except ValueError:
        return None
    return y if 1970 <= y <= (today or date.today()).year + 1 else None


def clean_row(row):
    langs, multi = languages(row.get('language'))
    description = re.sub(r'\s+', ' ', re.sub(r'#(\w+)', r'\1', row.get('description') or '')).strip()
    developer, publisher = credits(description)
    plats, genre_list = platforms(row.get('platform')), genres(row.get('genre'))
    # Arcade is a kind of game, not a console: it moves to the genres; with no console left the game is 'Altro'
    if 'Arcade' in plats:
        plats = [p for p in plats if p != 'Arcade'] or ['Altro']
        if 'Arcade' not in genre_list:
            genre_list.append('Arcade')
    return {
        'id': int(row['id']),
        'title': re.sub(r'\s+', ' ', (row.get('title') or '')).strip(),
        'platforms': plats,
        'genres': genre_list,
        'description': description,
        'developer': developer,
        'publisher': publisher,
        'languages': langs,
        'multilanguage': multi,
        'regions': regions(row.get('region')),
        'year': year(row.get('year')),
    }


def completeness(game):
    return sum(bool(game[k]) for k in ('platforms', 'genres', 'description', 'languages', 'regions', 'year'))


def clean(rows):
    """(games, report). Same title on the same platforms is one game: the most complete row wins."""
    best, dropped, empty = {}, 0, 0
    for row in rows:
        g = clean_row(row)
        if not g['title']:
            empty += 1
            continue
        key = (g['title'].lower(), tuple(sorted(g['platforms'])))
        if key in best:
            dropped += 1
            if completeness(g) <= completeness(best[key]):
                continue
        best[key] = g
    games = sorted(best.values(), key=lambda g: g['id'])
    report = {
        'input_rows': len(rows), 'games': len(games), 'duplicates_merged': dropped, 'without_title': empty,
        'without_year': sum(g['year'] is None for g in games),
        'without_platform': sum(not g['platforms'] for g in games),
        'without_genre': sum(not g['genres'] for g in games),
        'without_description': sum(not g['description'] for g in games),
        'without_developer': sum(not g['developer'] for g in games),
        'without_publisher': sum(not g['publisher'] for g in games),
    }
    return games, report
