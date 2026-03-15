#!/usr/bin/env python3
import os
import math
import random
import hashlib
from PIL import Image, ImageDraw, ImageFilter, ImageFont

OUT_DIR = os.path.join('assets', 'characters', 'marvel')
W, H = 1024, 1024

MARVEL_NAMES = [
    'Spider-Man','Iron Man','Thor','Hulk','Captain America','Black Widow','Hawkeye','Doctor Strange','Scarlet Witch','Vision',
    'Black Panther','Ant-Man','Wasp','Falcon','Winter Soldier','War Machine','Captain Marvel','Star-Lord','Gamora','Drax',
    'Rocket Raccoon','Groot','Mantis','Nebula','Loki','Thanos','Nick Fury','Moon Knight','Daredevil','Elektra',
    'Punisher','Blade','Ghost Rider','Wolverine','Deadpool','Storm','Cyclops','Jean Grey','Rogue','Iceman',
    'Nightcrawler','Colossus','Beast','Professor X','Magneto','Mystique','Emma Frost','Kitty Pryde','Jubilee','Cable',
    'Psylocke','Domino','X-23','Shang-Chi','Ms. Marvel','She-Hulk','Kate Bishop','Echo','Yelena Belova','America Chavez',
    'Shuri','Okoye','M’Baku','Namor','Silver Surfer','Fantastic Four','Mr. Fantastic','Invisible Woman','Human Torch','Thing',
    'Ultron','Red Skull','Baron Zemo','Kingpin','Green Goblin','Venom','Carnage','Morbius','Vulture','Mysterio',
    'Sandman','Electro','Kraven','Doc Ock','Lizard','Rhino','Taskmaster','Kang','Hela','Sentry',
    'Nova','Adam Warlock','Quicksilver','Agatha Harkness','Wiccan','Speed','Monica Rambeau','Photon','Blue Marvel','Ares'
]


def slugify(name: str) -> str:
    s = name.lower().replace('’', '').replace("'", '')
    out = []
    for ch in s:
        if ch.isalnum():
            out.append(ch)
        else:
            out.append('_')
    slug = ''.join(out)
    while '__' in slug:
        slug = slug.replace('__', '_')
    return slug.strip('_')


def pick_palette(seed: int):
    rnd = random.Random(seed)
    # cinematic high-contrast palettes
    palettes = [
        ((8, 16, 34), (168, 26, 60), (250, 213, 91)),
        ((10, 14, 20), (22, 120, 192), (113, 237, 255)),
        ((16, 8, 30), (110, 35, 188), (255, 102, 196)),
        ((22, 16, 10), (220, 85, 35), (255, 213, 122)),
        ((6, 24, 20), (20, 154, 113), (140, 255, 200)),
        ((20, 8, 8), (190, 44, 44), (255, 175, 90)),
    ]
    return palettes[rnd.randrange(len(palettes))]


def lerp(a, b, t):
    return int(a + (b - a) * t)


