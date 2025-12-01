"""
New handlers for character system V3
To be integrated into main.py BotCommands class
"""

# These methods should be added to the BotCommands class in main.py

def handle_profile(self):
    """Show comprehensive user profile with stats and transformations"""
    utente = user_service.get_user(self.chatid)
    
    # Check for expired transformations
    transformation_service.check_transformation_expired(utente)
    
    # Get current stats with transformation bonuses
    stats = transformation_service.get_current_stats_with_transformation(utente)
    
    msg = f"👤 **PROFILO DI {utente.username or utente.nome}**\\n\\n"
    msg += f"⭐ Livello: {utente.livello}\\n"
    msg += f"✨ EXP: {utente.exp}\\n"
    msg += f"🍑 {PointsName}: {utente.points}\\n\\n"
    
    # Character info
    session = user_service.db.get_session()
    from models.system import Livello
    character = session.query(Livello).filter_by(id=utente.livello_selezionato).first()
    session.close()
    
    if character:
        msg += f"🎮 **Personaggio Equipaggiato:**\\n"
        msg += f"└ {character.nome}"
        if character.character_group:
            msg += f" ({character.character_group})"
        msg += "\\n\\n"
    
    # Stats with breakdown
    msg += f"📊 **STATISTICHE**\\n\\n"
    msg += f"❤️ Vita: {stats['total']['max_health']} HP\\n"
    msg += f"  └ Base: {stats['base']['health']} | Allocata: +{stats['allocated']['health']}"
    if stats['transformation']['active']:
        msg += f" | Trasf: +{stats['transformation']['health']}"
    msg += "\\n\\n"
    
    msg += f"💙 Mana: {stats['total']['max_mana']}\\n"
    msg += f"  └ Base: {stats['base']['mana']} | Allocato: +{stats['allocated']['mana']}"
    if stats['transformation']['active']:
        msg += f" | Trasf: +{stats['transformation']['mana']}"
    msg += "\\n\\n"
    
    msg += f"⚔️ Danno: {stats['total']['damage']}\\n"
    msg += f"  └ Base: {stats['base']['damage']} | Allocato: +{stats['allocated']['damage']}"
    if stats['transformation']['active']:
        msg += f" | Trasf: +{stats['transformation']['damage']}"
    msg += "\\n\\n"
    
    # Stat points
    points_info = stats_service.get_available_stat_points(utente)
    msg += f"🎯 Punti Stat Disponibili: {points_info['available']}/{points_info['total']}\\n\\n"
    
    # Active transformation
    active_trans = transformation_service.get_active_transformation(utente)
    if active_trans:
        time_left = active_trans['expires_at'] - datetime.datetime.now()
        hours_left = int(time_left.total_seconds() / 3600)
        msg += f"✨ **TRASFORMAZIONE ATTIVA:**\\n"
        msg += f"└ {active_trans['name']}\\n"
        msg += f"└ Scade tra: {hours_left}h\\n\\n"
    
    # Inline buttons
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("📊 Alloca Statistiche", callback_data="stats_menu"))
    markup.add(types.InlineKeyboardButton("🔄 Reset Stats (100 🍑)", callback_data="reset_stats_confirm"))
    if character:
        markup.add(types.InlineKeyboardButton("✨ Trasformazioni", callback_data="transform_menu"))
    
    self.bot.reply_to(self.message, msg, reply_markup=markup, parse_mode='markdown')

