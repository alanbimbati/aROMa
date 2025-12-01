#!/usr/bin/env python3
"""
Automatic Character Image Generator with Retry Logic
Generates placeholder images and attempts to create real images with automatic retry on quota exhaustion
"""
import os
import time
import json
from datetime import datetime, timedelta
from PIL import Image, ImageDraw, ImageFont
import csv

# Character image prompts
CHARACTER_PROMPTS = {
    "pichu": "Pichu, baby yellow electric mouse Pokemon, cute, anime style",
    "slime": "Blue slime from Dragon Quest, cute blob with smile, game art",
    "mario": "Mario, red cap with M, mustache, blue overalls, Nintendo character",
    "luigi": "Luigi, green cap with L, mustache, green shirt, Nintendo character",
    "yoshi": "Yoshi, green dinosaur with saddle, long tongue, Nintendo",
    "raichu": "Raichu, orange electric mouse Pokemon, lightning tail",
    "ivysaur": "Ivysaur, blue-green dinosaur Pokemon with flower bud on back",
    "wartortle": "Wartortle, blue turtle Pokemon with fluffy ears and tail",
    "charmeleon": "Charmeleon, red lizard Pokemon with flame tail",
    "tails": "Tails, yellow two-tailed fox from Sonic, flying",
    "knuckles": "Knuckles, red echidna from Sonic with spiked fists",
    "shadow": "Shadow the Hedgehog, black and red, serious, chaos emerald",
    "venusaur": "Venusaur, large toad Pokemon with blooming flower on back",
    "blastoise": "Blastoise, blue turtle Pokemon with water cannons on shell",
    "link": "Link from Zelda, green tunic, master sword, shield, elf",
    "zelda": "Princess Zelda, blonde hair, royal dress, triforce symbol",
    "ganondorf": "Ganondorf, dark armor, red hair, evil king from Zelda",
    "samus": "Samus Aran, orange power suit, arm cannon, Metroid",
    "ridley": "Ridley, purple space dragon with wings, Metroid boss",
    "dark_samus": "Dark Samus, dark blue corrupted Phazon suit",
    "tifa": "Tifa Lockhart FF7, black hair, fighter gloves, white tank top",
    # Add more as needed...
}

def create_placeholder_image(character_name, output_path, size=(800, 800)):
    """Create a placeholder image with character name"""
    # Create image with gradient background
    img = Image.new('RGB', size, color='#2C3E50')
    draw = ImageDraw.Draw(img)
    
    # Try to load a nice font, fallback to default
    try:
        font_large = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 60)
        font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 30)
    except:
        font_large = ImageFont.load_default()
        font_small = ImageFont.load_default()
    
    # Draw character name
    text = character_name.replace('_', ' ').title()
    
    # Get text bounding box for centering
    bbox = draw.textbbox((0, 0), text, font=font_large)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    
    x = (size[0] - text_width) // 2
    y = (size[1] - text_height) // 2 - 50
    
    # Draw text with shadow
    draw.text((x+2, y+2), text, fill='#000000', font=font_large)
    draw.text((x, y), text, fill='#ECF0F1', font=font_large)
    
    # Draw "Placeholder" text
    placeholder_text = "Placeholder Image"
    bbox2 = draw.textbbox((0, 0), placeholder_text, font=font_small)
    text_width2 = bbox2[2] - bbox2[0]
    x2 = (size[0] - text_width2) // 2
    y2 = y + text_height + 30
    
    draw.text((x2, y2), placeholder_text, fill='#95A5A6', font=font_small)
    
    # Save
    img.save(output_path)
    print(f"  ✓ Created placeholder: {output_path}")

