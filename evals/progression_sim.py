"""How fast does a player level in a 90-day season? Monte Carlo over the game's own formulas.

    python evals/progression_sim.py [--days 90] [--runs 200] [--json out.json]

Every number the game decides (EXP curve, mob EXP, dungeon purse, caps) is the game's own; what a player *does* in a
day (profiles below) is an assumption and is printed with the result. Target: a player who plays every day reaches
level 100 near the end of the season, one who plays half the days does not.
"""
import argparse
import csv
import json
import os
import random
import statistics
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)
from services import dungeon_rewards as dr  # noqa: E402

CAP = 100
RECOMMENDED = [5, 9, 14, 20, 27, 35, 43, 51, 60, 70, 80, 90, 100]


def need(level):
    """EXP to be at `level` (services/leveling_service.py)."""
    return int(10 * level ** 2.5) if level > 1 else 0


def level_of(exp):
    lvl = 1
    while lvl < CAP and exp >= need(lvl + 1):
        lvl += 1
    return lvl


def world_mobs():
    rows = [r for r in csv.DictReader(open(os.path.join(BASE, 'data', 'mobs.csv'), encoding='utf-8')) if r['saga'] == 'Marvel']
    return [(int(r['difficulty']), float(r['hp'])) for r in rows]


MOBS = world_mobs()

# What a player does on a day they play, tuned on the 50 days of real history before the Marvel launch (323 players):
# those who played nearly every day got 1-4 world-mob kills a day and ~12 chat rewards; only the very top (one player
# in 323) did 13 kills a day. 'kills' are kills they get credit for (a mob is shared by damage), 'dungeons' the most
# they fit in a day, 'team' how many play together (a team goes in at a lower level and earns a bonus).
PROFILES = {
    'molto attivo':       dict(days_per_week=7.0, kills=8.0, messages=40, dungeons=2, team=3),
    'ogni giorno':        dict(days_per_week=7.0, kills=2.5, messages=12, dungeons=1, team=3),
    'cinque giorni su 7': dict(days_per_week=5.0, kills=2.5, messages=12, dungeons=1, team=3),
    'tre giorni su 7':    dict(days_per_week=3.0, kills=2.0, messages=10, dungeons=1, team=2),
    'una volta a settimana': dict(days_per_week=1.0, kills=2.0, messages=10, dungeons=1, team=2),
}
RULES = ('attuale', 'proposta')
MOB_FRACTION = 0.03       # 'proposta': a kill pays this share of the player's level step per mob tier...
MOB_RATIO = (0.25, 2.0)   # ...times how the mob's level compares with the player's (weak mobs pay less, strong ones more)


def step(level):
    return max(100, need(level + 1) - need(level))


def world_kill_exp(level, rule):
    """EXP of one world-mob kill for a player of `level` (full share). 'attuale' is services/reward_service.py as it is;
    'proposta' pays a fraction of the player's own level step, so the curve does not depend on how high mobs reach."""
    for _ in range(4):  # a player does not take on a mob far beyond what they can beat
        diff, hp = random.choice(MOBS)
        if diff <= level // 8 + 2:
            break
    mob_level = random.randint((diff - 1) * 10 + 1, diff * 10)
    if rule == 'proposta':
        ratio = min(MOB_RATIO[1], max(MOB_RATIO[0], mob_level / max(1, level)))
        return max(1, int(step(level) * MOB_FRACTION * diff * ratio * random.uniform(0.9, 1.1)))
    hp_scaling = min(3.0, (hp / 1000) ** 0.35) if hp > 1000 else 1.0
    pool = int(mob_level * 5 * hp_scaling * diff ** 1.8 * random.uniform(0.9, 1.1))
    factor = 1.0
    if mob_level > level:
        factor = 1.0 + min(2.0, (mob_level - level) * 0.02)
    elif level > mob_level + 15:
        factor = 0.5
    return min(int(pool * factor), int(step(level) * 1.5))


def day(exp, profile, state, rule):
    level = level_of(exp)
    gained = {'mob': 0, 'dungeon': 0, 'chat': 0}
    k = profile['kills']
    for _ in range(int(k) + (1 if random.random() < k - int(k) else 0)):
        gained['mob'] += world_kill_exp(level, rule)
    gained['chat'] += sum(random.randint(1, 10) + 1 for _ in range(profile['messages']))
    reach_cut = 2 if profile['team'] <= 1 else 4 + 2 * (profile['team'] - 1)  # a team goes in earlier than a lone player
    open_ones = [i for i, r in enumerate(RECOMMENDED) if i <= state['cleared'] and level >= r - reach_cut]
    for i in sorted(open_ones, reverse=True)[:profile['dungeons']]:  # the best ones they can do, once each
        gained['dungeon'] += int(dr.budget(RECOMMENDED[i])[0] * dr.team_bonus(profile['team']))
        state['cleared'] = max(state['cleared'], i + 1)
    return gained


def run(profile, days, runs, rule):
    finish, curve, mix = [], [[] for _ in range(days + 1)], {'mob': 0, 'dungeon': 0, 'chat': 0}
    for _ in range(runs):
        exp, state, reached = 0, {'cleared': 0}, None
        play_p = profile['days_per_week'] / 7
        for d in range(1, days + 1):
            if random.random() < play_p:
                g = day(exp, profile, state, rule)
                exp += sum(g.values())
                for k, v in g.items():
                    mix[k] += v
            curve[d].append(level_of(exp))
            if reached is None and level_of(exp) >= CAP:
                reached = d
        finish.append(reached)
    done = [f for f in finish if f]
    total = sum(mix.values()) or 1
    return dict(reach_100=len(done) / runs, median_day=statistics.median(done) if done else None,
                level_at={d: int(statistics.median(curve[d])) for d in (7, 14, 30, 45, 60, 75, 90) if d <= days},
                mix={k: round(100 * v / total) for k, v in mix.items()})


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--days', type=int, default=90)
    ap.add_argument('--runs', type=int, default=300)
    ap.add_argument('--rule', choices=RULES + ('both',), default='both')
    ap.add_argument('--json')
    args = ap.parse_args()
    out = {}
    for rule in (RULES if args.rule == 'both' else (args.rule,)):
        random.seed(5)
        print(f"\nEXP dei mob: {rule}")
        print(f"{'profilo':24} {'arriva a 100':>12} {'mediana':>8}   livello al giorno 7/14/30/45/60/75/90       EXP da mob/dungeon/chat")
        for name, p in PROFILES.items():
            r = run(p, args.days, args.runs, rule)
            out[f'{rule}/{name}'] = r
            lv = '/'.join(str(v) for v in r['level_at'].values())
            print(f"{name:24} {r['reach_100']*100:>11.0f}% {str(r['median_day'] or '-'):>8}   {lv:<38} {r['mix']['mob']}% / {r['mix']['dungeon']}% / {r['mix']['chat']}%")
    if args.json:
        json.dump(out, open(args.json, 'w'), indent=2)
