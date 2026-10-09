"""Balance eval: can a player of the intended level get through each Marvel dungeon, and does it get harder smoothly?

The mobs and bosses are spawned by the game's own code (so their stats scale exactly as in play); the player is a
deliberately plain build: every level gives 2 stat points (as in the game), spent half on damage, 30% on health,
the rest on mana, and the player uses the best character its level allows. Fights run turn by turn, solo, no potions.

    python evals/balance_sim.py [--runs 40] [--season Marvel]     # prints the table, exit code 1 if a gate fails
Gates (the same ones the judges are held to):
  1. the first dungeon is won by a level-1 player with most of its health left,
  2. every dungeon is won at its recommended level (at least 25% health left, in 90% of the spawns),
  3. no cliff: HP margin never drops more than 35 points from one dungeon to the next.
"""
import argparse
import json
import os
import random
import statistics
import sys
import types

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)
os.environ.setdefault('TEST', '1')
sys.modules.setdefault('main', types.ModuleType('main'))

from database import Database  # noqa: E402
from services.dungeon_service import DungeonService  # noqa: E402
from services.pve_service import PvEService  # noqa: E402

CHAT = -987654321


def player(level):
    points = 2 * level
    dmg_pts, hp_pts, mana_pts = round(points * 0.5), round(points * 0.3), points - round(points * 0.5) - round(points * 0.3)
    return dict(
        hp=100 + 10 * hp_pts,
        dmg=10 + 2 * dmg_pts,
        mana=50 + 5 * mana_pts,
        special=20 + 6 * level,       # the best character it can use: same formula the roster follows
        cost=10 + 2 * level,
        crit=0.05, crit_mult=1.5,
    )


def fight(pl, mobs):
    """One step. mobs: list of dicts(hp, dmg). Returns the player's remaining hp."""
    hp, mana = pl['hp'], pl['mana']
    mobs = [dict(m) for m in mobs]
    for _ in range(400):
        if not mobs:
            return hp
        use_special = mana >= pl['cost']
        hit = pl['dmg'] + (pl['special'] if use_special else 0)
        if use_special:
            mana -= pl['cost']
        hit *= 1 + pl['crit'] * (pl['crit_mult'] - 1)
        mobs[0]['hp'] -= hit
        if mobs[0]['hp'] <= 0:
            mobs.pop(0)
        hp -= sum(m['dmg'] for m in mobs)
        if hp <= 0:
            return 0
    return hp


def spawn(pve, session, entry, levels=(None, None), weight=1.0):
    """What the game would put on the field for one entry of a dungeon step, at the levels the game would use."""
    out = []
    if 'mobs' in entry:
        for m in entry['mobs']:
            for _ in range(m.get('count', 1)):
                ok, _, mob_id = pve.spawn_specific_mob(mob_name=m['name'], chat_id=CHAT, ignore_limit=True, session=session, level=levels[0], weight=weight)
                out.append(mob_id)
    if 'boss' in entry:
        ok, _, mob_id = pve.spawn_boss(boss_name=entry['boss'], chat_id=CHAT, ignore_limit=True, session=session, level=levels[1], weight=weight)
        out.append(mob_id)
    return out


def run(runs, theme):
    from models.pve import Mob
    db = Database()
    pve, ds = PvEService(), DungeonService()
    ids = [i for i, d in sorted(ds.dungeons_cache.items()) if d.get('saga', '').lower() == theme.lower()]
    rows = []
    for d_id in ids:
        d = ds.dungeons_cache[d_id]
        level = d.get('recommended_level') or (d['difficulty'] - 1) * 10 + 1
        margins = []
        for _ in range(runs):
            session = db.get_session()
            try:
                pl = player(level)
                hp = pl['hp']
                for n, step in enumerate(d['steps'], 1):
                    mob_ids = spawn(pve, session, step, ds.stage_levels(d, n), ds.enemy_weight(d))
                    mobs = [dict(hp=m.max_health, dmg=m.attack_damage) for m in session.query(Mob).filter(Mob.id.in_(mob_ids)).all()]
                    pl_now = dict(pl, hp=hp)
                    hp = fight(pl_now, mobs)
                    if hp <= 0:
                        break
                margins.append(100 * hp / pl['hp'])
            finally:
                session.rollback()
                session.close()
        rows.append(dict(id=d_id, name=d['name'], difficulty=d['difficulty'], level=level,
                         win=sum(1 for m in margins if m > 0) / runs, margin=statistics.median(margins),
                         p10=sorted(margins)[max(0, int(runs * 0.1) - 1)]))
    return rows


def judge(rows):
    problems = []
    first = rows[0]
    if first['margin'] < 50:
        problems.append(f"first dungeon ({first['name']}) leaves a level-{first['level']} player only {first['margin']:.0f}% health")
    for r in rows:
        if r['p10'] < 25:
            problems.append(f"{r['name']}: 10% of spawns leave a level-{r['level']} player under 25% health (worst decile {r['p10']:.0f}%)")
    for a, b in zip(rows, rows[1:]):
        if a['margin'] - b['margin'] > 35:
            problems.append(f"cliff between {a['name']} ({a['margin']:.0f}%) and {b['name']} ({b['margin']:.0f}%)")
    return problems


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--runs', type=int, default=40)
    ap.add_argument('--season', default='Marvel')
    ap.add_argument('--json')
    args = ap.parse_args()
    random.seed(11)
    rows = run(args.runs, args.season)
    print(f"{'dungeon':28} diff  lvl   win   median HP left   worst decile")
    for r in rows:
        print(f"{r['name']:28} {r['difficulty']:>4} {r['level']:>4}  {r['win']*100:>3.0f}%   {r['margin']:>8.0f}%       {r['p10']:>8.0f}%")
    problems = judge(rows)
    print('\n' + ('BALANCE OK' if not problems else 'PROBLEMS:\n  - ' + '\n  - '.join(problems)))
    if args.json:
        json.dump(dict(rows=rows, problems=problems), open(args.json, 'w'), indent=2)
    sys.exit(1 if problems else 0)