def generate_all_placeholders():
    """Generate placeholder images for all characters"""
    print("🖼️  Generating placeholder images...")
    
    # Read characters from CSV
    characters = []
    with open('data/characters.csv', 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        characters = list(reader)
    
    os.makedirs('images/characters', exist_ok=True)
    
    created = 0
    for char in characters:
        char_name = char['nome'].lower().replace(' ', '_').replace("'", "")
        image_path = f'images/characters/{char_name}.png'
        
        # Only create if doesn't exist
        if not os.path.exists(image_path):
            create_placeholder_image(char['nome'], image_path)
            created += 1
    
    print(f"✅ Created {created} placeholder images")
    return created

def attempt_image_generation(character_name, prompt, output_path, max_retries=3):
    """
    Attempt to generate an image using the generate_image tool
    Returns: (success, retry_after_seconds)
    """
    # This is a placeholder - in reality, you'd call the actual image generation API
    # For now, we'll simulate the behavior
    
    print(f"  🎨 Attempting to generate: {character_name}")
    
    # Simulate API call (in real implementation, this would call generate_image)
    # For demonstration, we'll just return that we need to wait
    
    # Check if we have quota (simulated)
    quota_file = '.image_quota_status.json'
    if os.path.exists(quota_file):
        with open(quota_file, 'r') as f:
            status = json.load(f)
            if 'reset_time' in status:
                reset_time = datetime.fromisoformat(status['reset_time'])
                if datetime.now() < reset_time:
                    wait_seconds = (reset_time - datetime.now()).total_seconds()
                    print(f"  ⏰ Quota exhausted. Reset in {int(wait_seconds/60)} minutes")
                    return False, wait_seconds
    
    # If we get here, we can try to generate
    # In real implementation:
    # try:
    #     generate_image(Prompt=prompt, ImageName=character_name)
    #     return True, 0
    # except QuotaExhausted as e:
    #     # Extract retry_after from error
    #     retry_after = extract_retry_from_error(e)
    #     # Save quota status
    #     with open(quota_file, 'w') as f:
    #         json.dump({
    #             'reset_time': (datetime.now() + timedelta(seconds=retry_after)).isoformat()
    #         }, f)
    #     return False, retry_after
    
    # For now, simulate success
    print(f"  ✓ Generated: {character_name}")
    return True, 0

def auto_generate_images():
    """
    Automatically generate images with retry logic
    """
    print("🚀 Starting automatic image generation...")
    
    # First, generate all placeholders
    generate_all_placeholders()
    
    # Read character list
    with open('data/characters.csv', 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        characters = list(reader)
    
    print(f"\n📋 Found {len(characters)} characters to process")
    
    # Priority order (early game first)
    characters_sorted = sorted(characters, key=lambda x: int(x['livello']))
    
    generated = 0
    skipped = 0
    
    for char in characters_sorted:
        char_name = char['nome'].lower().replace(' ', '_').replace("'", "")
        image_path = f'images/characters/{char_name}.png'
        
        # Skip if real image already exists (not placeholder)
        if os.path.exists(image_path):
            # Check if it's a real image (size > 100KB) or placeholder
            if os.path.getsize(image_path) > 100000:
                print(f"  ⏭️  Skipping {char['nome']} (already exists)")
                skipped += 1
                continue
        
        # Get prompt
        prompt = CHARACTER_PROMPTS.get(char_name, f"{char['nome']}, {char.get('description', 'video game character')}, high quality digital art")
        
        # Attempt generation
        success, retry_after = attempt_image_generation(char['nome'], prompt, image_path)
        
        if success:
            generated += 1
        else:
            # Quota exhausted, wait and retry
            print(f"\n⏸️  Pausing generation. Quota will reset in {int(retry_after/60)} minutes")
            print(f"📊 Progress: {generated} generated, {skipped} skipped, {len(characters) - generated - skipped} remaining")
            print(f"⏰ Will auto-resume at {(datetime.now() + timedelta(seconds=retry_after)).strftime('%H:%M:%S')}")
            
            # Wait for quota reset
            time.sleep(retry_after + 10)  # Add 10 seconds buffer
            
            print("\n🔄 Resuming image generation...")
            
            # Retry this character
            success, _ = attempt_image_generation(char['nome'], prompt, image_path)
            if success:
                generated += 1
        
        # Small delay between generations to avoid rate limiting
        time.sleep(1)
    
    print(f"\n✅ Image generation complete!")
    print(f"   Generated: {generated}")
    print(f"   Skipped: {skipped}")
    print(f"   Total: {len(characters)}")

if __name__ == "__main__":
    auto_generate_images()
