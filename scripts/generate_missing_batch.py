import os
import time
from database import Database

# List of missing characters/mobs based on find_missing_images.py output
# Format: (Type, Name, Filename)
MISSING_IMAGES = [
    ("mob", "Xenomorph Warrior", "xenomorph_warrior.png"),
    ("mob", "Praetorian", "praetorian.png"),
    ("mob", "Queen", "queen.png"),
    ("mob", "Necromorph Brute", "necromorph_brute.png"),
    ("mob", "Necromorph Divider", "necromorph_divider.png"),
    ("mob", "Houdini Splicer", "houdini_splicer.png"),
    ("mob", "Nitro Splicer", "nitro_splicer.png"),
    ("mob", "Vegeta (Scouter)", "vegeta_(scouter).png"),
    ("mob", "Cui", "cui.png"),
    ("mob", "Freezer (First Form)", "freezer_(first_form).png"),
    ("mob", "Freezer (Second Form)", "freezer_(second_form).png"),
    ("mob", "Freezer (Third Form)", "freezer_(third_form).png"),
    ("mob", "Freezer (Final Form)", "freezer_(final_form).png"),
    ("mob", "Cell (Imperfect)", "cell_(imperfect).png"),
    ("mob", "Cell (Semi-Perfect)", "cell_(semi-perfect).png"),
    ("mob", "Cell (Perfect)", "cell_(perfect).png"),
    ("mob", "Cell (Super Perfect)", "cell_(super_perfect).png"),
    ("mob", "Majin Buu (Fat)", "majin_buu_(fat).png"),
    ("mob", "Goku Black Base", "goku_black_base.png"),
    ("mob", "Immortal Zamasu", "immortal_zamasu.png"),
    ("boss", "Goku Black Rose", "goku_black_rose.png"),
    ("boss", "Corrupted Zamasu", "corrupted_zamasu.png")
]

PROMPTS = {
    "Xenomorph Warrior": "Xenomorph Warrior from Alien, dark biomechanical creature with elongated head, sharp claws, acid drool, dark sci-fi horror atmosphere, detailed, 8k",
    "Praetorian": "Praetorian Xenomorph from Alien, larger and more armored than warrior, massive crest on head, menacing posture, dark sci-fi background, highly detailed",
    "Queen": "Alien Queen Xenomorph, massive size, huge crest, multiple arms, laying eggs in background, terrifying and majestic, dark blue lighting, 8k",
    "Necromorph Brute": "Necromorph Brute from Dead Space, massive and heavily armored with bone plates, fleshy weak points, horrific mutation, space horror style",
    "Necromorph Divider": "Necromorph Divider from Dead Space, tall and lanky creature that can split apart, horrific body horror, dark corridor background, detailed",
    "Houdini Splicer": "Houdini Splicer from Bioshock, 1950s suit tattered, wearing a mask, fading into smoke/teleporting, fire magic in hand, art deco rupture background",
    "Nitro Splicer": "Nitro Splicer from Bioshock, crazy bomber carrying cocktails/grenades, vintage clothes, mask, rapturian aesthetic, detailed",
    "Vegeta (Scouter)": "Vegeta with Scouter from Dragon Ball Z, Saiyan armor with shoulder pads, scouter on eye, arms crossed, arrogant expression, anime style, high quality",
    "Cui": "Cui from Dragon Ball Z, purple alien with fish-like face, Frieza Force armor, scouter, anime style, cel shaded",
    "Freezer (First Form)": "Frieza First Form from Dragon Ball Z, small humanoid with horns, sitting in hover pod, evil smirk, anime style, detailed",
    "Freezer (Second Form)": "Frieza Second Form from Dragon Ball Z, tall and muscular, long horns curved up, terrifying presence, anime style",
    "Freezer (Third Form)": "Frieza Third Form from Dragon Ball Z, xenomorph-like head elongated, hunchback, monstrous, anime style",
    "Freezer (Final Form)": "Frieza Final Form from Dragon Ball Z, sleek white and purple design, small but menacing, aura of power, anime style 8k",
    "Cell (Imperfect)": "Cell Imperfect Form from Dragon Ball Z, insect-like appearance, green with spots, beak-like mouth, tail with stinger, anime style",
    "Cell (Semi-Perfect)": "Cell Semi-Perfect Form from Dragon Ball Z, bulkier, more human face but still insect features, big lips, desperate expression, anime style",
    "Cell (Perfect)": "Perfect Cell from Dragon Ball Z, handsome insectoid humanoid, green and white armor plates, confident smile, arms crossed, anime style 8k",
    "Cell (Super Perfect)": "Super Perfect Cell from Dragon Ball Z, surrounded by lightning, golden aura, fierce expression, Kamehameha pose, anime style high quality",
    "Majin Buu (Fat)": "Majin Buu Fat from Dragon Ball Z, pink round creature, cape and vest, happy but dangerous expression, steam coming from holes, anime style",
    "Goku Black Base": "Goku Black Base form from Dragon Ball Super, wearing black gi, red belt, single earring, evil smirk, dark aura, anime style",
    "Immortal Zamasu": "Zamasu from Dragon Ball Super, green skin, white hair, kaioshin outfit, halo of light behind him, arrogant god pose, anime style",
    "Goku Black Rose": "Goku Black Super Saiyan Rose, pink hair, dark pink aura, scythe of energy, menacing and elegant, anime style 8k",
    "Corrupted Zamasu": "Fused Zamasu Corrupted, half purple slimy monster half god, halo is broken, insane expression, gigantic arm, anime style detailed"
}

def print_batch_instructions():
    print("Detected missing images. Use the generate_image tool manually for each:")
    for type, name, filename in MISSING_IMAGES:
        prompt = PROMPTS.get(name, f"{name}, high quality, detailed character art")
        print(f"\n--- {name} ({type}) ---")
        print(f"Tool Usage: generate_image(Prompt='{prompt}', ImageName='{filename.replace('.png', '')}')")

if __name__ == "__main__":
    print_batch_instructions()
