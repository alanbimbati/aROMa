import os
from PIL import Image, ImageDraw, ImageFont
import random
import hashlib

def get_color(name):
    """Generate a consistent color from name"""
    hash_object = hashlib.md5(name.encode())
    hex_hash = hash_object.hexdigest()
    r = int(hex_hash[0:2], 16)
    g = int(hex_hash[2:4], 16)
    b = int(hex_hash[4:6], 16)
    return (r, g, b)

def create_placeholder(name, path):
    """Create a placeholder image with text"""
    width, height = 512, 512
    bg_color = get_color(name)
    
    # Make bg slightly darker
    bg_color = (int(bg_color[0]*0.7), int(bg_color[1]*0.7), int(bg_color[2]*0.7))
    
    img = Image.new('RGB', (width, height), color=bg_color)
    draw = ImageDraw.Draw(img)
    
    # Try to load a font
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 40)
    except:
        try:
            font = ImageFont.load_default()
        except:
            font = None
            
    # Draw text
    text = name
    if font:
        # Get text size
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        x = (width - text_width) / 2
        y = (height - text_height) / 2
        draw.text((x, y), text, fill=(255, 255, 255), font=font)
    else:
        # Fallback if no font
        draw.text((10, height/2), text, fill=(255, 255, 255))
        
    # Add a border
    draw.rectangle([0, 0, width-1, height-1], outline=(255, 255, 255), width=5)
    
    # Ensure directory exists
    os.makedirs(os.path.dirname(path), exist_ok=True)
    
    img.save(path)
    print(f"✅ Generated: {path}")

def main():
    targets = [
        ("Cell", "images/miscellania/cell.png"),
        ("Majin Buu", "images/miscellania/majin_buu.png"),
        ("Broly", "images/miscellania/broly.png"),
        ("Beerus", "images/miscellania/beerus.png"),
        ("Vegeta", "images/miscellania/vegeta.png"),
        ("Freezer First Form", "images/miscellania/freezer_first_form.png"),
        ("Freezer Second Form", "images/miscellania/freezer_second_form.png"),
        ("Freezer Third Form", "images/miscellania/freezer_third_form.png"),
        ("Cell Imperfect", "images/miscellania/cell_imperfect.png"),
        ("Raditz", "images/miscellania/raditz.png"),
        ("Nappa", "images/miscellania/nappa.png"),
        ("Dodoria", "images/miscellania/dodoria.png"),
        ("Zarbon", "images/miscellania/zarbon.png"),
        ("Guldo", "images/miscellania/guldo.png"),
        ("Recoome", "images/miscellania/recoome.png"),
        ("Burter", "images/miscellania/burter.png"),
        ("Jeice", "images/miscellania/jeice.png"),
        ("Capitano Ginyu", "images/miscellania/capitano_ginyu.png"),
        ("C19", "images/miscellania/c19.png"),
        ("C20", "images/miscellania/c20.png"),
        ("C17", "images/miscellania/c17.png"),
        ("C18", "images/miscellania/c18.png"),
        ("Saibaman Elite", "images/miscellania/saibaman_elite.png")
    ]
    
    print(f"Generating {len(targets)} placeholder images...")
    
    for name, path in targets:
        # Skip if exists? No, overwrite to ensure we have something
        create_placeholder(name, path)
        
    print("Done!")

if __name__ == "__main__":
    main()
