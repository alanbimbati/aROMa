"""Cover pictures taken from the posts of the album channels themselves (the best source: it is the picture the post has).

Run it where the bot's database and your Telegram user session are (the Raspberry), once, then again for new games:

    TG_API_ID=... TG_API_HASH=... TG_SESSION=user_session python scripts/fetch_album_covers.py [--limit N]

A bot cannot read a channel's history, only a user account can, so this uses the same kind of session the old scanner
did. For every row of the `games` table it opens the post `message_link` points to, downloads its photo and saves it
as cache/game_covers/<game id>.webp (320px). It overwrites the libretro picture of scripts/fetch_game_covers.py and
skips games that already have a picture from here (data/games_covers_album.txt). The session never leaves the machine.
"""
import asyncio
import io
import os
import re
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from PIL import Image  # noqa: E402
from sqlalchemy import text  # noqa: E402
from telethon import TelegramClient  # noqa: E402

from database import Database  # noqa: E402

OUT_DIR = os.path.join(BASE_DIR, 'cache', 'game_covers')
DONE = os.path.join(BASE_DIR, 'data', 'games_covers_album.txt')


def parse_link(link):
    """('c', channel id, message id) for t.me/c/<id>/<msg>, or (username, None, message id) for t.me/<name>/<msg>."""
    m = re.search(r't\.me/c/(\d+)/(?:\d+/)?(\d+)', link or '')
    if m:
        return int('-100' + m.group(1)), int(m.group(2))
    m = re.search(r't\.me/([A-Za-z0-9_]+)/(\d+)', link or '')
    return (m.group(1), int(m.group(2))) if m else (None, None)


async def photo_message(client, chat, msg_id):
    """The post itself, or, when the photo is posted just next to it (an album group, or the line before), that one."""
    msg = await client.get_messages(chat, ids=msg_id)
    if msg and msg.photo:
        return msg
    near = await client.get_messages(chat, ids=[msg_id - 1, msg_id + 1, msg_id - 2])
    group = getattr(msg, 'grouped_id', None)
    for m in near:
        if m and m.photo and (group is None or m.grouped_id == group or m.id == msg_id - 1):
            return m
    return None


async def main():
    limit = int(sys.argv[sys.argv.index('--limit') + 1]) if '--limit' in sys.argv else None
    os.makedirs(OUT_DIR, exist_ok=True)
    done = set(open(DONE).read().split()) if os.path.exists(DONE) else set()
    with Database().engine.connect() as c:
        rows = c.execute(text('select id, message_link from games order by id')).all()
    client = TelegramClient(os.getenv('TG_SESSION', 'user_session'), int(os.environ['TG_API_ID']), os.environ['TG_API_HASH'])
    saved = 0
    async with client:
        for game_id, link in rows:
            if str(game_id) in done:
                continue
            chat, msg_id = parse_link(link)
            if not chat:
                continue
            try:
                msg = await photo_message(client, chat, msg_id)
                if not msg:
                    print(f'  game {game_id}: no photo at {link}')
                    continue
                data = await client.download_media(msg.photo, file=bytes)
                im = Image.open(io.BytesIO(data)).convert('RGB')
                im.thumbnail((320, 480))
                im.save(os.path.join(OUT_DIR, f'{game_id}.webp'), 'WEBP', quality=84)
                done.add(str(game_id))
                saved += 1
            except Exception as e:
                print(f'  game {game_id}: {e}')
            if limit and saved >= limit:
                break
            await asyncio.sleep(0.3)  # stay far from Telegram's flood limits
    open(DONE, 'w').write('\n'.join(sorted(done, key=int)))
    print(f'{saved} pictures saved from the channels')


if __name__ == '__main__':
    asyncio.run(main())
