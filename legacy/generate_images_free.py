#!/usr/bin/env python3
"""
Automatic Character Image Generator - FREE APIs
Uses free image generation APIs (no account needed)
"""
import os
import csv
import requests
import time
from PIL import Image
from io import BytesIO

# Free API options (no registration required)
POLLINATIONS_API = "https://image.pollinations.ai/prompt/{prompt}"
REPLICATE_FREE = "https://api.replicate.com/v1/predictions"

def generate_image_pollinations(prompt, output_path):
    """
    Generate image using Pollinations.ai (FREE, no API key)
    """
    try:
        # Clean prompt for URL
        clean_prompt = prompt.replace(' ', '%20')
        url = f"https://image.pollinations.ai/prompt/{clean_prompt}?width=800&height=800&nologo=true"
        
        print(f"  🎨 Generating with Pollinations.ai...")
        response = requests.get(url, timeout=30)
        
        if response.status_code == 200:
            img = Image.open(BytesIO(response.content))
            img.save(output_path)
            print(f"  ✅ Generated: {output_path}")
            return True
        else:
            print(f"  ❌ Failed: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return False

def generate_image_artbot(prompt, output_path):
    """
    Generate image using Artbot.ai (FREE, no API key)
    """
    try:
        url = "https://api.artbot.ai/generate"
        
        payload = {
            "prompt": prompt,
            "width": 800,
            "height": 800,
            "steps": 20
        }
        
        print(f"  🎨 Generating with Artbot.ai...")
        response = requests.post(url, json=payload, timeout=60)
        
        if response.status_code == 200:
            data = response.json()
            image_url = data.get('image_url')
            
            if image_url:
                img_response = requests.get(image_url)
                img = Image.open(BytesIO(img_response.content))
                img.save(output_path)
                print(f"  ✅ Generated: {output_path}")
                return True
                
        print(f"  ❌ Failed: {response.status_code}")
        return False
        
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return False

def generate_image_craiyon(prompt, output_path):
    """
    Generate image using Craiyon (formerly DALL-E mini) - FREE
    """
    try:
        url = "https://backend.craiyon.com/generate"
        
        payload = {"prompt": prompt}
        
        print(f"  🎨 Generating with Craiyon...")
        response = requests.post(url, json=payload, timeout=120)
        
        if response.status_code == 200:
            data = response.json()
            images = data.get('images', [])
            
            if images:
                # Get first image (base64)
                import base64
                img_data = base64.b64decode(images[0])
                img = Image.open(BytesIO(img_data))
                img.save(output_path)
                print(f"  ✅ Generated: {output_path}")
                return True
                
        print(f"  ❌ Failed: {response.status_code}")
        return False
        
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return False

# Character prompts with better descriptions
CHARACTER_PROMPTS = {
    "chocobo": "Yellow bird creature from Final Fantasy, cute, game art style",
    "pichu": "Pichu Pokemon, baby electric mouse, yellow, cute anime style",
    "slime": "Blue slime from Dragon Quest, cute blob, game art",
    "pikachu": "Pikachu Pokemon, yellow electric mouse, red cheeks, anime",
    "bulbasaur": "Bulbasaur Pokemon, green dinosaur with plant bulb, anime",
    "squirtle": "Squirtle Pokemon, blue turtle, anime style",
    "charmander": "Charmander Pokemon, orange lizard with flame tail, anime",
    "crash_bandicoot": "Crash Bandicoot, orange marsupial, video game character",
    "spyro": "Spyro the Dragon, purple dragon, video game character",
    "sonic": "Sonic the Hedgehog, blue hedgehog, video game character",
    "mario": "Mario, red cap, mustache, blue overalls, Nintendo",
    "luigi": "Luigi, green cap, mustache, Nintendo character",
    "goku": "Goku from Dragon Ball, spiky black hair, orange gi, anime",
    "vegeta": "Vegeta from Dragon Ball, spiky black hair, saiyan armor, anime",
    "cloud": "Cloud Strife from Final Fantasy 7, blonde spiky hair, buster sword",
    "link": "Link from Zelda, green tunic, master sword, elf ears",
    # Add more as needed...
}

def get_prompt_for_character(char_name, char_description):
    """Generate a good prompt for character"""
    # Check if we have a custom prompt
    if char_name in CHARACTER_PROMPTS:
        return CHARACTER_PROMPTS[char_name]
    
    # Generate from description
    base = f"{char_name.replace('_', ' ').title()}"
    
    if char_description:
        return f"{base}, {char_description}, high quality digital art, video game character"
    else:
        return f"{base}, video game character, high quality digital art"

def auto_generate_all_images():
    """
    Automatically generate ALL character images using FREE APIs
    """
    print("🚀 Starting AUTOMATIC image generation with FREE APIs...")
    print("📝 No API keys needed, no account required!\n")
    
    # Read characters
    with open('data/characters.csv', 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        characters = list(reader)
    
    print(f"📋 Found {len(characters)} characters\n")
    
    # Create directory
    os.makedirs('images/characters', exist_ok=True)
    
    # Sort by level (generate early game first)
    characters_sorted = sorted(characters, key=lambda x: int(x['livello']))
    
    generated = 0
    skipped = 0
    failed = 0
    
    for i, char in enumerate(characters_sorted, 1):
        char_name = char['nome'].lower().replace(' ', '_').replace("'", "").replace(".", "")
        image_path = f'images/characters/{char_name}.png'
        
        print(f"\n[{i}/{len(characters)}] {char['nome']} (Lv {char['livello']})")
        
        # Skip if already exists and is not a placeholder
        if os.path.exists(image_path):
            size = os.path.getsize(image_path)
            if size > 100000:  # Real image
                print(f"  ⏭️  Already exists (skipping)")
                skipped += 1
                continue
            else:
                print(f"  🔄 Replacing placeholder...")
        
        # Get prompt
        prompt = get_prompt_for_character(char_name, char.get('description', ''))
        print(f"  📝 Prompt: {prompt[:60]}...")
        
        # Try multiple APIs until one works
        success = False
        
        # Try Pollinations.ai first (fastest and most reliable)
        if not success:
            success = generate_image_pollinations(prompt, image_path)
        
        # If failed, try Craiyon
        if not success:
            print(f"  🔄 Trying alternative API...")
            time.sleep(2)
            success = generate_image_craiyon(prompt, image_path)
        
        if success:
            generated += 1
            print(f"  ✅ Success! ({generated} total)")
        else:
            failed += 1
            print(f"  ❌ Failed to generate")
        
        # Rate limiting (be nice to free APIs)
        if i % 10 == 0:
            print(f"\n⏸️  Pausing 5 seconds (rate limiting)...")
            time.sleep(5)
        else:
            time.sleep(1)
        
        # Progress report every 25 images
        if i % 25 == 0:
            print(f"\n📊 Progress Report:")
            print(f"   ✅ Generated: {generated}")
            print(f"   ⏭️  Skipped: {skipped}")
            print(f"   ❌ Failed: {failed}")
            print(f"   📈 Completion: {int((i/len(characters))*100)}%\n")
    
    # Final report
    print(f"\n{'='*60}")
    print(f"✅ GENERATION COMPLETE!")
    print(f"{'='*60}")
    print(f"✅ Generated: {generated}")
    print(f"⏭️  Skipped: {skipped}")
    print(f"❌ Failed: {failed}")
    print(f"📊 Total: {len(characters)}")
    print(f"{'='*60}\n")

if __name__ == "__main__":
    auto_generate_all_images()
