#!/usr/bin/env python3
"""
Genera le immagini dei personaggi Marvel usando Replicate FLUX Schnell.
Legge i personaggi da data/characters.csv, data/mobs.csv, data/bosses.csv (saga=Marvel).
Salva in assets/characters/marvel/<slug>.png

Usage (dalla root del progetto aROMa):
    python scripts/generate_marvel_replicate.py
    python scripts/generate_marvel_replicate.py --overwrite
    python scripts/generate_marvel_replicate.py --name "Iron Man"
"""

import argparse
import csv
import os
import sys
import time
from pathlib import Path

import requests

# ── Replicate config ──────────────────────────────────────────────────────────
REPLICATE_API_TOKEN = os.getenv("REPLICATE_API_TOKEN", "")
FLUX_MODEL = "black-forest-labs/flux-schnell"
POLL_INTERVAL = 2
POLL_TIMEOUT = 120
OUT_DIR = Path("assets/characters/marvel")

# ── Style hints ───────────────────────────────────────────────────────────────
CHARACTER_STYLE_HINTS = {
    "spider-man": "classic red and blue suit with white eye lenses, web pattern, no black suit",
    "iron spider": "red and gold nano-tech suit with spider symbol, sleek futuristic armor",
    "cosmic spider-man": "ethereal blue glow over classic suit, cosmic energy aura",
    "iron man mark 1": "grey bulky iron suit, crude armor plates, visible rivets",
    "iron man": "iconic red and gold armor, arc reactor chest light, sleek design",
    "iron man hulkbuster": "massive red and yellow armored suit, giant proportions",
    "iron man bleeding edge": "ultra-sleek red and gold armor with liquid metal finish",
    "captain america": "blue suit with white star and red stripes, iconic vibranium shield",
    "captain america (worth)": "blue suit holding Mjolnir, lightning crackling, worthy pose",
    "hulk": "green skin, massive muscular build, purple pants, rage expression",
    "world breaker hulk": "dark green skin, massive build, earthquake energy, gamma aura",
    "thor odinson": "casual asgardian prince look, blonde hair, Mjolnir at side",
    "thor": "full asgardian armor, red cape, short hair, Mjolnir, lightning aura",
    "king thor": "regal golden asgardian armor, crown, Mjolnir, imposing ruler",
    "rune king thor": "ancient runes glowing on armor, cosmic power, mystical look",
    "natasha romanoff": "black tactical stealth suit, calm determined expression",
    "black widow": "black tactical suit with red hourglass insignia, dual pistols",
    "stan lee": "legendary creator in classic suit, glasses, iconic smile",
    "peter parker": "teenager in casual clothes, spider sense alert expression",
    "tony stark": "genius billionaire in business suit, confident smirk, arc reactor glow",
    "steve rogers": "WWII era soldier uniform, earnest expression, shield at back",
    "bruce banner": "torn clothes, scientist look, slight green tinge under skin",
}

TOKEN_STYLE_HINTS = {
    "widow": "black tactical stealth suit with red hourglass insignia",
    "hawkeye": "purple tactical archer suit, quiver and bow visible",
    "strange": "blue mystic robes and red cloak of levitation, glowing magic sigils",
    "scarlet": "red chaos magic aura, crimson outfit, elegant mystic look",
    "vision": "synthezoid red face with yellow forehead gem, green and yellow suit",
    "panther": "sleek black panther armor with silver lines and cat mask",
    "thanos": "purple titan with gold infinity armor, imposing portrait",
    "loki": "green and gold asgardian outfit, horned crown, mischievous grin",
    "wolverine": "yellow and blue suit, black pointed mask fins, adamantium claws extended",
    "deadpool": "red and black tactical suit, white eye patches, katanas over shoulders",
    "punisher": "black tactical outfit with white skull chest emblem",
    "daredevil": "dark red vigilante suit with horned mask",
    "ghost rider": "flaming skull, black leather jacket, hellfire aura",
    "doom": "green cloak and steel full-face mask, regal armored villain",
    "goblin": "green armored glider villain, menacing grin, pumpkin bombs",
    "venom": "black symbiote body with white spider emblem, sharp teeth, tongue",
    "carnage": "red symbiote tendrils, chaotic monstrous silhouette, red and black",
    "ultron": "silver chrome robotic body, glowing red eyes, menacing mechanical design",
    "hydra": "dark tactical military uniform with green hydra emblem",
    "chitauri": "alien warrior armor, reptilian features, sci-fi weapon",
    "hela": "black horned crown, dark green and black outfit, death goddess aura",
    "odin": "golden asgardian armor, eyepatch, white beard, all-father presence",
    "ronan": "dark kree warrior armor, universal weapon staff, imposing figure",
    "star-lord": "red long coat, space helmet, dual element guns",
    "groot": "tree creature, bark skin, warm glowing core, gentle giant",
    "rocket": "raccoon with tactical gear, large cannon weapon, smug expression",
    "ego": "golden glowing celestial being, planetary scale cosmic entity",
    "corvus": "dark armor, glaive weapon, black order general look",
    "proxima": "dark armor, spear weapon, fierce warrior expression",
    "ebony": "thin elongated villain in dark robes, mind control power aura",
    "cull": "massive black armored warrior, overwhelming physical presence",
    "outrider": "alien creature, feral attack pose, dark chitinous armor",
}

