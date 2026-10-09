"""Illustrations for every Marvel character, mob and boss, downloaded from the Pollinations image generator.

It needs a free API key (a minute to get, GitHub login): https://enter.pollinations.ai/keys
Put it in .env as POLLINATIONS_API_KEY. Without one the service only serves a handful of pictures.

Replaces the programmatic name cards. Each picture is cropped to a square (the generator's corner mark is cut off),
saved as assets/characters/marvel/<slug>.jpg and recorded in data/marvel_images.csv (prompt and seed), so a missing
file can be fetched again identically. Runs resumably: pictures already there are skipped.

    python scripts/fetch_marvel_images.py                 # everything still missing
    python scripts/fetch_marvel_images.py --only "Falcon" # one
    python scripts/fetch_marvel_images.py --overwrite     # redo all
"""
import argparse
import csv
import io
import os
import sys
import time
import urllib.parse
import zlib
from concurrent.futures import ThreadPoolExecutor

import requests
from PIL import Image

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)
from scripts.generate_marvel_replicate import CHARACTER_STYLE_HINTS, STYLE_SUFFIX, TOKEN_STYLE_HINTS  # noqa: E402
from scripts.install_marvel_images import marvel_names, slugify  # noqa: E402

OUT_DIR = os.path.join(BASE_DIR, 'assets', 'characters', 'marvel')
MANIFEST = os.path.join(BASE_DIR, 'data', 'marvel_images.csv')
API_KEY = os.getenv("POLLINATIONS_API_KEY", "")
ENDPOINT = "https://gen.pollinations.ai/image/{prompt}" if API_KEY else "https://image.pollinations.ai/prompt/{prompt}"


class NoAccess(Exception):
    """The service refused us: retrying would only waste time."""
SIZE = 768
# Real illustrations made earlier with another service: kept as they are
KEEP_PNG = {'peter_parker', 'spider_man', 'stan_lee', 'tony_stark'}

