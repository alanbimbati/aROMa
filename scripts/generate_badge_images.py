"""Render the Nostr badge images: one PNG per achievement tier, plus one per podium place.

Files are named <achievement_key>-<tier>.png (podiums: season-podium-<n>.png), which is what
NOSTR_BADGE_IMAGE_BASE has to serve.
"""
import csv
import json
import os
import re
import sys

from PIL import Image, ImageDraw, ImageFont

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(BASE_DIR, 'assets', 'badges')
SIZE = 512
SCALE = 2  # drawn at 2x and scaled down, for smooth edges

TIER_COLORS = {
    'bronze': (205, 127, 50), 'silver': (192, 197, 206), 'gold': (255, 200, 40),
    'platinum': (120, 220, 215), 'diamond': (130, 190, 255), 'legendary': (190, 110, 255),
}
TIER_ORDER = list(TIER_COLORS)
PODIUM_COLORS = {1: TIER_COLORS['gold'], 2: TIER_COLORS['silver'], 3: TIER_COLORS['bronze']}
FONT = '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
EMOJI_FONT = '/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf'  # bitmap font: only renders at 109 px
BG = (24, 26, 38)


def icon_of(name):
    """The achievement's own emoji (the one its name starts with), if any."""
    m = re.match(r"^\s*([^\w\s'.,!&-]+)", name)
    return m.group(1).replace('\ufe0f', '') if m else None


def draw_icon(img, icon, center, size):
    glyph = Image.new('RGBA', (136, 128), (0, 0, 0, 0))
    ImageDraw.Draw(glyph).text((0, 0), icon, font=ImageFont.truetype(EMOJI_FONT, 109), embedded_color=True)
    glyph = glyph.crop(glyph.getbbox()).resize((size, size), Image.LANCZOS)
    img.alpha_composite(glyph, (center[0] - size // 2, center[1] - size // 2))


def clean(name):
    # Drop emoji and decoration: the font cannot draw them.
    return re.sub(r'[^\w\s\'.,!&-]', '', name).strip()


def wrap(draw, text, font, width):
    lines, line = [], ''
    for word in text.split():
        trial = f'{line} {word}'.strip()
        if draw.textlength(trial, font=font) <= width or not line:
            line = trial
        else:
            lines.append(line)
            line = word
    return (lines + [line])[:3]


def star(draw, cx, cy, r, fill):
    import math
    pts = []
    for i in range(10):
        a = -math.pi / 2 + i * math.pi / 5
        rad = r if i % 2 == 0 else r * 0.45
        pts.append((cx + rad * math.cos(a), cy + rad * math.sin(a)))
    draw.polygon(pts, fill=fill)


def render(title, color, stars, path, icon=None):
    s = SIZE * SCALE
    img = Image.new('RGBA', (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    c = s // 2
    d.ellipse([8, 8, s - 8, s - 8], fill=color)
    dark = tuple(int(v * 0.55) for v in color)
    d.ellipse([40, 40, s - 40, s - 40], fill=dark)
    d.ellipse([64, 64, s - 64, s - 64], fill=BG)

    if icon:
        draw_icon(img, icon, (c, c - 150), 250)
    gap = 88
    start = c - gap * (stars - 1) / 2
    for i in range(stars):
        star(d, start + i * gap, c + 40, 34, color)

    font = ImageFont.truetype(FONT, 60)
    lines = wrap(d, title, font, s - 300)
    while len(lines) > 2 or any(d.textlength(l, font=font) > s - 300 for l in lines):
        font = ImageFont.truetype(FONT, font.size - 4)
        lines = wrap(d, title, font, s - 300)
    y = c + 100 if icon else c + 20
    for line in lines:
        d.text((c, y), line, font=font, fill=(240, 240, 245), anchor='ma')
        y += font.size + 12

    img.resize((SIZE, SIZE), Image.LANCZOS).save(path)


def definition_files():
    """Every achievement file the game can load: the default ones plus those of each season pack."""
    with open(os.path.join(BASE_DIR, 'data', 'season_content_manifest.json'), encoding='utf-8') as f:
        manifest = json.load(f)
    paths = list(manifest['default']['achievements'])
    for pack in manifest.get('packs', {}).values():
        paths += pack.get('append', {}).get('achievements', [])
    paths.append('data/achievements.json')  # loaded separately by the tracker
    return [os.path.join(BASE_DIR, p) for p in dict.fromkeys(paths)]


def definitions():
    for path in definition_files():
        if not os.path.exists(path):
            continue
        if path.endswith('.json'):
            with open(path, encoding='utf-8') as f:
                for row in json.load(f):
                    tiers = row['tiers']
                    yield row['achievement_key'], row['name'], json.loads(tiers) if isinstance(tiers, str) else tiers
        else:
            with open(path, encoding='utf-8') as f:
                for row in csv.DictReader(f):
                    yield row['key'], row['name'], json.loads(row['tiers'])


if __name__ == '__main__':
    os.makedirs(OUT_DIR, exist_ok=True)
    count = 0
    for key, name, tiers in definitions():
        for tier in tiers:
            if tier not in TIER_COLORS:
                print(f'skip {key}: unknown tier {tier}', file=sys.stderr)
                continue
            render(clean(name) or key, TIER_COLORS[tier], TIER_ORDER.index(tier) + 1,
                   os.path.join(OUT_DIR, f'{key}-{tier}.png'), icon_of(name))
            count += 1
    for place, color in PODIUM_COLORS.items():
        render(f'{place}° Posto', color, 4 - place, os.path.join(OUT_DIR, f'season-podium-{place}.png'),
               ['🥇', '🥈', '🥉'][place - 1])
        count += 1
    print(f'{count} badge images in {OUT_DIR}')
