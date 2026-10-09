import os
import sys
import csv
import json
import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from sqlalchemy import create_engine, desc
from sqlalchemy.orm import sessionmaker
from database import Database
from models.user import Utente
from models.equipment import Equipment, UserEquipment
from models.system import UserCharacter
from models.inventory import UserItem
from models.character_ownership import CharacterOwnership
from models.seasons import Season
from services.season_manager import SeasonManager
from models.system_state import SystemState

data_dir = os.path.join(BASE_DIR, 'data')
equip_path = os.path.join(data_dir, 'equipment.csv')

def prepare_equip():
    max_eq_id = 0
    radar_already_exists = False
    with open(equip_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row['name'] == 'Radar cerca sfere':
                radar_already_exists = True
            max_eq_id = max(max_eq_id, int(row['id']))
            
    if not radar_already_exists:
        radar_id = max_eq_id + 1
        new_item = [
            radar_id, 'Radar cerca sfere', 'accessory2', 5, 1, '{"speed": 5}', 0, '{}', 
            'Un radar speciale che aumenta il drop rate delle Sfere del Drago del 5% e ricorda la vittoria nella prima stagione.', 'Esclusivo', 'dragon_radar'
        ]
        with open(equip_path, 'a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(new_item)
        print("Radar aggiunto a equipment.csv")

# Per-player progression that starts over for everyone. What stays is who the player is (account, name,
# premium, crystals bought with money, paid skins, Nostr link), the history (events, fights, past seasons) and
# what they earned: achievements, with their titles and badges, are never taken back.
RESET_TABLES = [
    'user_stat',             # the new season's achievements count from zero; tiers already earned stay
    'dungeon_progress', 'user_resources', 'user_refined_materials', 'alchemy_queue', 'refinery_queue',
    'crafting_queue', 'garden_slots', 'user_equipment', 'user_item', 'user_mounts', 'user_transformation',
    'parry_stats', 'parry_states', 'user_character', 'character_ownership',
]


def reset_everyone(session, stan_lee_id, keep_equipped=()):
    """Back to level 1 for every player, with nothing but Stan Lee (and, for the players in keep_equipped, the items they
    wear). Returns the number of players."""
    from sqlalchemy import inspect, text
    present = set(inspect(session.get_bind()).get_table_names())
    counts = {}
    if 'user_equipment' in present:
        keep = list(keep_equipped)
        counts['user_equipment'] = session.execute(
            text('delete from user_equipment where not (equipped = true and user_id = any(:keep))'), {'keep': keep}).rowcount
    for table in RESET_TABLES:
        if table in present and table != 'user_equipment':
            counts[table] = session.execute(text(f'delete from "{table}"')).rowcount
    if 'market_listings' in present:
        counts['market_listings (active)'] = session.execute(text("delete from market_listings where status = 'active'")).rowcount
    print("Azzerato: " + ", ".join(f"{t} {n}" for t, n in counts.items() if n))

    users = session.query(Utente).all()
    for u in users:
        u.livello = 1
        u.exp = 0
        u.chat_exp = 0
        u.health = u.max_health = 100
        u.current_hp = 100
        u.mana = u.max_mana = 50
        u.current_mana = 50
        u.base_damage = 10
        u.stat_points = 2  # what the game gives at level 1 (livello * 2); the bot would put them back anyway
        u.resistance = 0
        u.crit_chance = 0
        u.speed = 0
        u.allocated_health = u.allocated_mana = u.allocated_damage = 0
        u.allocated_speed = u.allocated_resistance = u.allocated_crit = 0
        u.points = 0
        u.livello_selezionato = stan_lee_id
        u.current_transformation = None
        u.transformation_expires_at = None
        u.active_status_effects = None
        u.shield_hp = u.shield_max_hp = 0
        u.last_character_change = None
        u.resting_since = None
        u.vigore_until = None
        u.invincible_until = None
        u.luck_boost = 0
        u.daily_wumpa_earned = 0
        session.add(UserCharacter(user_id=u.id_telegram, character_id=stan_lee_id, obtained_at=datetime.date.today()))
        session.add(CharacterOwnership(user_id=u.id_telegram, character_id=stan_lee_id))
    return users


def run_wipe(apply):
    print("Connessione al DB in corso...")
    db = Database()
    session = db.get_session()
    if apply and SystemState.get_val(session, 'season_wipe_done', None):
        session.close()
        print("Il wipe è già stato eseguito su questo database: non lo ripeto.")
        return False

    stan_lee_id = None
    with open(os.path.join(data_dir, 'characters.csv'), 'r', encoding='utf-8') as f:
        for row in csv.DictReader(f):
            if row['nome'] == 'Stan Lee':
                stan_lee_id = int(row['id'])
                break
    if stan_lee_id is None:
        sys.exit("Stan Lee non trovato in characters.csv: il wipe non può assegnare il personaggio iniziale.")

    # The equipment table is seeded from the CSV at boot: the prizes must already be there.
    prizes = {}
    for name in ('Radar cerca sfere', 'Orecchini Potara'):
        item = session.query(Equipment).filter_by(name=name).first()
        if not item:
            sys.exit(f"'{name}' non è nella tabella equipment: avvia prima il bot con il codice nuovo.")
        prizes[name] = item.id

    closing_season = session.query(Season).filter_by(is_active=True).order_by(Season.id.desc()).first() \
        or session.query(Season).filter_by(theme="Dragon Ball").order_by(Season.id.desc()).first()

    # Who won, decided before anything is reset
    top_users = session.query(Utente).order_by(desc(Utente.exp)).limit(3).all()
    podium = [(u.id_telegram, u.nome, u.exp) for u in top_users]
    rewards = [10000, 5000, 2000]
    for i, (uid, name, exp) in enumerate(podium):
        print(f"Top {i+1}: {name} (Exp: {exp})")

    print("Azzeramento di tutti gli utenti...")
    users = reset_everyone(session, stan_lee_id, keep_equipped=[p[0] for p in podium])

    # Dungeon ids are reused between seasons: nothing of the old progress may survive (done above), and the ladder
    # of the new season starts closed for everyone.
    print("Premi del podio (gli achievement della scorsa stagione, i titoli, i Wumpa, gli oggetti, e restano loro quelli equipaggiati)...")
    for i, (uid, name, exp) in enumerate(podium):
        user = session.query(Utente).filter_by(id_telegram=uid).first()
        if closing_season:
            SeasonManager().award_podium(session, closing_season, i + 1, uid, label="Saga Dragon Ball")
        user.points = rewards[i]
        for equipment_id in prizes.values():
            session.add(UserEquipment(user_id=uid, equipment_id=equipment_id))

    print("Disattivazione stagioni precedenti e attivazione Stagione Marvel...")
    for s in session.query(Season).filter_by(is_active=True).all():
        s.is_active = False

    marvel_season = session.query(Season).filter_by(theme="Marvel").first()
    now = datetime.datetime.now()
    if not marvel_season:
        marvel_season = Season(
            name="Stagione 5: Marvel",
            start_date=now,
            end_date=now + datetime.timedelta(days=90),
            is_active=True,
            theme="Marvel",
            description="La nuova epica stagione Marvel!",
            exp_multiplier=1.0
        )
        session.add(marvel_season)
        session.flush()
    else:
        marvel_season.is_active = True
        marvel_season.start_date = now
        marvel_season.end_date = now + datetime.timedelta(days=90)

    marvel_season.final_reward_name = marvel_season.final_reward_name or "Iron Man (Mark 85)"
    seeded = SeasonManager().seed_rewards_from_csv(session, marvel_season.id, os.path.join(data_dir, 'season_marvel_rewards.csv'))
    print(f"Season Pass: {seeded} premi inseriti")

    if apply:
        SystemState.set_val(session, 'season_wipe_done', now.isoformat())
        session.commit()
        print(f"Season Wipe completato su {len(users)} utenti e premi distribuiti!")
    else:
        session.rollback()
        print(f"PROVA A SECCO su {len(users)} utenti: nulla è stato salvato. Usa --apply per eseguirlo davvero.")
    return True


if __name__ == '__main__':
    apply = '--apply' in sys.argv
    prepare_equip()
    try:
        run_wipe(apply)
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"Errore durante l'esecuzione del Wipe: {e}")
        sys.exit(1)