HINTS = {
    'kate bishop': "young archer woman, purple and black costume, dark sunglasses, bow and quiver",
    'falcon': "Sam Wilson, red and silver mechanical wings, tactical suit, goggles",
    'echo': "deaf martial artist woman, black bodysuit with a white handprint on her face",
    'wasp': "slim heroine in black and yellow suit with insect wings and antennae helmet",
    'ant-man': "red and silver ant suit with round helmet",
    'vulture': "elderly villain in a green mechanical bird wing flight harness, bald head",
    'yelena belova': "female assassin in black and white tactical vest with fur-trimmed collar",
    'daredevil': "red vigilante suit with horned mask, billy club, rooftop at night",
    'elektra': "female assassin in red outfit with twin sai blades, hooded",
    'punisher': "black tactical outfit with white skull chest emblem, assault rifle",
    'winter soldier': "metal left arm, dark tactical gear, long hair, face mask",
    'blade': "black leather coat, sunglasses, silver sword, vampire hunter",
    'kitty pryde': "young mutant woman in yellow and blue X-Men uniform phasing through a wall",
    'jubilee': "yellow coat and sunglasses, colorful plasma sparks in her hands",
    'nightcrawler': "blue furry mutant with pointed ears, red and black costume, demon tail, teleport smoke",
    'electro': "yellow and blue lightning villain, electrified bodysuit with star mask",
    'shang-chi': "martial artist in red and gold outfit, ten glowing rings on his arms",
    'okoye': "bald warrior woman in red Dora Milaje armor holding a vibranium spear",
    "m'baku": "huge bearded warrior in white gorilla fur armor, Jabari tribe",
    'moon knight': "white hooded costume with crescent moon cape, silver mask",
    'x-23': "young mutant in black leather X-Force suit, adamantium claws extended",
    'cyclops': "red ruby quartz visor, blue and yellow X-Men uniform, optic blast",
    'iceman': "ice-covered translucent body, frost aura, blue X-Men colors",
    'rhino': "massive man in grey rhinoceros armored suit with a horn",
    'kraven': "muscular hunter in a lion-mane vest, spear, jungle trophies",
    'domino': "white skin with black eye patches, black tactical gear, dual pistols",
    'taskmaster': "white skull mask and hood, blue cape, round shield and sword",
    'gamora': "green-skinned warrior woman, black leather outfit, long sword, dark hair",
    'storm': "white flowing hair, black costume with cape, lightning in the sky",
    'nebula': "blue cybernetic woman, bald with metal implants, black armor",
    'drax': "huge grey-skinned warrior with red tattoos, twin daggers, bare chest",
    'rocket raccoon': "armed raccoon in orange jumpsuit holding a huge blaster",
    'mysterio': "fishbowl glass dome helmet, green cape, purple smoke illusions",
    'sandman': "figure made of swirling sand, striped shirt, giant sand fist",
    'beast': "blue furry mutant genius, lab coat, glasses, X-Men",
    'psylocke': "purple ninja costume with psychic butterfly aura, katana",
    'monica rambeau': "woman with glowing white energy aura, blue and white suit",
    'colossus': "huge man with polished steel skin, red and yellow X-Men outfit",
    'mantis': "woman with antennae, green insect-like empath suit, calm aura",
    'nick fury': "black eyepatch, black leather trench coat, bald head, serious look",
    'vision': "synthezoid red face, yellow forehead gem, green and yellow suit with cape",
    'war machine': "grey and black heavy armor with shoulder cannons",
    'lizard': "giant green lizard man, torn lab coat, reptile scales and claws",
    'rogue': "brunette with a white streak, green and yellow suit, bomber jacket",
    'she-hulk': "tall muscular green-skinned woman in a white and purple suit, confident",
    'quicksilver': "silver hair, silver and blue speedster suit, speed lines",
    'human torch': "man engulfed in orange flames, blue fantastic four suit",
    'invisible woman': "woman in blue suit with a translucent force-field bubble, blonde hair",
    'shuri': "young Wakandan princess, vibranium gauntlets, purple tech suit",
    'ms. marvel': "young heroine in blue and red suit with lightning bolt, giant glowing fist",
    'green goblin': "green armored goblin villain with pointed ears, purple tunic, pumpkin bomb, glider",
    'mr. fantastic': "stretching man in blue fantastic four suit, grey temples",
    'thing': "orange rocky-skinned giant in blue trunks, fantastic four",
    'mystique': "blue-skinned shapeshifter with red hair, white dress, yellow eyes",
    'morbius': "pale vampire scientist, black coat, dark veins, fangs",
    'wiccan': "young mage with black hair, red and gold magical robes, glowing hex",
    'speed': "teenage speedster in a green and yellow suit with a speed trail",
    'nova': "gold helmet and blue suit, cosmic energy Nova Corps hero",
    'ghost rider': "flaming skull rider, black leather jacket, chains, motorcycle",
    'kingpin': "huge bald crime lord in a white suit with cane, menacing",
    'cable': "cybernetic eye and arm, tactical armor with a large rifle, time traveler",
    'doc ock': "four mechanical tentacles, green and yellow suit, round glasses",
    'baron zemo': "purple mask with dark hood, ruthless strategist, tactical gear",
    'agatha harkness': "witch in purple robes with glowing magic hands, dark hair",
    'america chavez': "star on her jacket, jean jacket, star-shaped portal",
    'carnage': "chaotic red symbiote with long tentacles and claws",
    'blue marvel': "blue and black costume with glowing antimatter energy",
    'emma frost': "white outfit, platinum blonde hair, diamond skin, regal",
    'namor': "winged ankles, green swimming trunks, atlantean king with trident, water waves",
    'professor x': "bald old man in a wheelchair, glowing psychic Cerebro aura",
    'photon': "pure white-yellow light energy woman, glowing radiant aura",
    'magneto': "red and purple armor with cape and helmet, metal objects floating",
    'kang': "blue and green armor with high collar and helmet, time portal behind",
    'adam warlock': "golden skin with red cape, soul gem on forehead, cosmic aura",
    'sentry': "gold and white radiant hero with golden lightning, cape",
    'jean grey': "red and gold phoenix fire aura, long red hair, green costume",
    'iron man': "advanced red and gold nanotech armor, glowing arc reactor, flying",
    'fantastic four': "four heroes in blue uniforms: a stretching man, an invisible woman, a flaming man and a rocky giant",
    'scagnozzo': "street thug with a baseball bat, hoodie, alley",
    'scagnozzo armato': "gangster with a pistol, leather jacket, night street",
    'ninja della mano': "black ninja assassin with red markings, katana",
    'cacciatore': "mercenary hunter in camouflage with a rifle and animal trophies",
    'simbionte': "black liquid alien symbiote creature with white eyes and teeth",
    'sentinella': "giant purple and blue robot with large hands, mutant hunter",
    'guardia temporale': "futuristic soldier in sleek blue armor with an energy rifle",
    'steve rogers': "WWII era soldier uniform, earnest expression, shield at back",
}


def prompt_for(name):
    key = name.casefold()
    hint = HINTS.get(key) or CHARACTER_STYLE_HINTS.get(key)
    if not hint:
        hint = next((h for token, h in TOKEN_STYLE_HINTS.items() if token in key), None)
    return f"{name}, {hint or 'iconic superhero costume, recognizable design'}, Marvel Comics, {STYLE_SUFFIX}"


