"""Marvel dungeon ladder: 13 dungeons from difficulty 1 to 10, with the mobs and bosses the new ones need.

The ids follow the ladder (the game unlocks dungeons in id order within a season), so adding a dungeon in the
middle renumbers the ones after it. Marvel has not launched in production yet, so nothing depends on the old ids.

    python scripts/marvel_dungeons.py          # show the ladder
    python scripts/marvel_dungeons.py --apply  # rewrite dungeons.csv, mobs.csv, bosses.csv (Marvel rows only)
"""
import csv
import io
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from services.dungeon_rewards import completion  # noqa: E402

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(BASE_DIR, 'data')
FIRST_ID = 13
KEPT = ['Base Hydra', 'Famiglia Divina (Asgard)', 'Guardiani della Galassia', 'Infinity War', 'Endgame', "L'Arrivo di Galactus"]

# name, hp, attack, attack type, difficulty, description, speed
NEW_MOBS = [
    ('Scagnozzo', 35, 10, 'physical', 1, 'Teppista di strada', 30),
    ('Scagnozzo Armato', 50, 14, 'ranged', 1, 'Malvivente con la pistola', 32),
    ('Ninja della Mano', 80, 22, 'physical', 2, 'Assassino della Mano', 55),
    ('Cacciatore', 140, 40, 'ranged', 4, 'Cacciatore al soldo di Kraven', 55),
    ('Simbionte', 200, 55, 'physical', 6, 'Creatura aliena fatta di simbionte', 65),
    ('Sentinella', 420, 90, 'ranged', 7, 'Robot gigante anti-mutanti', 45),
    ('Guardia Temporale', 480, 100, 'ranged', 8, 'Soldato del Conquistatore', 60),
]
# name, hp, attack, attack type, description, wumpa, exp, speed, behaviour, phases, difficulty
NEW_BOSSES = [
    ('Vulture', 900, 30, 'physical', "L'Avvoltoio di New York", 400, 100, 45, 'tactical', {"50": "phase2"}, 1),
    ('Rhino', 1800, 55, 'physical', 'Una corazza vivente che non si ferma', 800, 200, 40, 'tactical', {"50": "phase2"}, 2),
    ('Green Goblin', 4500, 115, 'magic', "L'incubo di Oscorp", 2200, 500, 75, 'tactical', {"50": "phase2", "20": "phase3"}, 4),
    ('Kraven', 6500, 145, 'physical', 'Il cacciatore supremo', 3500, 700, 75, 'tactical', {"50": "phase2"}, 5),
    ('Carnage', 11000, 210, 'physical', 'Caos in forma di simbionte', 6000, 1200, 85, 'boss', {"50": "phase2", "20": "phase3"}, 7),
    ('Magneto', 16000, 270, 'magic', 'Il Padrone del Magnetismo', 9000, 1800, 85, 'boss', {"50": "phase2", "20": "phase3"}, 8),
    ('Kang', 28000, 380, 'magic', 'Il Conquistatore', 15000, 3000, 90, 'boss', {"80": "phase2", "50": "phase3", "20": "phase4"}, 9),
]


def talk(text, delay=6):
    return {"text": text, "delay": delay}


# The level a player should have to clear it alone (a team can go in earlier): a smooth climb over the whole ladder,
# the enemies are made at it (see evals/balance_sim.py) and the rewards follow it (services/dungeon_rewards.py)
RECOMMENDED_LEVEL = {'Strade di New York': 5, "Hell's Kitchen": 9, 'Base Hydra': 14, 'Torre Oscorp': 20, 'La Grande Caccia': 27, 'Guardiani della Galassia': 35, 'Invasione Simbionte': 43, 'Famiglia Divina (Asgard)': 51, 'Mondo Mutante': 60, 'Il Conquistatore': 70, 'Infinity War': 80, 'Endgame': 90, "L'Arrivo di Galactus": 100}