def handle_choose_character_new(self):
    """New character selection with pagination"""
    utente = user_service.get_user(self.chatid)
    if not utente:
        return
    
    # Show first page
    page_chars, total_pages, current_page = character_service.get_characters_paginated(utente, page=0)
    
    if not page_chars:
        self.bot.reply_to(self.message, "Non hai personaggi disponibili!")
        return
    
    char = page_chars[0]
    is_equipped = (utente.livello_selezionato == char.id)
    
    # Format character card
    msg = character_service.format_character_card(char, is_equipped=is_equipped)
    msg += f"\\n\\n📄 Personaggio {current_page + 1} di {total_pages}"
    
    # Navigation buttons
    markup = types.InlineKeyboardMarkup()
    
    nav_row = []
    if total_pages > 1:
        nav_row.append(types.InlineKeyboardButton("◀️", callback_data=f"char_page|{max(0, current_page - 1)}"))
    nav_row.append(types.InlineKeyboardButton(f"{current_page + 1}/{total_pages}", callback_data="char_page_info"))
    if total_pages > 1:
        nav_row.append(types.InlineKeyboardButton("▶️", callback_data=f"char_page|{min(total_pages - 1, current_page + 1)}"))
    
    markup.row(*nav_row)
    
    # Select button
    if not is_equipped:
        markup.add(types.InlineKeyboardButton("✅ Equipaggia questo personaggio", callback_data=f"char_select|{char.id}"))
    else:
        markup.add(types.InlineKeyboardButton("⭐ Già Equipaggiato", callback_data="char_already_equipped"))
    
    # Try to send with image
    image_sent = False
    session = user_service.db.get_session()
    from models.system import Livello
    char_obj = session.query(Livello).filter_by(id=char.id).first()
    session.close()
    
    if char_obj and char_obj.telegram_file_id:
        try:
            self.bot.send_photo(self.chatid, char_obj.telegram_file_id, caption=msg, reply_markup=markup, parse_mode='markdown')
            image_sent = True
        except:
            pass
    
    if not image_sent:
        self.bot.reply_to(self.message, msg, reply_markup=markup, parse_mode='markdown')


# Callback handlers to add to handle_inline_buttons function:

def handle_char_page_callback(call, user_id, utente):
    """Handle character page navigation"""
    page = int(call.data.split("|")[1])
    
    page_chars, total_pages, current_page = character_service.get_characters_paginated(utente, page=page)
    
    if not page_chars:
        bot.answer_callback_query(call.id, "Nessun personaggio!")
        return
    
    char = page_chars[0]
    is_equipped = (utente.livello_selezionato == char.id)
    
    msg = character_service.format_character_card(char, is_equipped=is_equipped)
    msg += f"\\n\\n📄 Personaggio {current_page + 1} di {total_pages}"
    
    # Navigation buttons
    markup = types.InlineKeyboardMarkup()
    
    nav_row = []
    if total_pages > 1:
        nav_row.append(types.InlineKeyboardButton("◀️", callback_data=f"char_page|{max(0, current_page - 1)}"))
    nav_row.append(types.InlineKeyboardButton(f"{current_page + 1}/{total_pages}", callback_data="char_page_info"))
    if total_pages > 1:
        nav_row.append(types.InlineKeyboardButton("▶️", callback_data=f"char_page|{min(total_pages - 1, current_page + 1)}"))
    
    markup.row(*nav_row)
    
    if not is_equipped:
        markup.add(types.InlineKeyboardButton("✅ Equipaggia questo personaggio", callback_data=f"char_select|{char.id}"))
    else:
        markup.add(types.InlineKeyboardButton("⭐ Già Equipaggiato", callback_data="char_already_equipped"))
    
   # Update message
    bot.edit_message_text(msg, user_id, call.message.message_id, reply_markup=markup, parse_mode='markdown')
    bot.answer_callback_query(call.id)

def handle_char_select_callback(call, user_id, utente):
    """Handle character selection"""
    char_id = int(call.data.split("|")[1])
    
    success, msg = character_service.equip_character(utente, char_id)
    
    if success:
        bot.answer_callback_query(call.id, "✅ Personaggio equipaggiato!")
        bot.send_message(user_id, f"✅ {msg}", reply_markup=get_start_markup(user_id))
    else:
        bot.answer_callback_query(call.id, f"❌ {msg}")

def handle_stats_menu_callback(call, user_id, utente):
    """Show stat allocation menu"""
    points_info = stats_service.get_available_stat_points(utente)
    
    msg = f"📊 **ALLOCAZIONE STATISTICHE**\\n\\n"
    msg += f"🎯 Punti Disponibili: {points_info['available']}\\n\\n"
    msg += f"Scegli dove allocare i tuoi punti:"
    
    markup = types.InlineKeyboardMarkup()
    if points_info['available'] > 0:
        markup.add(types.InlineKeyboardButton(f"❤️ +Vita (+{stats_service.HEALTH_PER_POINT} HP max)", callback_data="stat_alloc|health"))
        markup.add(types.InlineKeyboardButton(f"💙 +Mana (+{stats_service.MANA_PER_POINT} mana max)", callback_data="stat_alloc|mana"))
        markup.add(types.InlineKeyboardButton(f"⚔️ +Danno (+{stats_service.DAMAGE_PER_POINT} danno)", callback_data="stat_alloc|damage"))
    else:
        msg += "\\n\\n⚠️ Non hai punti disponibili!"
    
    bot.edit_message_text(msg, user_id, call.message.message_id, reply_markup=markup, parse_mode='markdown')
    bot.answer_callback_query(call.id)

