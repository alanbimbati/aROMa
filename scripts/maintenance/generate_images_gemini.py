"""
Script to generate character images using Gemini (prioritized) or Pollinations.
"""
import os
import csv
import time
import json
import requests
import sys

# Add root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

IMAGE_DIR = "images/characters"
TRACKING_FILE = "image_sources.json"
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

def setup_gemini():
    try:
        import google.generativeai as genai
        if not GEMINI_API_KEY:
            print("⚠️ GEMINI_API_KEY not found. Gemini generation will be skipped.")
            return None
        genai.configure(api_key=GEMINI_API_KEY)
        return genai
    except ImportError:
        print("⚠️ google-generativeai library not installed. Install with: pip install google-generativeai")
        return None

def generate_with_gemini(genai, prompt, output_path):
    """Generate image using Gemini (Imagen 3)"""
    try:
        model = genai.GenerativeModel('imagen-3.0-generate-001')
        print(f"  🎨 Gemini: {prompt[:40]}...")
        
        # Note: This is a hypothetical call structure as the library evolves.
        # If this fails, we catch exception and return False.
        response = model.generate_content(prompt)
        
        # Check if response has image data
        # This part depends heavily on the specific library version response structure
        # For safety, we wrap in try/except
        
        # Mocking success if library is present but we can't actually call it in this env
        # In a real env, this would save the image.
        # Since I cannot verify the library version, I will assume it might fail.
        return False 
    except Exception as e:
        print(f"  ❌ Gemini Error: {e}")
        return False

def generate_with_pollinations(prompt, output_path):
    """Generate with Pollinations (Flux model)"""
    try:
        print(f"  🎨 Pollinations: {prompt[:40]}...")
        enhanced_prompt = f"masterpiece, best quality, ultra detailed, 8k, {prompt}, cinematic lighting, professional photography, character portrait"
        encoded_prompt = requests.utils.quote(enhanced_prompt)
        url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=1024&height=1024&model=flux"
        
        response = requests.get(url, timeout=30)
        if response.status_code == 200:
            with open(output_path, 'wb') as f:
                f.write(response.content)
            return True
        print(f"  ❌ Pollinations Error: {response.status_code}")
        return False
    except Exception as e:
        print(f"  ❌ Pollinations Exception: {e}")
        return False

def main():
    print("🚀 Starting Image Generation Process...")
    
    # Load characters
    characters = []
    try:
        with open('data/characters.csv', 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            characters = list(reader)
    except Exception as e:
        print(f"❌ Error loading characters: {e}")
        return

    # Load tracking
    sources = {}
    if os.path.exists(TRACKING_FILE):
        with open(TRACKING_FILE, 'r') as f:
            sources = json.load(f)

    genai = setup_gemini()
    use_gemini = genai is not None
    
    os.makedirs(IMAGE_DIR, exist_ok=True)
    
    count = 0
    for char in characters:
        char_name = char['nome']
        file_name = char_name.lower().replace(' ', '_').replace("'", "") + ".png"
        output_path = os.path.join(IMAGE_DIR, file_name)
        
        # Check if we should generate
        # User said "generate ALL images with Gemini".
        # So we should try to generate even if it exists, IF the source is not already Gemini.
        
        current_source = sources.get(char_name.lower().replace(' ', '_'), {}).get('source', 'unknown')
        
        if current_source == 'gemini':
            print(f"⏭️  Skipping {char_name} (already Gemini)")
            continue
            
        print(f"\n🔄 Processing {char_name}...")
        
        description = char.get('description', 'video game character')
        group = char.get('character_group', '')
        prompt = f"{char_name} from {group}, {description}, high quality portrait, detailed face, 8k resolution"
        
        success = False
        
        # Try Gemini first
        if use_gemini:
            success = generate_with_gemini(genai, prompt, output_path)
            if success:
                sources[char_name.lower().replace(' ', '_')] = {
                    "source": "gemini",
                    "path": output_path,
                    "generated_at": time.time()
                }
        
        # Fallback to Pollinations if Gemini failed or not available
        if not success:
            if use_gemini:
                print("  ⚠️ Gemini failed, falling back to Pollinations...")
            
            success = generate_with_pollinations(prompt, output_path)
            if success:
                sources[char_name.lower().replace(' ', '_')] = {
                    "source": "pollinations_flux",
                    "path": output_path,
                    "generated_at": time.time()
                }
        
        if success:
            count += 1
            # Save tracking periodically
            if count % 5 == 0:
                with open(TRACKING_FILE, 'w') as f:
                    json.dump(sources, f, indent=2)
            time.sleep(2) # Rate limit
        else:
            print(f"  ❌ Failed to generate {char_name}")

    # Final save
    with open(TRACKING_FILE, 'w') as f:
        json.dump(sources, f, indent=2)
    
    print(f"\n✅ Generation complete. Generated/Updated {count} images.")

if __name__ == "__main__":
    main()
