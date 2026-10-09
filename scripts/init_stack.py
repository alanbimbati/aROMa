"""Runs once per `docker compose up`, before the bot and the web app start. Safe to repeat: every step is idempotent.

  1. waits for the database
  2. if the Marvel launch is requested (MARVEL_LAUNCH=1) and has not happened yet: takes a backup first
  3. keeps players' equipment when equipment ids change
  4. creates/updates the schema and the seed data
  5. the Marvel launch itself (season wipe), once, remembered in the database
  6. pictures: Marvel art in the folder the bot reads, badge images for Nostr
"""
import glob
import os
import subprocess
import sys
import time
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)
PY = sys.executable


def step(title):
    print(f"\n=== {title}", flush=True)


def run(*cmd, check=True, env=None):
    return subprocess.run(cmd, cwd=BASE_DIR, check=check, env={**os.environ, **(env or {})}).returncode


def wait_for_database(tries=40):
    from database import Database
    from sqlalchemy import text
    for _ in range(tries):
        try:
            with Database().engine.connect() as c:
                c.execute(text("select 1"))
            return
        except Exception as e:
            print(f"  database not ready ({str(e)[:60]}), retrying...", flush=True)
            time.sleep(3)
    sys.exit("The database never became reachable.")


def has_table(name):
    from database import Database
    from sqlalchemy import inspect
    return inspect(Database().engine).has_table(name)


def launch_pending():
    if os.getenv('MARVEL_LAUNCH') != '1':
        return False
    if not has_table('system_state'):
        return True
    from database import Database
    from models.system_state import SystemState
    session = Database().get_session()
    try:
        return not SystemState.get_val(session, 'season_wipe_done', None)
    finally:
        session.close()


def backup():
    os.makedirs(os.path.join(BASE_DIR, 'backups'), exist_ok=True)
    target = os.path.join(BASE_DIR, 'backups', f"pre_marvel_{datetime.now():%Y%m%d_%H%M%S}.dump")
    env = {'PGPASSWORD': os.getenv('DB_PASSWORD', '')}
    code = run('pg_dump', '-h', os.getenv('DB_HOST', 'postgres'), '-p', os.getenv('DB_PORT', '5432'),
               '-U', os.getenv('DB_USER', 'alan'), '-Fc', '-f', target, os.getenv('DB_NAME', 'aroma_bot'), check=False, env=env)
    if code != 0 or not os.path.exists(target) or os.path.getsize(target) == 0:
        sys.exit("Backup failed: the Marvel launch is NOT run without one.")
    print(f"  backup saved to {target} ({os.path.getsize(target) // 1024} KB)")


def hand_back_ownership():
    """The init container runs as root: give what it created to whoever owns the mounted data folder."""
    try:
        owner = os.stat(os.path.join(BASE_DIR, 'data'))
        if os.geteuid() != 0 or owner.st_uid == 0:
            return
        for folder in ('assets', 'images', 'backups', 'cache'):
            for root, dirs, files in os.walk(os.path.join(BASE_DIR, folder)):
                for name in dirs + files:
                    path = os.path.join(root, name)
                    if os.lstat(path).st_uid == 0:
                        os.chown(path, owner.st_uid, owner.st_gid, follow_symlinks=False)
            os.chown(os.path.join(BASE_DIR, folder), owner.st_uid, owner.st_gid) if os.path.isdir(os.path.join(BASE_DIR, folder)) else None
    except Exception as e:
        print(f"  could not hand back ownership: {e}")


def main():
    step("Database")
    wait_for_database()

    pending = launch_pending()
    if pending and has_table('utente'):
        step("Backup before the Marvel launch")
        backup()

    if has_table('equipment'):
        step("Equipment ids")
        run(PY, 'scripts/migrations/remap_equipment_ids.py', '--apply')

    step("Schema and seed data")
    run(PY, 'db_setup.py')

    if pending:
        step("Marvel launch (season wipe)")
        run(PY, 'scripts/season_wipe.py', '--apply')

    step("Pictures")
    marvel = os.path.join(BASE_DIR, 'assets', 'characters', 'marvel')
    if os.getenv('FETCH_IMAGES', '1') == '1' and len(glob.glob(os.path.join(marvel, '*.jpg'))) < 100:
        print("  Marvel illustrations missing: fetching them (a few minutes, first start only)")
        run(PY, 'scripts/fetch_marvel_images.py', check=False)
    run(PY, 'scripts/install_marvel_images.py')
    if not glob.glob(os.path.join(BASE_DIR, 'assets', 'badges', '*.png')):
        print("  generating the badge images")
        run(PY, 'scripts/generate_badge_images.py', check=False)
    hand_back_ownership()
    print("\nInit done.", flush=True)


if __name__ == '__main__':
    main()
