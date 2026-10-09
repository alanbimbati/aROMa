"""The card of a catalogue game as the bot shows it (information only: no file is ever sent from here)."""
import io
import os
import re
from html import escape

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
COVERS = os.path.join(BASE_DIR, 'cache', 'game_covers')
CAPTION_LIMIT = 1024  # Telegram's limit for a photo caption


def parse_start_payload(text):
    """The game id in '/start game_123', or None."""
    m = re.match(r'/start(?:@\w+)?\s+game_(\d{1,7})$', (text or '').strip())
    return int(m.group(1)) if m else None


def card_text(game):
    lines = [f"🎮 <b>{escape(game['title'])}</b>"]
    facts = [', '.join(game['platforms']), str(game['year']) if game['year'] else '']
    lines.append(' · '.join(f for f in facts if f))
    if game['genres']:
        lines.append(f"🏷 {escape(' · '.join(game['genres']))}")
    langs = list(game['languages']) or (['Multilingue'] if game['multilanguage'] else [])
    if langs or game['regions']:
        lines.append('🌍 ' + escape(' · '.join([*langs, *game['regions']])))
    credits = [c for c in (game['developer'], game['publisher']) if c]
    if credits:
        lines.append('🏢 ' + escape(' / '.join(dict.fromkeys(credits))))
    head = '\n'.join(lines)
    room = CAPTION_LIMIT - len(head) - 3
    desc = game['description']
    if desc and room > 40:
        desc = escape(desc[:room - 1] + '…' if len(desc) > room else desc)  # escaping can only lengthen it, so cut first
        head += '\n\n' + desc
    return head[:CAPTION_LIMIT]


def cover_jpeg(game_id):
    """The cover as JPEG bytes (Telegram treats a .webp upload as a sticker), or None if the game has none."""
    path = os.path.join(COVERS, f'{int(game_id)}.webp')
    if not os.path.isfile(path):
        return None
    from PIL import Image
    out = io.BytesIO()
    Image.open(path).convert('RGB').save(out, 'JPEG', quality=88)
    out.seek(0)
    return out
