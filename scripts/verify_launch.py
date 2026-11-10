"""Checks a database before and after the Marvel launch: what must change did, and nothing else was lost.

    python scripts/verify_launch.py --snapshot before.json   # run on the database BEFORE the launch
    python scripts/verify_launch.py --check before.json      # run AFTER it; exit code 1 if anything is off

The same script runs against a copy of production and, in CI, against a synthetic database built by the
previous release's code.
"""
import csv
import json
import os
import sys
from datetime import datetime, timedelta

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from sqlalchemy import inspect, text  # noqa: E402

from database import Database  # noqa: E402

# Tables the launch is allowed to change; every other table must have exactly the rows it had before.
from scripts.season_wipe import RESET_TABLES  # noqa: E402

# Tables the launch is allowed to change; every other table must have exactly the rows it had before.
MAY_CHANGE = set(RESET_TABLES) | {
    'user_achievement',     # only grows: the podium gets its achievements
    'utente',               # everyone is reset
    'season', 'season_reward',  # the Marvel season and its pass
    'achievement',          # the podium achievement definitions
    'system_state',         # remembers the wipe
    'equipment',            # new rows (Radar, remapped ids)
    'market_listings', 'nostr_badge_outbox',  # open listings and unsent badges are cleared
}


def tables(db):
    return sorted(inspect(db.engine).get_table_names())


def counts(db):
    with db.engine.connect() as c:
        return {t: c.execute(text(f'select count(*) from "{t}"')).scalar() for t in tables(db)}


def snapshot(path):
    db = Database()
    with db.engine.connect() as c:
        extra = {
            'equipment_by_user': {str(r[0]): r[1] for r in c.execute(text(
                'select user_id, count(*) from user_equipment group by user_id')).all()},
            'achievements_by_user': {str(r[0]): r[1] for r in c.execute(text(
                'select user_id, count(*) from user_achievement where current_tier is not null group by user_id')).all()},
            'titles': {str(r[0]): r[1] for r in c.execute(text('select "id_Telegram", titles from utente')).all()},
            'top3': [r[0] for r in c.execute(text('select "id_Telegram" from utente order by exp desc limit 3')).all()],
            'worn_by_top3': [r[0] for r in c.execute(text(
                'select id from user_equipment where equipped = true and user_id in '
                '(select "id_Telegram" from utente order by exp desc limit 3)')).all()],
            'premium_users': c.execute(text('select count(*) from utente where premium = 1')).scalar(),
            'money': {str(r[0]): r[1] for r in c.execute(text('select "id_Telegram", money from utente')).all()},
        }
    with open(path, 'w') as f:
        json.dump({'counts': counts(db), **extra}, f)
    print(f"snapshot saved: {len(tables(db))} tables, {sum(counts(db).values())} rows")


class Report:
    def __init__(self):
        self.failed = 0

    def check(self, ok, label, detail=''):
        print(f"  {'✅' if ok else '❌'} {label}{(' — ' + str(detail)) if detail else ''}")
        if not ok:
            self.failed += 1


