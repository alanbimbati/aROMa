"""Fills a database made by the PREVIOUS release with invented players, using plain SQL so it works whatever the schema.

CI uses it to rehearse the upgrade: old schema + these players -> new code -> scripts/verify_launch.py.
The players cover what production has: levels and EXP spread out, premium and not, titles, achievements,
old equipment ids that the new equipment file renumbers, and progress on dungeon ids the Marvel season reuses.
"""
import json
import os
import random
import sys
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, BASE_DIR)

from sqlalchemy import create_engine, text  # noqa: E402

PLAYERS = int(os.getenv('SYNTH_PLAYERS', 60))


def url():
    return (f"postgresql://{os.getenv('DB_USER', 'alan')}:{os.getenv('DB_PASSWORD', '')}"
            f"@{os.getenv('DB_HOST', 'localhost')}:{os.getenv('DB_PORT', '5432')}/{os.getenv('DB_NAME', 'aroma_bot')}")


def main():
    rng = random.Random(7)
    engine = create_engine(url())
    now = datetime.now()
    with engine.begin() as c:
        equipment_ids = [r[0] for r in c.execute(text("select id from equipment where id in (19, 41)")).all()]
        for i in range(PLAYERS):
            uid = 9_000_000 + i
            level = max(1, 120 - i * 2)
            c.execute(text(
                'insert into utente ("id_Telegram", nome, username, game_name, exp, money, livello, premium, livello_selezionato, '
                'titles, health, max_health, base_damage, stat_points, cristalli_aroma) '
                "values (:id, :n, :u, :g, :e, :m, :l, :p, 60, :t, 100, 100, 10, 0, 0)"),
                dict(id=uid, n=f"Giocatore {i}", u=f"synthetic{i}", g=f"Eroe {i}", e=level ** 2 * 900, m=rng.randint(0, 500000),
                     l=level, p=int(i % 5 == 0), t=json.dumps(["Esploratore", "Veterano"] if i % 3 else [])))
            for char in rng.sample(range(1, 200), rng.randint(1, 4)):
                c.execute(text("insert into user_character (user_id, character_id, obtained_at) values (:u, :c, :d)"),
                          dict(u=uid, c=char, d=now.date()))
            for key, value in (('total_kills', rng.randint(0, 5000)), ('boss_kills', rng.randint(0, 300)), ('total_damage', rng.randint(0, 9_000_000))):
                c.execute(text("insert into user_stat (user_id, stat_key, value, last_updated) values (:u, :k, :v, :d)"),
                          dict(u=uid, k=key, v=value, d=now))
            for key in rng.sample(['butcher', 'big_hit', 'boss_slayer', 'wumpa_collector'], rng.randint(0, 4)):
                c.execute(text("insert into user_achievement (user_id, achievement_key, current_tier, progress_value, unlocked_at, last_progress_update) "
                               "values (:u, :k, 'bronze', 100, :d, :d)"), dict(u=uid, k=key, d=now))
            for eq in equipment_ids:
                if rng.random() < 0.3:
                    c.execute(text("insert into user_equipment (user_id, equipment_id, equipped, created_at) values (:u, :e, false, :d)"),
                              dict(u=uid, e=eq, d=now))
            # old dungeons: ids 1-20, the last ones are the ids the Marvel ladder reuses
            for d_id in range(1, rng.randint(2, 21)):
                c.execute(text("insert into dungeon_progress (user_id, dungeon_def_id, best_rank, completed_at, times_completed) "
                               "values (:u, :d, 'B', :t, 1)"), dict(u=uid, d=d_id, t=now))
        # The season that just ended: the podium achievements are filed under it
        c.execute(text("insert into season (name, start_date, end_date, is_active, exp_multiplier, theme) "
                       "values ('Stagione 1: Dragonball Saga', '2026-01-10', '2026-03-02', false, 1.0, 'Dragon Ball')"))
        guild = c.execute(text("insert into guilds (name, leader_id) values ('Gilda sintetica', 9000000) returning id")).scalar()
        for eq in equipment_ids:
            c.execute(text("insert into crafting_queue (guild_id, user_id, equipment_id, start_time, completion_time, status) "
                           "values (:g, 9000000, :e, :t, :t, 'pending')"), dict(g=guild, e=eq, t=now))
    print(f"{PLAYERS} synthetic players inserted")


if __name__ == '__main__':
    main()