STYLE_SUFFIX = (
    "single character centered portrait, cinematic lighting, dramatic rim light, "
    "comic book art style, highly detailed, sharp focus, dark background, "
    "professional character concept art"
)

NEGATIVE_PROMPT = (
    "blurry, low quality, text, watermark, logo, bad anatomy, deformed, "
    "duplicate character, extra limbs, extra head, cropped, lowres, "
    "monochrome, disfigured, distorted, multiple people"
)


def slugify(name: str) -> str:
    s = name.lower().replace("'", "").replace("'", "")
    out = []
    for ch in s:
        if ch.isalnum():
            out.append(ch)
        else:
            out.append("_")
    slug = "".join(out)
    while "__" in slug:
        slug = slug.replace("__", "_")
    return slug.strip("_")


def build_prompt(name: str) -> str:
    key = name.casefold()
    hint = CHARACTER_STYLE_HINTS.get(key)
    if not hint:
        for token, h in TOKEN_STYLE_HINTS.items():
            if token in key:
                hint = h
                break
    if not hint:
        hint = "iconic superhero costume, recognizable design, single hero"
    return f"{name}, {hint}, {STYLE_SUFFIX}"


def load_marvel_names() -> list[str]:
    names = set()
    base = Path("data")
    files = [
        ("characters.csv", "character_group", "Marvel", "nome"),
        ("mobs.csv", "saga", "Marvel", "nome"),
        ("bosses.csv", "saga", "Marvel", "nome"),
    ]
    for fname, group_col, group_val, name_col in files:
        path = base / fname
        if not path.exists():
            continue
        with open(path, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get(group_col, "").strip() == group_val:
                    n = row.get(name_col, "").strip()
                    if n:
                        names.add(n)
    return sorted(names)


def call_replicate(prompt: str) -> bytes:
    headers = {
        "Authorization": f"Token {REPLICATE_API_TOKEN}",
        "Content-Type": "application/json",
    }
    payload = {
        "version": "black-forest-labs/flux-schnell",
        "input": {
            "prompt": prompt,
            "num_outputs": 1,
            "output_format": "png",
            "width": 768,
            "height": 768,
        },
    }
    r = requests.post(
        "https://api.replicate.com/v1/predictions",
        json=payload,
        headers=headers,
        timeout=30,
    )
    r.raise_for_status()
    prediction = r.json()
    pred_id = prediction["id"]

    deadline = time.time() + POLL_TIMEOUT
    while time.time() < deadline:
        time.sleep(POLL_INTERVAL)
        status_r = requests.get(
            f"https://api.replicate.com/v1/predictions/{pred_id}",
            headers=headers,
            timeout=15,
        )
        status_r.raise_for_status()
        data = status_r.json()
        if data["status"] == "succeeded":
            img_url = data["output"][0]
            img_r = requests.get(img_url, timeout=30)
            img_r.raise_for_status()
            return img_r.content
        if data["status"] in ("failed", "canceled"):
            raise RuntimeError(f"Replicate prediction {pred_id} {data['status']}")

    raise TimeoutError(f"Replicate prediction {pred_id} timed out after {POLL_TIMEOUT}s")


def generate_all(names: list[str], overwrite: bool) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    total = len(names)
    generated = 0
    skipped = 0
    errors = 0

    for i, name in enumerate(names, 1):
        out_path = OUT_DIR / f"{slugify(name)}.png"
        if out_path.exists() and not overwrite:
            skipped += 1
            print(f"[{i}/{total}] skip  {name}")
            continue

        prompt = build_prompt(name)
        print(f"[{i}/{total}] {name}...", end=" ", flush=True)
        try:
            img_bytes = call_replicate(prompt)
            out_path.write_bytes(img_bytes)
            generated += 1
            print(f"OK ({len(img_bytes):,} bytes)")
        except Exception as e:
            errors += 1
            print(f"ERRORE: {e}")
        time.sleep(0.5)

    print(f"\nGenerate: {generated} | Skippate: {skipped} | Errori: {errors}")
    print(f"Costo approssimativo: ${generated * 0.003:.3f}")
    print(f"Immagini in: {OUT_DIR}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Genera le immagini dei personaggi Marvel via Replicate FLUX"
    )
    parser.add_argument("--name", help="Genera solo questo personaggio")
    parser.add_argument("--overwrite", action="store_true", help="Rigenera quelle già esistenti")
    args = parser.parse_args()

    if not REPLICATE_API_TOKEN:
        print("ERRORE: REPLICATE_API_TOKEN non impostata nell'ambiente.")
        print("  export REPLICATE_API_TOKEN=r8_...")
        sys.exit(1)

    if args.name:
        names = [args.name]
    else:
        names = load_marvel_names()
        if not names:
            print("ERRORE: nessun personaggio Marvel trovato nei CSV.")
            sys.exit(1)
        print(f"Trovati {len(names)} personaggi Marvel.")

    generate_all(names, overwrite=args.overwrite)


if __name__ == "__main__":
    main()