def handle_stat_alloc_callback(call, user_id, utente):
    """Handle stat point allocation"""
    stat_type = call.data.split("|")[1]
    
    success, msg = stats_service.allocate_stat_point(utente, stat_type)
    
    bot.answer_callback_query(call.id, msg if success else f"❌ {msg}")
    
    if success:
        # Refresh stats menu
        utente = user_service.get_user(user_id)  # Refresh user data
        handle_stats_menu_callback(call, user_id, utente)

def handle_reset_stats_callback(call, user_id, utente):
    """Handle stat reset confirmation"""
    if call.data == "reset_stats_confirm":
        msg = f"⚠️ **CONFERMA RESET STATISTICHE**\\n\\n"
        msg += f"Vuoi davvero resettare tutte le statistiche allocate?\\n"
        msg += f"Costo: {stats_service.RESET_COST} {PointsName}\\n\\n"
        msg += f"Tutti i punti allocati verranno restituiti."
        
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("✅ Sì, Reset", callback_data="reset_stats_yes"))
        markup.add(types.InlineKeyboardButton("❌ Annulla", callback_data="reset_stats_no"))
        
        bot.edit_message_text(msg, user_id, call.message.message_id, reply_markup=markup, parse_mode='markdown')
        bot.answer_callback_query(call.id)
    
    elif call.data == "reset_stats_yes":
        success, msg = stats_service.reset_stat_points(utente)
        bot.answer_callback_query(call.id, "✅ Reset completato!" if success else f"❌ {msg}")
        bot.send_message(user_id, msg)
    
    elif call.data == "reset_stats_no":
        bot.answer_callback_query(call.id, "Reset annullato")
        bot.delete_message(user_id, call.message.message_id)

def handle_transform_menu_callback(call, user_id, utente):
    """Show transformation menu"""
    transformations = transformation_service.get_available_transformations(utente)
    active_trans = transformation_service.get_active_transformation(utente)
    
    msg = f"✨ **TRASFORMAZIONI**\\n\\n"
    
    if active_trans:
        time_left = active_trans['expires_at'] - datetime.datetime.now()
        hours_left = int(time_left.total_seconds() / 3600)
        msg += f"🔥 Trasformazione Attiva: {active_trans['name']}\\n"
        msg += f"⏰ Scade tra: {hours_left}h\\n\\n"
    
    if transformations:
        msg += "**Trasformazioni Disponibili:**\\n\\n"
        markup = types.InlineKeyboardMarkup()
        
        for trans in transformations:
            status = "✅" if trans['can_activate'] else "🔒"
            btn_text = f"{status} {trans['name']} ({trans['wumpa_cost']} 🍑)"
            
            if trans['can_activate']:
                markup.add(types.InlineKeyboardButton(btn_text, callback_data=f"transform|{trans['id']}"))
            else:
                markup.add(types.InlineKeyboardButton(btn_text, callback_data="transform_locked"))
        
        bot.edit_message_text(msg, user_id, call.message.message_id, reply_markup=markup, parse_mode='markdown')
    else:
        msg += "Nessuna trasformazione disponibile per questo personaggio."
        bot.edit_message_text(msg, user_id, call.message.message_id, parse_mode='markdown')
    
    bot.answer_callback_query(call.id)

def handle_transform_activate_callback(call, user_id, utente):
    """Activate transformation"""
    trans_id = int(call.data.split("|")[1])
    
    success, msg = transformation_service.activate_transformation(utente, trans_id)
    
    bot.answer_callback_query(call.id, "✨ Trasformazione attivata!" if success else f"❌ Errore")
    bot.send_message(user_id, msg, parse_mode='markdown')
