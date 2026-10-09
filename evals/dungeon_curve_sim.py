"""How many dungeons does a level cost, and what does that do to a 90-day season?

    python evals/dungeon_curve_sim.py [--runs 300]

Reuses progression_sim (mob EXP rule 'proposta', chat, profiles). Only the dungeon payout changes: a clear pays
step(level) / n(level), n being the dungeons a player needs to go up one level.
"""
import argparse
import random
import statistics
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import progression_sim as ps  # noqa: E402
from services import dungeon_rewards as dr  # noqa: E402


def n_dungeons(level, start, end, shape):
    """Dungeons per level: `start` at level 1, `end` at level 100, along `shape` (1 = straight line)."""
    t = ((min(level, 100) - 1) / 99) ** shape
    return start + (end - start) * t


def make_day(start, end, shape):
    def day(exp, profile, state, rule):
        level = ps.level_of(exp)
        g = {'mob': 0, 'dungeon': 0, 'chat': 0}
        k = profile['kills']
        for _ in range(int(k) + (1 if random.random() < k - int(k) else 0)):
            g['mob'] += ps.world_kill_exp(level, rule)
        g['chat'] += sum(random.randint(1, 10) + 1 for _ in range(profile['messages']))
        reach_cut = 2 if profile['team'] <= 1 else 4 + 2 * (profile['team'] - 1)
        open_ones = [i for i, r in enumerate(ps.RECOMMENDED) if i <= state['cleared'] and level >= r - reach_cut]
        for i in sorted(open_ones, reverse=True)[:profile['dungeons']]:
            r = ps.RECOMMENDED[i]
            # paid on the player's own level step, nudged by how the dungeon compares with them
            ratio = min(1.5, max(0.6, r / max(1, level)))
            g['dungeon'] += int(ps.step(level) / n_dungeons(level, start, end, shape) * ratio * dr.team_bonus(profile['team']))
            state['cleared'] = max(state['cleared'], i + 1)
        return g
    return day


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--runs', type=int, default=300)
    args = ap.parse_args()
    variants = [('oggi (2 fissi)', 2, 2, 1), ('2 -> 4 lineare', 2, 4, 1), ('2 -> 6 lineare', 2, 6, 1),
                ('2 -> 8 lineare', 2, 8, 1), ('2 -> 8 lenta (^2)', 2, 8, 2), ('2 -> 12 lenta (^2)', 2, 12, 2)]
    print(f"{'curva':20} {'profilo':22} {'100?':>5} {'giorno':>7}  livello al giorno 7/14/30/45/60/75/90   % EXP da dungeon")
    for label, a, b, s in variants:
        ps.day = make_day(a, b, s)
        for name in ('molto attivo', 'ogni giorno', 'cinque giorni su 7', 'tre giorni su 7'):
            random.seed(5)
            r = ps.run(ps.PROFILES[name], 90, args.runs, 'proposta')
            lv = '/'.join(str(v) for v in r['level_at'].values())
            print(f"{label:20} {name:22} {r['reach_100']*100:>4.0f}% {str(r['median_day'] or '-'):>7}  {lv:<38} {r['mix']['dungeon']}%")
        print()
    print("dungeon per salire di livello (n) alla curva:")
    for label, a, b, s in variants:
        print(f"  {label:20}", ' '.join(f"L{l}:{n_dungeons(l, a, b, s):.1f}" for l in (1, 10, 25, 50, 75, 99)))