# Ladder order. 'kept' ones keep their steps from the current file; the others are defined here.
LADDER = [
    dict(name='Strade di New York', difficulty=1, wumpa=300, exp=150,
         description="Ripulisci le strade di New York dai malviventi e affronta l'Avvoltoio.",
         steps=[{"mobs": [{"name": "Scagnozzo", "count": 3}]},
                {"mobs": [{"name": "Scagnozzo Armato", "count": 2}], "dialogue": talk("Scagnozzo: Prendete l'eroe!", 4)},
                {"boss": "Vulture", "dialogue": talk("Vulture: Dall'alto nessuno mi prende!")}]),
    dict(name="Hell's Kitchen", difficulty=2, wumpa=600, exp=300,
         description="La Mano ha invaso il quartiere: ninja, un colpo di scena e un gigante corazzato.",
         steps=[{"mobs": [{"name": "Ninja della Mano", "count": 4}]},
                {"mobs": [{"name": "Ninja della Mano", "count": 3}, {"name": "Scagnozzo Armato", "count": 2}]},
                {"boss": "Rhino", "dialogue": talk("Rhino: Niente può fermarmi!")}]),
    dict(name='Base Hydra'),
    dict(name='Torre Oscorp', difficulty=4, wumpa=1800, exp=900,
         description="Nei laboratori di Oscorp qualcosa è andato storto, e Norman Osborn ride.",
         steps=[{"mobs": [{"name": "Ultron Bot", "count": 3}]},
                {"mobs": [{"name": "Chitauri", "count": 3}], "dialogue": talk("Segnale intercettato: tecnologia aliena nei laboratori.", 5)},
                {"boss": "Green Goblin", "dialogue": talk("Green Goblin: Un po' di fuochi d'artificio?", 7)}]),
    dict(name='La Grande Caccia', difficulty=5, wumpa=2800, exp=1400,
         description="Kraven ha scelto la preda: tu. Sopravvivi alla caccia.",
         steps=[{"mobs": [{"name": "Cacciatore", "count": 4}]},
                {"mobs": [{"name": "Cacciatore", "count": 3}, {"name": "Elite Hydra", "count": 2}], "dialogue": talk("Cacciatore: Il capo vuole la sua preda viva.", 5)},
                {"boss": "Kraven", "dialogue": talk("Kraven: La caccia finisce qui.", 7)}]),
    dict(name='Guardiani della Galassia'),
    dict(name='Invasione Simbionte', difficulty=7, wumpa=4500, exp=2250,
         description="Una macchia di simbionte è fuggita dal laboratorio: ora ce n'è ovunque.",
         steps=[{"mobs": [{"name": "Simbionte", "count": 4}]},
                {"mobs": [{"name": "Simbionte", "count": 5}], "dialogue": talk("Il simbionte si moltiplica. Non lasciate che vi tocchi!", 5)},
                {"boss": "Carnage", "dialogue": talk("Carnage: CAOS!", 8)}]),
    dict(name='Famiglia Divina (Asgard)'),
    dict(name='Mondo Mutante', difficulty=8, wumpa=6000, exp=3000,
         description="Le Sentinelle danno la caccia ai mutanti, e Magneto non resterà a guardare.",
         steps=[{"mobs": [{"name": "Sentinella", "count": 3}]},
                {"mobs": [{"name": "Sentinella", "count": 4}], "dialogue": talk("Sentinella: Mutante rilevato. Eliminazione.", 5)},
                {"boss": "Magneto", "dialogue": talk("Magneto: Io sono il futuro dei mutanti.", 8)}]),
    dict(name='Il Conquistatore', difficulty=9, wumpa=7000, exp=3500,
         description="Kang conosce già il finale: dimostragli che si sbaglia.",
         steps=[{"mobs": [{"name": "Guardia Temporale", "count": 4}]},
                {"mobs": [{"name": "Guardia Temporale", "count": 3}, {"name": "Outrider", "count": 3}], "dialogue": talk("Guardia Temporale: Il Conquistatore ha già vinto.", 5)},
                {"boss": "Kang", "dialogue": talk("Kang: Ho già visto come finisce.", 9)}]),
    dict(name='Infinity War'),
    dict(name='Endgame'),
    dict(name="L'Arrivo di Galactus"),
]


def _read(path):
    raw = open(path, newline='', encoding='utf-8').read()
    reader = csv.DictReader(io.StringIO(raw, newline=''), skipinitialspace=True)
    return reader.fieldnames, list(reader), raw


def _json(value):
    value = value.strip()
    while value.startswith('"') and value.endswith('"'):
        value = value[1:-1].strip()
    return json.loads(value.replace('""', '"'))