def fetch(name, retries=None):
    # Anonymous use is throttled (HTTP 402 most of the time, one picture every minute or so): keep asking politely
    retries = retries or (5 if API_KEY else 120)
    slug = slugify(name)
    seed = zlib.crc32(slug.encode()) % 100000
    prompt = prompt_for(name)
    url = ENDPOINT.format(prompt=urllib.parse.quote(prompt)) + f"?width=1024&height=1024&model=flux&nologo=true&seed={seed}"
    for attempt in range(retries):
        try:
            headers = {'User-Agent': 'aROMa-fan-game/1.0'}
            if API_KEY:
                headers['Authorization'] = f'Bearer {API_KEY}'
            r = requests.get(url + (f"&key={API_KEY}" if API_KEY else ""), timeout=120, headers=headers)
            if r.status_code in (401, 402, 403):
                if API_KEY:
                    raise NoAccess(f"HTTP {r.status_code}")
                time.sleep(10)
                continue
            if r.status_code == 200 and r.headers.get('content-type', '').startswith('image'):
                img = Image.open(io.BytesIO(r.content))
                img.load()
                w, h = img.size
                img = img.convert('RGB').crop((0, 0, w, int(h * 0.93)))  # the generator signs the bottom edge
                side = min(img.size)
                left = (img.width - side) // 2
                img = img.crop((left, 0, left + side, side)).resize((SIZE, SIZE), Image.LANCZOS)
                return slug, img, prompt, seed
            wait = 8 * (attempt + 1)
        except NoAccess:
            raise
        except Exception:  # network hiccup, truncated body...
            wait = 5 * (attempt + 1)
        time.sleep(wait)
    return slug, None, prompt, seed


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--only')
    ap.add_argument('--overwrite', action='store_true')
    ap.add_argument('--workers', type=int, default=None)
    args = ap.parse_args()
    os.makedirs(OUT_DIR, exist_ok=True)

    names = []
    seen = set()
    for _, name in marvel_names():
        if name.lower() not in seen:
            seen.add(name.lower())
            names.append(name)
    if args.only:
        names = [n for n in names if n.lower() == args.only.lower()]

    def todo(name):
        slug = slugify(name)
        if slug in KEEP_PNG and not args.overwrite:
            return False
        return args.overwrite or not os.path.exists(os.path.join(OUT_DIR, slug + '.jpg'))

    pending = [n for n in names if todo(n)]
    print(f"{len(pending)} of {len(names)} pictures to fetch")
    manifest = {}
    if os.path.exists(MANIFEST):
        with open(MANIFEST, newline='', encoding='utf-8') as f:
            manifest = {r['slug']: r for r in csv.DictReader(f)}
    done = failed = 0
    if pending and not API_KEY:
        print("No POLLINATIONS_API_KEY set: anonymous use is throttled to about one picture a minute, so this will be slow. "
              "A free key (https://enter.pollinations.ai/keys, in .env) makes it a few minutes.")
    with ThreadPoolExecutor(max_workers=args.workers or (3 if API_KEY else 1)) as pool:
        try:
            results = pool.map(fetch, pending)
            for slug, img, prompt, seed in results:
                if img is None:
                    failed += 1
                    print(f"  FAILED {slug}")
                    continue
                img.save(os.path.join(OUT_DIR, slug + '.jpg'), 'JPEG', quality=88, optimize=True)
                old_png = os.path.join(OUT_DIR, slug + '.png')
                if slug not in KEEP_PNG and os.path.exists(old_png):
                    os.remove(old_png)  # the name card it replaces
                manifest[slug] = {'slug': slug, 'source': 'pollinations.ai (flux)', 'seed': seed, 'prompt': prompt}
                done += 1
                if done % 10 == 0:
                    print(f"  {done}/{len(pending)}")
                    _save_manifest(manifest)
        except NoAccess as e:
            print(f"Stopped: the image service refused the request ({e}). Set a valid POLLINATIONS_API_KEY and run again: "
                  f"what is already downloaded is kept.")
            pool.shutdown(wait=False, cancel_futures=True)
    for slug in KEEP_PNG:
        manifest.setdefault(slug, {'slug': slug, 'source': 'replicate (flux-schnell)', 'seed': '', 'prompt': ''})
    _save_manifest(manifest)
    print(f"Fetched {done}, failed {failed}")


def _save_manifest(manifest):
    with open(MANIFEST, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=['slug', 'source', 'seed', 'prompt'])
        w.writeheader()
        w.writerows(sorted(manifest.values(), key=lambda r: r['slug']))


if __name__ == '__main__':
    main()