def check(path):
    before = json.load(open(path))
    db = Database()
    r = Report()
    now = counts(db)
    with db.engine.connect() as c:
        q = lambda sql, **p: c.execute(text(sql), p)  # noqa: E731

        print("The season")
        seasons = q("select id, name, theme, start_date, end_date from season where is_active").all()
        r.check(len(seasons) == 1, "exactly one active season", [s[1] for s in seasons])
        season = seasons[0] if seasons else None
        r.check(bool(season) and season[2] == 'Marvel', "it is the Marvel season")
        if season:
            span = season[4] - season[3]
            r.check(timedelta(days=89) <= span <= timedelta(days=91), "it lasts 90 days", span)
            rewards = q("select count(*) from season_reward where season_id = :s", s=season[0]).scalar()
            with open(os.path.join(BASE_DIR, 'data', 'season_marvel_rewards.csv'), newline='', encoding='utf-8') as f:
                expected = len(list(csv.DictReader(f)))
            r.check(rewards == expected, "the Season Pass has all its rewards", f"{rewards}/{expected}")
        r.check(q("select value from system_state where key = 'season_wipe_done'").first() is not None,
                "the wipe is remembered, so it cannot run twice")

        print("Players")
        users = q('select count(*) from utente').scalar()
        r.check(users == before['counts']['utente'], "no player lost", f"{users}")
        not_reset = q('select count(*) from utente where livello <> 1 or exp <> 0').scalar()
        r.check(not_reset == 0, "everyone back to level 1 with no EXP", f"{not_reset} not reset")
        stan = None
        with open(os.path.join(BASE_DIR, 'data', 'characters.csv'), newline='', encoding='utf-8') as f:
            stan = next(int(x['id']) for x in csv.DictReader(f) if x['nome'] == 'Stan Lee')
        wrong_char = q('select count(*) from utente where livello_selezionato <> :s', s=stan).scalar()
        r.check(wrong_char == 0, "everyone starts as Stan Lee", f"{wrong_char} different")
        owners = q('select count(distinct user_id), count(*) from user_character').first()
        r.check(owners[0] == users and owners[1] == users, "each player owns exactly that one character", owners)
        own2 = q('select count(*) from character_ownership').scalar()
        r.check(own2 == users, "the exclusive-ownership table agrees", own2)
        ghosts = q('select count(*) from user_character uc left join utente u on u."id_Telegram" = uc.user_id '
                   'where u."id_Telegram" is null').scalar()
        r.check(ghosts == 0, "no character owned by a player who does not exist")

        print("The podium")
        top = before['top3']
        prizes = [10000, 5000, 2000]
        for place, uid in enumerate(top):
            keys = {x[0] for x in q("select achievement_key from user_achievement where user_id = :u and current_tier is not null "
                                    "and achievement_key like 'season_%'", u=uid).all()}
            has = lambda suffix: any(k.endswith(suffix) for k in keys)  # noqa: E731
            r.check(has(f"_podium_{place + 1}") and has('_podium'),
                    f"place {place + 1} ({uid}) has the place and the podium achievements", sorted(keys))
            r.check(has('_champion') == (place == 0), f"place {place + 1}: champion achievement only for the winner")
            money = q('select money from utente where "id_Telegram" = :u', u=uid).scalar()
            r.check(money == prizes[place], f"place {place + 1} ({uid}) has just the prize, not the old Wumpa", money)
        others = q('select count(*) from utente where money <> 0 and "id_Telegram" <> all(:t)', t=top).scalar()
        r.check(others == 0, "everyone else has no Wumpa", f"{others} with some")
        prize_items = q("select count(*) from user_equipment ue join equipment e on e.id = ue.equipment_id "
                        "where e.name in ('Radar cerca sfere', 'Orecchini Potara') and ue.user_id = any(:t)", t=top).scalar()
        r.check(prize_items == 2 * len(top), "the podium got the Radar and the Potara", prize_items)
        worn = before.get('worn_by_top3', [])
        still = q('select count(*) from user_equipment where id = any(:ids) and equipped = true', ids=worn).scalar()
        r.check(still == len(worn), "the podium keeps the items they were wearing", f"{still}/{len(worn)}")
        eq_total = q('select count(*) from user_equipment').scalar()
        r.check(eq_total == len(worn) + 2 * len(top), "nobody else has any equipment", eq_total)

        print("Achievements are kept")
        kept = {u: n for u, n in before['achievements_by_user'].items()}
        now_ach = {str(x[0]): x[1] for x in q('select user_id, count(*) from user_achievement where current_tier is not null group by user_id').all()}
        added = now['user_achievement'] - before['counts']['user_achievement']
        r.check(added == 2 * len(top) + 1, "the podium got exactly its achievements: place and podium each, champion for the winner", added)
        lost_ach = {u: (n, now_ach.get(u, 0)) for u, n in kept.items() if now_ach.get(u, 0) < n}
        r.check(not lost_ach, "nobody lost an achievement", lost_ach)
        lost_titles = []
        for uid, titles in before['titles'].items():
            held = json.loads(q('select titles from utente where "id_Telegram" = :u', u=int(uid)).scalar() or '[]')
            if not set(json.loads(titles or '[]')) <= set(held):
                lost_titles.append(uid)
        r.check(not lost_titles, "nobody lost a title", lost_titles[:5])

        print("Everyone starts from zero")
        for table in RESET_TABLES:
            if table in now and table not in ('user_equipment', 'user_character', 'character_ownership'):
                n = q(f'select count(*) from "{table}"').scalar()
                r.check(n == 0, f"{table} is empty", n)
        r.check(now.get('user_stat', 0) == 0, "no stats left: nothing can unlock again by itself")
        dirty = q('select count(*) from utente where chat_exp <> 0 or stat_points <> livello * 2 or allocated_health <> 0 or allocated_damage <> 0').scalar()
        r.check(dirty == 0, "only the level-1 points, no allocated stats, no chat EXP", dirty)

        print("Nothing else was touched")
        lost = {t: (before['counts'][t], now.get(t)) for t in before['counts']
                if t not in MAY_CHANGE and now.get(t) != before['counts'][t]}
        r.check(not lost, "every other table has exactly the rows it had", lost or f"{len(before['counts']) - len(MAY_CHANGE & set(before['counts']))} tables compared")
        r.check(q('select count(*) from utente where premium = 1').scalar() == before.get('premium_users', q('select count(*) from utente where premium = 1').scalar()),
                "premium accounts are still premium")

        print("Equipment still points at what it did")
        for table in ('user_equipment', 'crafting_queue'):
            if table in now:
                dangling = q(f'select count(*) from {table} t left join equipment e on e.id = t.equipment_id '
                             'where e.id is null').scalar()
                r.check(dangling == 0, f"{table}: every reference resolves", f"{dangling} dangling")

        print("Dungeons")
        marvel_ids = {int(x['id']) for x in csv.DictReader(open(os.path.join(BASE_DIR, 'data', 'dungeons.csv'), newline='', encoding='utf-8'),
                                                         skipinitialspace=True) if x['saga'] == 'Marvel'}
        stale = q('select count(*) from dungeon_progress').scalar()
        r.check(stale == 0, "no player starts with any dungeon already cleared", f"{stale} left")
        known = {int(x['id']) for x in csv.DictReader(open(os.path.join(BASE_DIR, 'data', 'dungeons.csv'), newline='', encoding='utf-8'),
                                                    skipinitialspace=True)}
        orphans = q('select count(*) from dungeon_progress where dungeon_def_id <> all(:ids)', ids=list(known)).scalar()
        r.check(orphans == 0, "no progress on dungeons that no longer exist", orphans)

    print(f"\n{'ALL CHECKS PASSED' if not r.failed else str(r.failed) + ' CHECK(S) FAILED'}")
    return 1 if r.failed else 0


if __name__ == '__main__':
    if '--snapshot' in sys.argv:
        snapshot(sys.argv[sys.argv.index('--snapshot') + 1])
    elif '--check' in sys.argv:
        sys.exit(check(sys.argv[sys.argv.index('--check') + 1]))
    else:
        sys.exit(__doc__)