def build_dungeons():
    _, current, _ = _read(os.path.join(DATA, 'dungeons.csv'))
    kept = {r['name']: r for r in current if r['saga'] == 'Marvel' and r['name'] in KEPT}
    rows = []
    for offset, d in enumerate(LADDER):
        d_id = FIRST_ID + offset
        if d['name'] in kept:
            old = kept[d['name']]
            row = dict(name=d['name'], difficulty=int(old['difficulty']), steps=_json(old['steps']),
                       rewards=_json(old['rewards']), description=old['description'])
        else:
            row = dict(name=d['name'], difficulty=d['difficulty'], steps=d['steps'],
                       rewards={"wumpa": d['wumpa'], "exp": d['exp']}, description=d['description'])
        row['id'] = d_id
        row['recommended_level'] = RECOMMENDED_LEVEL[d['name']]
        exp, wumpa = completion(row['recommended_level'])
        row['rewards'] = {"wumpa": wumpa, "exp": exp}  # what a lone player gets on top of the kills
        rows.append(row)
    return rows


def dungeon_ids():
    return {r['name']: r['id'] for r in build_dungeons()}


def write_csv(path, header, rows, keep_first=None, new_header=False):
    """Keep the non-Marvel part of a CSV as it is (same line endings), then append the Marvel rows."""
    raw = open(path, newline='', encoding='utf-8').read()
    eol = '\r\n' if raw.count('\r\n') > raw.count('\n') / 2 else '\n'
    lines = [l.rstrip('\r') for l in raw.split('\n') if l.strip()]
    parsed = list(csv.reader(io.StringIO('\n'.join(lines), newline='')))
    keep = [l for l, r in zip(lines[1:], parsed[1:]) if keep_first(r)]
    out = io.StringIO(newline='')
    writer = csv.DictWriter(out, fieldnames=header, lineterminator=eol)
    writer.writerows(rows)
    with open(path, 'w', newline='', encoding='utf-8') as f:
        first = ','.join(header) if new_header else lines[0]
        f.write(eol.join([first] + keep) + eol + out.getvalue())


def apply():
    # dungeons
    rows = build_dungeons()
    path = os.path.join(DATA, 'dungeons.csv')
    header, _, _ = _read(path)
    header = [h for h in header if h]
    if 'recommended_level' not in header:
        header.append('recommended_level')
    out_rows = [{'id': r['id'], 'name': r['name'], 'saga': 'Marvel', 'difficulty': r['difficulty'],
                 'steps': json.dumps(r['steps'], ensure_ascii=False), 'rewards': json.dumps(r['rewards']),
                 'description': r['description'], 'recommended_level': r['recommended_level']} for r in rows]
    write_csv(path, header, out_rows, keep_first=lambda r: r[2] != 'Marvel', new_header=True)

    # mobs
    path = os.path.join(DATA, 'mobs.csv')
    header, current, _ = _read(path)
    marvel_old = [r for r in current if r['saga'] == 'Marvel' and r['nome'] not in {m[0] for m in NEW_MOBS}]
    mob_rows = marvel_old + [dict(nome=n, hp=hp, attack_damage=dmg, attack_type=t, difficulty=d, series='Marvel',
                                  description=desc, speed=sp, saga='Marvel') for n, hp, dmg, t, d, desc, sp in NEW_MOBS]
    write_csv(path, header, [{k: r[k] for k in header} for r in mob_rows], keep_first=lambda r: r[8] != 'Marvel')

    # bosses
    path = os.path.join(DATA, 'bosses.csv')
    header, current, _ = _read(path)
    marvel_old = [r for r in current if r['saga'] == 'Marvel' and r['nome'] not in {b[0] for b in NEW_BOSSES}]
    boss_rows = marvel_old + [dict(nome=n, hp=hp, attack_damage=dmg, attack_type=t, series='Marvel', description=desc,
                                   loot_wumpa=w, loot_exp=e, speed=sp, abilities='[]', ai_behavior=ai,
                                   phase_config=json.dumps(ph), saga='Marvel', difficulty=d)
                              for n, hp, dmg, t, desc, w, e, sp, ai, ph, d in NEW_BOSSES]
    write_csv(path, header, [{k: r[k] for k in header} for r in boss_rows], keep_first=lambda r: r[12] != 'Marvel')
    return rows


if __name__ == '__main__':
    for r in build_dungeons():
        print(f"{r['id']:3} d{r['difficulty']:<2} {r['name']:28} {len(r['steps'])} stadi  {r['rewards']}")
    if '--apply' in sys.argv:
        apply()
        print("Written.")
