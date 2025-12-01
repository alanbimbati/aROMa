#!/usr/bin/env python3
"""
Batch image generation script that handles rate limits
Generates images for all characters with 'unknown_small' placeholders
"""
import json
import time
import os
import sys

# Add parent directory to path for imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

TRACKING_FILE = "image_sources.json"
IMAGE_DIR = "images/characters"

# Character prompts for better image generation
CHARACTER_PROMPTS = {
    "artemis": "Artemis from Hades game, goddess of the hunt, green glowing aura, bow and arrows, elegant design, anime style",
    "roy": "Roy from Fire Emblem, red hair, young swordsman, determined expression, anime style, detailed armor",
    "corrin": "Corrin from Fire Emblem, dragon warrior, silver hair, detailed armor, fantasy RPG style",
    "mumbo_jumbo": "Mumbo Jumbo from Banjo-Kazooie, shaman character, mask, colorful design, game character art",
    "bayonetta": "Bayonetta, witch with guns, elegant and powerful, long black hair, stylish outfit, action game art",
    "ciri": "Ciri from The Witcher, white hair, scar on face, sword fighter, fantasy RPG style, detailed character",
    "horus": "Horus Egyptian god, falcon head, golden armor, divine presence, detailed mythology art",
    "ike": "Ike from Fire Emblem, blue hair, heavy sword Ragnell, muscular warrior, anime RPG style",
    "charmeleon": "Charmeleon Pokemon, red lizard with flame tail, angry expression, anime style, detailed scales",
    "broly": "Broly from Dragon Ball, legendary Super Saiyan, muscular, green aura, intense expression, anime style",
    "connor": "Connor from Assassin's Creed 3, Native American assassin, hood, tomahawk, detailed historical outfit",
    "vegeta": "Vegeta from Dragon Ball, spiky black hair, saiyan armor, proud warrior, anime style",
    "doom_slayer": "Doom Slayer, armored space marine, brutal, iconic helmet, dark sci-fi style, detailed armor",
    "pikachu": "Pikachu Pokemon, yellow electric mouse, red cheeks, cute expression, anime style, energetic pose",
    "luigi": "Luigi from Nintendo, green cap with L, mustache, green shirt, friendly expression, game character art",
}

def get_prompt_for_character(char_name, default_desc="video game character"):
    """Get optimized prompt for character"""
    if char_name in CHARACTER_PROMPTS:
        return f"{CHARACTER_PROMPTS[char_name]}, high quality portrait, 8k, detailed character design"
    return f"{char_name.replace('_', ' ').title()}, {default_desc}, high quality portrait, detailed face, 8k"

def load_tracking_data():
    """Load image tracking data"""
    try:
        with open(TRACKING_FILE, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading tracking file: {e}")
        return {}

def save_tracking_data(data):
    """Save image tracking data"""
    try:
        with open(TRACKING_FILE, 'w') as f:
            json.dump(data, f, indent=2)
        print("✓ Tracking data saved")
    except Exception as e:
        print(f"Error saving tracking file: {e}")

def get_placeholder_characters():
    """Get list of characters with placeholder images"""
    data = load_tracking_data()
    placeholders = []
    
    for char_name, info in data.items():
        if info.get('source') == 'unknown_small':
            placeholders.append(char_name)
    
    return sorted(placeholders)

def main():
    print("🎨 Batch Image Generation Script")
    print("=" * 60)
    
    placeholders = get_placeholder_characters()
    print(f"\nFound {len(placeholders)} characters with placeholders\n")
    
    if not placeholders:
        print("✅ All characters have images!")
        return
    
    print("Characters to generate:")
    for i, char in enumerate(placeholders[:20], 1):  # Show first 20
        print(f"  {i}. {char.replace('_', ' ').title()}")
    
    if len(placeholders) > 20:
        print(f"  ... and {len(placeholders) - 20} more")
    
    print("\n" + "=" * 60)
    print("NOTE: This script requires manual generation via Antigravity")
    print("      or an external API key for automated generation.")
    print("=" * 60)
    
    # Save list for reference
    with open('remaining_images.txt', 'w') as f:
        for char in placeholders:
            f.write(f"{char}\n")
    
    print("\n✓ List saved to remaining_images.txt")

if __name__ == "__main__":
    main()
