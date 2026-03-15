#!/usr/bin/env python3
import argparse
import os
import sys
import time
from typing import Iterable, List, Optional


def ensure_local_venv_python() -> None:
    """Re-exec script with the project image venv if available.

    This prevents NumPy/SciPy ABI issues from the system interpreter.
    """
    if os.environ.get("AROMA_IMG_SKIP_REEXEC") == "1":
        return

    script_dir = os.path.dirname(os.path.abspath(__file__))
    repo_root = os.path.dirname(script_dir)
    venv_python = os.path.join(repo_root, ".venv_img", "bin", "python")

    if not os.path.exists(venv_python):
        return
    if os.path.abspath(sys.executable) == os.path.abspath(venv_python):
        return

    os.environ["AROMA_IMG_SKIP_REEXEC"] = "1"
    os.execv(venv_python, [venv_python] + sys.argv)


ensure_local_venv_python()

import torch
from diffusers import AutoPipelineForText2Image, EulerAncestralDiscreteScheduler
from PIL import Image
from transformers import CLIPModel, CLIPProcessor

try:
    from generate_marvel_epic_images import MARVEL_NAMES, slugify
except Exception:
    MARVEL_NAMES = []

    def slugify(name: str) -> str:
        s = name.lower().replace("’", "").replace("'", "")
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


def build_character_hint(name: str) -> str:
    key = name.casefold()
    if key in CHARACTER_STYLE_HINTS:
        return CHARACTER_STYLE_HINTS[key]
    for token, hint in TOKEN_STYLE_HINTS.items():
        if token in key:
            return hint
    return (
        "iconic superhero costume faithful to comic source, recognizable face/mask, "
        "single hero only"
    )


def build_prompt(name: str) -> str:
    style_hint = build_character_hint(name)
    return (
        f"{name} superhero portrait, single subject, centered, head and torso, "
        f"{style_hint}, cinematic comic style, dramatic rim light, "
        "detailed costume textures, sharp focus, clean anatomy, premium key art, "
        "vibrant colors, highly detailed digital painting"
    )


def negative_prompt() -> str:
    return (
        "blurry, low quality, text, watermark, logo, bad anatomy, deformed, "
        "duplicate character, multiple characters, two people, twin, mirrored body, "
        "extra limbs, extra head, extra arms, double face, cloned face, "
        "mutated hands, cropped, lowres, monochrome, grayscale, disfigured, "
        "distorted costume, wrong costume colors, body merged"
    )


def load_pipeline(model: str) -> AutoPipelineForText2Image:
    pipe = AutoPipelineForText2Image.from_pretrained(model, torch_dtype=torch.float32)
    pipe = pipe.to("cpu")
    pipe.enable_attention_slicing()
    pipe.scheduler = EulerAncestralDiscreteScheduler.from_config(pipe.scheduler.config)
    if hasattr(pipe, "safety_checker") and pipe.safety_checker is not None:
        pipe.safety_checker = lambda images, **kwargs: (images, [False] * len(images))
    return pipe


def load_ranker(enabled: bool):
    if not enabled:
        return None, None
    model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32")
    processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")
    return model, processor


def clip_score(image: Image.Image, prompt: str, model, processor) -> float:
    inputs = processor(
        text=[prompt],
        images=[image],
        return_tensors="pt",
        padding=True,
        truncation=True,
        max_length=77,
    )
    with torch.no_grad():
        out = model(**inputs)
    text = out.text_embeds / out.text_embeds.norm(p=2, dim=-1, keepdim=True)
    img = out.image_embeds / out.image_embeds.norm(p=2, dim=-1, keepdim=True)
    return float((text @ img.T).item())


def generate_one(
    pipe: AutoPipelineForText2Image,
    rank_model,
    rank_processor,
    name: str,
    out_path: str,
    steps: int,
    guidance: float,
    width: int,
    height: int,
    variants: int,
    base_seed: Optional[int],
) -> None:
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    prompt = build_prompt(name)

    best_image = None
    best_score = float("-inf")
    for i in range(max(1, variants)):
        generator = None
        if base_seed is not None:
            generator = torch.Generator(device="cpu").manual_seed(base_seed + i)

        image = pipe(
            prompt=prompt,
            negative_prompt=negative_prompt(),
            num_inference_steps=steps,
            guidance_scale=guidance,
            width=width,
            height=height,
            generator=generator,
        ).images[0]

        score = 0.0
        if rank_model is not None and rank_processor is not None:
            score = clip_score(image, prompt, rank_model, rank_processor)
        if score >= best_score:
            best_score = score
            best_image = image

    assert best_image is not None
    best_image.save(out_path)


