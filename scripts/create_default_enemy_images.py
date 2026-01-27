"""
Script to create default generic images for mobs and bosses
"""
try:
    from PIL import Image, ImageDraw, ImageFont
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    print("⚠️ PIL/Pillow non disponibile. Installa con: pip install Pillow")
    print("Oppure aggiungi manualmente le immagini:")
    print("  - images/mobs/default.png (256x256, mostro semplice)")
    print("  - images/bosses/default.png (256x256, boss potente)")

def create_mob_image():
    """Create a generic mob image"""
    if not PIL_AVAILABLE:
        return False
    
    # Create 256x256 image with dark background
    img = Image.new('RGB', (256, 256), color='#2d5016')  # Dark green
    draw = ImageDraw.Draw(img)
    
    # Draw a simple monster shape (circle body + eyes)
    # Body (circle)
    draw.ellipse([50, 80, 206, 236], fill='#4a7c2a', outline='#1a3009', width=3)
    
    # Head (smaller circle)
    draw.ellipse([80, 40, 176, 136], fill='#5a8c3a', outline='#1a3009', width=3)
    
    # Eyes (red glowing)
    draw.ellipse([100, 70, 120, 90], fill='#ff0000')
    draw.ellipse([136, 70, 156, 90], fill='#ff0000')
    
    # Mouth (simple line)
    draw.arc([100, 100, 156, 120], start=0, end=180, fill='#000000', width=4)
    
    # Save
    img.save('images/default.png')
    print("✅ Creata immagine generica: images/default.png")
    return True

def create_boss_image():
    """Create a generic boss image (unused for now, using default.png)"""
    return True

if __name__ == "__main__":
    import os
    import sys
    
    # Add parent directory to path
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    # Create directories
    os.makedirs('images', exist_ok=True)
    
    print("🎨 Creazione immagini generiche per nemici...\n")
    
    mob_ok = create_mob_image()
    
    if mob_ok:
        print("\n✅ Immagine default creata con successo!")
    else:
        print("\n⚠️ Aggiungi manualmente le immagini se necessario.")

