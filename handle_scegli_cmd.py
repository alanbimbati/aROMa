@bot.message_handler(commands=['scegli', 'personaggio'])
def handle_scegli_cmd(message):
    """Show character selection menu"""
    user_id = message.from_user.id
    utente = user_service.get_user(user_id)
    
    if not utente:
        bot.reply_to(message, "❌ Utente non trovato. Usa /start per registrarti.")
        return
    
    from services.character_service import CharacterService
    char_service = CharacterService()
    
    # Get available characters for this user
    characters, total_pages, current_page = char_service.get_characters_paginated(utente, page=0, per_page=1)
    
    if not characters:
        bot.reply_to(message, "❌ Non hai personaggi disponibili al tuo livello!")
        return
    
    character = characters[0]
    
    # Format character card
    card_msg = char_service.format_character_card(character, show_price=False, is_equipped=(character['id'] == utente.livello_selezionato))
    
    # Create navigation buttons
    markup = types.InlineKeyboardMarkup()
    nav_row = []
    if current_page > 0:
        nav_row.append(types.InlineKeyboardButton("◀️ Prec", callback_data=f"char_page|{current_page - 1}"))
    nav_row.append(types.InlineKeyboardButton(f"{current_page + 1}/{total_pages}", callback_data="char_page_info"))
    if current_page < total_pages - 1:
        nav_row.append(types.InlineKeyboardButton("Succ ▶️", callback_data=f"char_page|{current_page + 1}"))
    markup.row(*nav_row)
    
    # Equip button
    if character['id'] != utente.livello_selezionato:
        markup.add(types.InlineKeyboardButton("✅ Equipaggia", callback_data=f"char_equip|{character['id']}"))
    
    bot.reply_to(message, card_msg, reply_markup=markup, parse_mode='markdown')