def make_bg(seed: int):
    c0, c1, c2 = pick_palette(seed)
    base = Image.new('RGB', (W, H), c0)
    pix = base.load()

    # vertical + diagonal gradient
    for y in range(H):
        ty = y / (H - 1)
        for x in range(W):
            tx = x / (W - 1)
            t = min(1.0, max(0.0, 0.72 * ty + 0.28 * (1.0 - tx)))
            r = lerp(c0[0], c1[0], t)
            g = lerp(c0[1], c1[1], t)
            b = lerp(c0[2], c1[2], t)
            pix[x, y] = (r, g, b)

    rnd = random.Random(seed)

    # glow orbs
    glow = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    for _ in range(6):
        cx = rnd.randint(-200, W + 200)
        cy = rnd.randint(-100, H + 200)
        rr = rnd.randint(180, 420)
        alpha = rnd.randint(30, 90)
        gd.ellipse((cx - rr, cy - rr, cx + rr, cy + rr), fill=(c2[0], c2[1], c2[2], alpha))
    glow = glow.filter(ImageFilter.GaussianBlur(48))
    base = Image.alpha_composite(base.convert('RGBA'), glow)

    # dynamic streaks
    streaks = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    sd = ImageDraw.Draw(streaks)
    for _ in range(12):
        x0 = rnd.randint(-200, W)
        y0 = rnd.randint(0, H)
        x1 = x0 + rnd.randint(350, 900)
        y1 = y0 - rnd.randint(80, 260)
        width = rnd.randint(2, 6)
        sd.line((x0, y0, x1, y1), fill=(255, 255, 255, rnd.randint(40, 100)), width=width)
    streaks = streaks.filter(ImageFilter.GaussianBlur(2))
    base = Image.alpha_composite(base, streaks)

    # vignette
    vignette = Image.new('L', (W, H), 0)
    vd = ImageDraw.Draw(vignette)
    vd.ellipse((-W * 0.15, -H * 0.1, W * 1.15, H * 1.12), fill=255)
    vignette = Image.eval(vignette, lambda p: int(p * 0.78)).filter(ImageFilter.GaussianBlur(120))
    dark = Image.new('RGBA', (W, H), (0, 0, 0, 140))
    base = Image.composite(base, dark, Image.eval(vignette, lambda p: 255 - p))

    return base.convert('RGB')


def load_font(size):
    candidates = [
        '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
        '/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf',
    ]
    for path in candidates:
        if os.path.exists(path):
            return ImageFont.truetype(path, size=size)
    return ImageFont.load_default()


def fit_text(draw, text, max_w, start_size=86, min_size=34):
    size = start_size
    while size >= min_size:
        font = load_font(size)
        bbox = draw.textbbox((0, 0), text, font=font)
        w = bbox[2] - bbox[0]
        if w <= max_w:
            return font
        size -= 2
    return load_font(min_size)


def render_card(name: str):
    seed = int(hashlib.sha256(name.encode('utf-8')).hexdigest()[:8], 16)
    img = make_bg(seed)
    d = ImageDraw.Draw(img)

    # border frame
    d.rounded_rectangle((20, 20, W - 20, H - 20), radius=28, outline=(255, 255, 255), width=2)

    # center silhouette-like shape (generic heroic shard)
    rnd = random.Random(seed)
    shape = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    sd = ImageDraw.Draw(shape)
    cx, cy = W // 2, H // 2 + 40
    pts = []
    for i in range(12):
        ang = (math.pi * 2) * i / 12.0 + rnd.uniform(-0.12, 0.12)
        rr = rnd.randint(120, 290)
        pts.append((cx + int(rr * math.cos(ang)), cy + int(rr * math.sin(ang))))
    sd.polygon(pts, fill=(255, 255, 255, 28), outline=(255, 255, 255, 90))
    shape = shape.filter(ImageFilter.GaussianBlur(1.5))
    img = Image.alpha_composite(img.convert('RGBA'), shape).convert('RGB')
    d = ImageDraw.Draw(img)

    # title + subtitle
    title_font = fit_text(d, name, max_w=W - 120)
    subtitle_font = load_font(30)

    title_y = H - 220
    # shadow
    d.text((62, title_y + 3), name, font=title_font, fill=(0, 0, 0))
    d.text((60, title_y), name, font=title_font, fill=(245, 245, 245))

    subtitle = 'aROMa • Season 2'
    d.text((60, title_y + 88), subtitle, font=subtitle_font, fill=(230, 230, 230))

    # top tag
    tag_font = load_font(26)
    d.rounded_rectangle((60, 62, 278, 108), radius=16, fill=(0, 0, 0, 120), outline=(255, 255, 255), width=1)
    d.text((76, 72), 'MARVEL HERO', font=tag_font, fill=(255, 255, 255))

    return img


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    generated = 0
    for name in MARVEL_NAMES:
        slug = slugify(name)
        out = os.path.join(OUT_DIR, f'{slug}.png')
        img = render_card(name)
        img.save(out, 'PNG', optimize=True)
        generated += 1
    print(f'Generated {generated} images in {OUT_DIR}')


if __name__ == '__main__':
    main()
