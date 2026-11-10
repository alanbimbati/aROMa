"""The Arena page: the mobs a player can fight, their own state, and the fight buttons (played by the bot)."""
import os
from datetime import datetime

from database import Database
from models.pve import Mob
from models.user import Utente
from services import web_actions

# The callback data of the chat buttons: the bot plays a web action through the very same handler.
ACTIONS = {
    'attack': 'attack_enemy|mob|{id}', 'special': 'special_attack_enemy|mob|{id}', 'defend': 'defend_mob|mob|{id}',
    'aoe': 'aoe_attack_enemy|mob|{id}', 'special_aoe': 'special_aoe_attack_enemy|mob|{id}',
    'flee': 'flee_enemy|mob|{id}', 'scan': 'scan_mob|{id}',
}


def _group_id():
    from settings import GRUPPO_AROMA
    return int(GRUPPO_AROMA)


def _has_scouter(user_id):
    from services.equipment_service import EquipmentService
    try:
        return any(item.effect_type in ('scan', 'scouter_scan')
                   for _, item in EquipmentService().get_equipped_items(user_id))
    except Exception as e:
        print(f"[WEB] scouter check failed for {user_id}: {e}")
        return False


def _cooldown(speed, last, now):
    total = 60 / (1 + (speed or 0) * 0.05)
    left = total - (now - last).total_seconds() if isinstance(last, datetime) else 0
    return round(total, 1), round(max(0.0, left), 1)


def _player(user, scouter, now):
    from services.character_loader import get_character_loader
    character = get_character_loader().get_character_by_id(user.livello_selezionato) or {}
    hp = user.current_hp if user.current_hp is not None else user.health
    total, left = _cooldown(user.speed, user.last_attack_time, now)
    return {
        'hp': max(0, hp or 0), 'max_hp': user.max_health or 0, 'mana': max(0, user.mana or 0),
        'max_mana': user.max_mana or 0, 'shield': user.shield_hp or 0, 'resting': bool(user.resting_since),
        # After an AoE the real wait is twice this: the bot's answer says so when a button is pressed too early.
        'cooldown': total, 'ready_in': left, 'scouter': scouter,
        'special': {'name': character.get('special_attack_name') or 'Attacco speciale',
                    'mana': character.get('special_attack_mana_cost') or 0},
    }


def _mob(mob, private, scouter, now):
    name = mob.name.lower().replace(' ', '_')
    out = {
        'id': mob.id, 'name': mob.name, 'level': mob.mob_level or 1, 'boss': bool(mob.is_boss),
        'tier': mob.difficulty_tier or 1, 'speed': mob.speed or 0, 'private': private, 'dungeon': bool(mob.dungeon_id),
        # Like the card in the chat: everyone sees the share of health left, the numbers need a Scouter.
        'hp_pct': max(0, min(100, round(100 * mob.health / mob.max_health))) if mob.max_health else 0,
        'img': name, 'defending': bool(mob.is_defending),
    }
    if scouter:
        _, left = _cooldown(mob.speed or 30, mob.last_attack_time, now)
        out.update(hp=mob.health, max_hp=mob.max_health, attack=mob.attack_damage, resistance=mob.resistance or 0,
                   attacks_in=left)
    return out


def state(user_id):
    session = Database().get_session()
    try:
        user = session.query(Utente).filter_by(id_telegram=user_id).first()
        if not user:
            return {'player': None, 'mobs': [], 'paused': False}
        now = datetime.now()
        scouter = _has_scouter(user_id)
        mobs = session.query(Mob).filter(Mob.chat_id.in_([_group_id(), user_id]), Mob.is_dead == False).order_by(Mob.id).all()  # noqa: E712
        cards = [_mob(m, m.chat_id == user_id, scouter, now) for m in mobs]
        cards.sort(key=lambda m: (not m['private'], not m['boss'], m['id']))
        for card in cards:  # the chat shows the area attacks only with two enemies or more in the same place
            card['aoe'] = sum(1 for other in cards if other['private'] == card['private']) >= 2
        return {'player': _player(user, scouter, now), 'mobs': cards,
                'paused': os.getenv('COMBAT_PAUSED', '0').strip() == '1'}
    finally:
        session.close()


def act(user_id, mob_id, action):
    if action not in ACTIONS:
        return {'ok': False, 'message': "Azione sconosciuta.", **state(user_id)}
    session = Database().get_session()
    try:
        mob = session.query(Mob).filter_by(id=mob_id).first()
        chat_id = mob.chat_id if mob else None
        gone = not mob or mob.is_dead
    finally:
        session.close()
    if gone:
        return {'ok': False, 'message': "Questo nemico non c'è più.", **state(user_id)}
    if chat_id not in (_group_id(), user_id):
        return {'ok': False, 'message': "Questo nemico non è alla tua portata.", **state(user_id)}

    action_id = web_actions.enqueue(user_id, chat_id, ACTIONS[action].format(id=mob_id))
    result = web_actions.wait_result(action_id)
    if result is None:
        return {'ok': False, 'message': "Il bot non risponde in questo momento: riprova tra poco.", **state(user_id)}
    ok, message = result
    return {'ok': ok, 'message': message, **state(user_id)}
