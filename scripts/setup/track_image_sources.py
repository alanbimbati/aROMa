"""
Script to track image sources (Gemini vs Placeholder)
"""
import os
import json
import glob

IMAGE_DIR = "images/characters"
TRACKING_FILE = "image_sources.json"

def scan_images():
    """Scan images and try to determine source based on file size/date"""
    # This is a best-effort initial scan
    # Placeholders are usually small (< 50KB?) or created recently
    # Gemini images might be larger
    
    sources = {}
    if os.path.exists(TRACKING_FILE):
        with open(TRACKING_FILE, 'r') as f:
            sources = json.load(f)
            
    files = glob.glob(os.path.join(IMAGE_DIR, "*.png"))
    
    for file_path in files:
        filename = os.path.basename(file_path)
        char_name = filename.replace(".png", "")
        
        if char_name not in sources:
            # Guess source
            size = os.path.getsize(file_path)
            if size < 100000: # < 100KB likely placeholder or simple generation
                source = "unknown_small"
            else:
                source = "unknown_large"
                
            sources[char_name] = {
                "source": source,
                "path": file_path,
                "size": size
            }
            
    with open(TRACKING_FILE, 'w') as f:
        json.dump(sources, f, indent=2)
        
    print(f"Tracked {len(sources)} images.")

if __name__ == "__main__":
    scan_images()