def parse_names(
    csv_path: Optional[str], csv_col: str, names: Optional[str], batch_marvel: bool
) -> List[str]:
    parsed: List[str] = []

    if names:
        parsed.extend([n.strip() for n in names.split(",") if n.strip()])

    if csv_path:
        import csv

        with open(csv_path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                n = (row.get(csv_col) or "").strip()
                if n:
                    parsed.append(n)

    if batch_marvel:
        parsed.extend(MARVEL_NAMES)

    # De-duplicate while preserving order
    seen = set()
    unique: List[str] = []
    for n in parsed:
        k = n.casefold()
        if k in seen:
            continue
        seen.add(k)
        unique.append(n)
    return unique


def pick_guidance(model: str, explicit_guidance: Optional[float]) -> float:
    if explicit_guidance is not None:
        return explicit_guidance
    return 0.0 if "turbo" in model.lower() else 7.5


def iter_slice(names: List[str], start: int, limit: int) -> Iterable[str]:
    if start < 0:
        start = 0
    if limit <= 0:
        return names[start:]
    return names[start : start + limit]


CHARACTER_STYLE_HINTS = {
    "spider-man": "classic red and blue suit with white eye lenses, web pattern, no black suit",
    "iron man": "classic red and gold armor, arc reactor chest light, no duplicate body",
    "captain america": "blue suit with white star and red stripes, iconic shield",
    "thor": "asgardian armor, red cape, short hair, lightning aura",
    "hulk": "green skin, massive muscular build, purple pants",
    "black panther": "black vibranium suit with silver accents and cat-like mask",
}

TOKEN_STYLE_HINTS = {
    "widow": "black tactical stealth suit with red hourglass insignia",
    "hawkeye": "purple tactical archer suit, quiver and bow visible",
    "strange": "blue mystic robes and red cloak of levitation, glowing magic sigils",
    "scarlet": "red chaos magic aura and crimson outfit, elegant mystic look",
    "vision": "synthezoid red face with yellow forehead gem, green/yellow suit",
    "panther": "sleek black panther armor with silver lines",
    "thanos": "purple titan with gold armor, powerful imposing portrait",
    "loki": "green and gold asgardian outfit, horned crown",
    "wolverine": "yellow and blue suit, black pointed mask fins, adamantium claws",
    "deadpool": "red and black tactical suit, white eye patches, katanas",
    "punisher": "black tactical outfit with white skull chest emblem",
    "daredevil": "dark red vigilante suit with horned mask",
    "ghost rider": "flaming skull, black leather jacket, hellfire glow",
    "doctor doom": "green cloak and steel mask, regal armored villain",
    "goblin": "green armored glider villain style, menacing grin",
    "venom": "black symbiote body with white spider emblem, sharp teeth",
    "carnage": "red symbiote tendrils, chaotic monstrous silhouette",
    "america chavez": "star-themed jacket, confident hero pose",
}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--name")
    parser.add_argument("--out")
    parser.add_argument("--names", help="Comma-separated names")
    parser.add_argument("--csv-path", help="Optional CSV file containing character names")
    parser.add_argument("--csv-col", default="nome")
    parser.add_argument("--batch-marvel", action="store_true")
    parser.add_argument("--out-dir", default="assets/characters/marvel")
    parser.add_argument("--model", default="runwayml/stable-diffusion-v1-5")
    parser.add_argument("--steps", type=int, default=22)
    parser.add_argument("--guidance", type=float, default=None)
    parser.add_argument("--quality", choices=["balanced", "ultra"], default="balanced")
    parser.add_argument("--variants", type=int, default=1)
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--no-ranker", action="store_true")
    parser.add_argument("--w", type=int, default=640)
    parser.add_argument("--h", type=int, default=640)
    parser.add_argument("--start", type=int, default=0)
    parser.add_argument("--limit", type=int, default=0, help="0 means no limit")
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    if args.name and args.out:
        names = [args.name]
        explicit_out = args.out
    else:
        names = parse_names(args.csv_path, args.csv_col, args.names, args.batch_marvel)
        explicit_out = None
        if not names:
            raise SystemExit(
                "No names to generate. Use --name/--out or one of --batch-marvel, --names, --csv-path."
            )

    names = list(iter_slice(names, args.start, args.limit))
    guidance = pick_guidance(args.model, args.guidance)
    if args.seed is None:
        args.seed = 1337

    if args.quality == "ultra":
        if args.steps < 28:
            args.steps = 28
        if args.w < 768:
            args.w = 768
        if args.h < 768:
            args.h = 768
        if args.guidance is None:
            guidance = 8.0

    print(
        f"Loading model: {args.model} | steps={args.steps} | guidance={guidance} | size={args.w}x{args.h} | variants={args.variants}"
    )
    pipe = load_pipeline(args.model)
    rank_model, rank_processor = load_ranker(not args.no_ranker and args.variants > 1)

    total = len(names)
    generated = 0
    skipped = 0
    started = time.time()

    for idx, name in enumerate(names, start=1):
        out_path = explicit_out or os.path.join(args.out_dir, f"{slugify(name)}.png")
        if (not args.overwrite) and os.path.exists(out_path):
            skipped += 1
            print(f"[{idx}/{total}] skip {name} -> {out_path}")
            continue

        t0 = time.time()
        generate_one(
            pipe,
            rank_model,
            rank_processor,
            name,
            out_path,
            args.steps,
            guidance,
            args.w,
            args.h,
            variants=args.variants,
            base_seed=args.seed,
        )
        dt = time.time() - t0
        generated += 1
        print(f"[{idx}/{total}] saved {name} -> {out_path} ({dt:.1f}s)")

    elapsed = time.time() - started
    print(
        f"Done. generated={generated} skipped={skipped} total={total} elapsed={elapsed/60:.1f}m"
    )


if __name__ == "__main__":
    main()
