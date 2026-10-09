"""Keep players' equipment when equipment.csv ids change. Run BEFORE the new code seeds the table.

The CSV used to have two rows with id 19 and two with id 41; the later row won in the database.
The CSV now gives the losers their own ids, so the rows the players actually own have to move first.
"""
import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, BASE_DIR)

from sqlalchemy import text
from database import Database

# (name, id in the database today, id in the new CSV)
REMAPS = [("Gi di Kame", 19, 24), ("Leggings di Ferro", 41, 43)]


def run(apply):
    session = Database().get_session()
    try:
        for name, old_id, new_id in REMAPS:
            row = session.execute(text("select name from equipment where id = :i"), {"i": old_id}).first()
            if not row or row[0] != name:
                print(f"{name}: id {old_id} is {row[0] if row else 'empty'}, nothing to move")
                continue
            if not session.execute(text("select 1 from equipment where id = :i"), {"i": new_id}).first():
                session.execute(text(
                    "insert into equipment (id, name, slot, rarity, min_level, stats_json, crafting_time, "
                    "crafting_requirements, description, set_name, effect_type) "
                    "select :n, name, slot, rarity, min_level, stats_json, crafting_time, crafting_requirements, "
                    "description, set_name, effect_type from equipment where id = :o"), {"n": new_id, "o": old_id})
            for table in ("user_equipment", "crafting_queue"):
                moved = session.execute(text(f"update {table} set equipment_id = :n where equipment_id = :o"),
                                        {"n": new_id, "o": old_id}).rowcount
                print(f"{name}: {moved} rows of {table} moved {old_id} -> {new_id}")
        if apply:
            session.commit()
            print("Applied.")
        else:
            session.rollback()
            print("Dry run: nothing changed. Use --apply.")
    finally:
        session.close()


if __name__ == '__main__':
    run('--apply' in sys.argv)
