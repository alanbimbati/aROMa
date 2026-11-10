"""Ephemeral replies to a button press: a message only the player who pressed it sees (Bot API 10.4)."""
import json
import os
from datetime import datetime

from telebot import apihelper


def ephemeral_enabled():
    """EPHEMERAL_COMBAT=0 in .env puts back the popups and the public messages."""
    return os.getenv('EPHEMERAL_COMBAT', '1').strip() == '1'


def send_ephemeral_reply(bot, call, text, parse_mode='Markdown'):
    """False means the player saw nothing and the caller must fall back to what it did before."""
    if not ephemeral_enabled():
        return False
    # No chat_id on purpose: with it, a server that ignores the ephemeral part would post in the group.
    params = {'text': text, 'ephemeral_message_parameters': json.dumps({'callback_query_id': call.id})}
    if parse_mode:
        params['parse_mode'] = parse_mode
    try:
        # pyTelegramBotAPI has no wrapper for this yet, and a raw call does not depend on its version.
        apihelper._make_request(bot.token, 'sendMessage', params=params, method='post')
        return True
    except Exception as e:
        if parse_mode and "can't parse entities" in str(e):
            return send_ephemeral_reply(bot, call, text, parse_mode=None)
        print(f"[EPHEMERAL] reply to callback {call.id} failed: {e}")
        return False


def _bar(value, maximum, filled, slots=8):
    if not maximum or maximum <= 0:
        return ""
    full = max(0, min(slots, round(slots * value / maximum)))
    return filled * full + "⬜" * (slots - full)


def player_combat_report(user, cooldown_multiplier=1, now=None):
    """The fighter's own state after an action: what the group card cannot show for each player."""
    now = now or datetime.now()
    max_hp = user.max_health or 0
    hp = user.current_hp if user.current_hp is not None else user.health
    hp = max(0, hp or 0)
    mana = max(0, user.mana or 0)
    max_mana = user.max_mana or 0

    lines = ["🎯 *Solo per te*"]
    lines.append(f"❤️ {hp}/{max_hp} {_bar(hp, max_hp, '🟥')}".rstrip())
    lines.append(f"💙 {mana}/{max_mana} {_bar(mana, max_mana, '🟦')}".rstrip())
    shield = getattr(user, 'shield_hp', 0) or 0
    if shield > 0:
        lines.append(f"🛡️ Scudo: {shield}")
    if max_hp and 0 < hp <= max_hp * 0.25:
        lines.append("⚠️ Sei in pericolo: curati o difenditi!")
    elif hp == 0:
        lines.append("💀 Sei a terra.")

    cooldown = 60 / (1 + (getattr(user, 'speed', 0) or 0) * 0.05) * cooldown_multiplier
    last_attack = getattr(user, 'last_attack_time', None)
    remaining = cooldown - (now - last_attack).total_seconds() if isinstance(last_attack, datetime) else 0
    if remaining > 0:
        ready_at = datetime.fromtimestamp(now.timestamp() + remaining).strftime('%H:%M:%S')
        lines.append(f"⏳ Prossima azione tra {int(remaining) + 1}s ({ready_at})")
    else:
        lines.append("✅ Puoi agire subito")
    return "\n".join(lines)
