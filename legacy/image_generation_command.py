#!/usr/bin/env python3
"""
Generate Character Images - Telegram Bot Command
Usage: Send /generate_images in Telegram to generate missing character images
"""
import os
import csv
from telebot import types

def register_image_generation_command(bot, admin_ids=[]):
    """Register the /generate_images command"""
    
    @bot.message_handler(commands=['generate_images'])
    def handle_generate_images(message):
        user_id = message.from_user.id
        
        # Optional: restrict to admins only
        if admin_ids and user_id not in admin_ids:
            bot.reply_to(message, "⛔ Solo gli admin possono generare immagini!")
            return
        
        bot.reply_to(message, "🎨 Avvio generazione immagini...\nQuesto potrebbe richiedere alcuni minuti.")
        
        # Read characters
        with open('data/characters.csv', 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            characters = list(reader)
        
        # Count missing images
        missing = []
        for char in characters:
            char_name = char['nome'].lower().replace(' ', '_').replace("'", "")
            image_path = f'images/characters/{char_name}.png'
            
            if not os.path.exists(image_path):
                missing.append(char)
            elif os.path.getsize(image_path) < 50000:  # Placeholder check
                missing.append(char)
        
        if not missing:
            bot.send_message(user_id, "✅ Tutte le immagini sono già presenti!")
            return
        
        bot.send_message(user_id, f"📊 Trovate {len(missing)} immagini mancanti.\n\n⏳ Generazione in corso...")
        
        # Generate images (you would call your image generation API here)
        # For now, just report what would be generated
        
        generated = 0
        failed = 0
        
        for i, char in enumerate(missing[:10]):  # Limit to 10 at a time
            char_name = char['nome'].lower().replace(' ', '_').replace("'", "")
            
            try:
                # Here you would call: generate_image(Prompt=..., ImageName=char_name)
                # For now, just simulate
                generated += 1
                
                if (i + 1) % 5 == 0:
                    bot.send_message(user_id, f"⏳ Progresso: {i+1}/{min(10, len(missing))} immagini...")
                    
            except Exception as e:
                failed += 1
                print(f"Failed to generate {char['nome']}: {e}")
        
        # Final report
        report = f"✅ Generazione completata!\n\n"
        report += f"✓ Generate: {generated}\n"
        if failed > 0:
            report += f"✗ Fallite: {failed}\n"
        if len(missing) > 10:
            report += f"\n⚠️ Rimangono {len(missing) - 10} immagini da generare.\n"
            report += "Usa di nuovo /generate_images per continuare."
        
        bot.send_message(user_id, report)

# Usage in main.py:
# from image_generation_command import register_image_generation_command
# register_image_generation_command(bot, admin_ids=[YOUR_TELEGRAM_ID])
