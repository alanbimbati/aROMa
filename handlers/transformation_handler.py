"""
Transformation Handlers
Extracted from main.py to reduce file size and improve maintainability.
"""
import datetime
from telebot import types
from services.character_loader import get_character_loader
from services.user_service import UserService
from services.transformation_service import TransformationService
from models.system import UserCharacter, CharacterTransformation, UserTransformation
from models.user import Utente

# These helpers are expected to be passed from main.py or imported if possible
# For now, we'll assume they are available or define placeholders if needed
# but better to pass the bot and other globals.

def handle_transformation_callbacks(bot, call, utente, user_service, transformation_service):
    """Dispatcher for transformation-related callbacks"""
    action = call.data
    user_id = call.from_user.id
    
    # Helper for safe editing
    def safe_edit(text, markup=None):
        try:
            bot.edit_message_text(text, user_id, call.message.message_id, reply_markup=markup, parse_mode='markdown')
        except:
            bot.send_message(user_id, text, reply_markup=markup, parse_mode='markdown')

    def safe_answer(text=None, show_alert=False):
        try:
            bot.answer_callback_query(call.id, text=text, show_alert=show_alert)
        except:
            pass

    if action.startswith("transform_menu|"):
        base_char_id = int(action.split("|")[1])
        char_loader = get_character_loader()
        base_char = char_loader.get_character_by_id(base_char_id)
        
        if not base_char:
            safe_answer("❌ Personaggio non trovato!")
            return

        transforms = char_loader.get_transformation_chain(base_char_id)
        session = user_service.db.get_session()
        
        msg = f"🔥 **TRASFORMAZIONI per {base_char['nome']}**\n\n"
        msg += f"💙 Mana attuale: {utente.mana}/{utente.max_mana}\n\n"
        msg += "📋 **Opzioni disponibili:**\n"
        
        markup = types.InlineKeyboardMarkup()
        
        for t in transforms:
            owned = session.query(UserCharacter).filter_by(user_id=user_id, character_id=t['id']).first()
            price = t.get('price', 0)
            mana_cost = t.get('transformation_mana_cost', 50)
            duration = t.get('transformation_duration_days', 0)
            duration_str = f"{duration}g" if duration > 0 else "♾️"
            
            # Time-based restriction (Great Ape)
            is_ape = 'Great Ape' in t['nome'] or 'Scimmione' in t['nome'] or t['id'] == 500
            current_hour = datetime.datetime.now().hour
            is_night = current_hour >= 18 or current_hour < 6
            
            if is_ape and not is_night:
                status_icon = "🌙"
                msg += f"{status_icon} **{t['nome']}** (Solo Notte: 18:00-06:00)\n"
                msg += f"   └ Disponibile al calare del sole\n"
            else:
                status_icon = "✅" if owned else "🔒"
                msg += f"{status_icon} **{t['nome']}**\n"
            msg += f"   ├ Costo Mana: {mana_cost} 💙\n"
            msg += f"   └ Durata: {duration_str}\n"
            
            if not owned and price > 0:
                msg += f"   └ Prezzo: {price} 🍑\n"
                markup.add(types.InlineKeyboardButton(f"🛒 Compra {t['nome']} ({price} 🍑)", callback_data=f"buy_transform|{t['id']}"))
            elif owned:
                if can_afford or (is_ape and not is_night):
                    btn_text = f"🔥 Trasformati in {t['nome']}"
                    if is_ape and not is_night:
                        btn_text = f"🌙 {t['nome']} (Notte)"
                    markup.add(types.InlineKeyboardButton(btn_text, callback_data=f"activate_transform|{t['id']}"))
                else:
                    markup.add(types.InlineKeyboardButton(f"❌ {t['nome']} (No Mana)", callback_data="no_mana"))
            
            msg += "\n"
        
        active_trans = transformation_service.get_active_transformation(utente, session=session)
        if active_trans:
            markup.add(types.InlineKeyboardButton("❌ Annulla Trasformazione", callback_data="revert_transform"))
            
        session.close()
        markup.add(types.InlineKeyboardButton("🔙 Indietro", callback_data="back_to_profile"))
        safe_edit(msg, markup)
        safe_answer()

    elif action.startswith("activate_transform|"):
        trans_id = int(action.split("|")[1])
        char_loader = get_character_loader()
        trans_char = char_loader.get_character_by_id(trans_id)
        
        if not trans_char:
            safe_answer("❌ Trasformazione non trovata!")
            return

        mana_cost = trans_char.get('transformation_mana_cost', 50)
        if utente.mana < mana_cost:
            safe_answer(f"❌ Mana insufficiente! Serve: {mana_cost}, hai: {utente.mana}")
            return
            
        success, msg = transformation_service.activate_transformation(utente, trans_id)
        if success:
            safe_answer("✅ Trasformazione attivata!")
            bot.send_message(user_id, f"{msg}")
        else:
            safe_answer(f"❌ {msg}", show_alert=True)

    elif action == "revert_transform":
        success, msg = transformation_service.revert_transformation(utente)
        if success:
            safe_answer("✅ Trasformazione annullata!")
            bot.send_message(user_id, f"ℹ️ {msg}")
        else:
            safe_answer(f"❌ {msg}", show_alert=True)

    elif action.startswith("buy_transform|"):
        trans_id = int(action.split("|")[1])
        char_loader = get_character_loader()
        character = char_loader.get_character_by_id(trans_id)
        
        if not character:
            safe_answer("❌ Trasformazione non trovata!", show_alert=True)
            return
        
        session = user_service.db.get_session()
        base_char_id = utente.livello_selezionato
        trans_entry = session.query(CharacterTransformation).filter_by(
            base_character_id=base_char_id,
            transformed_character_id=trans_id
        ).first()
        
        if not trans_entry:
            session.close()
            safe_answer("❌ Questa trasformazione non è acquistabile per il tuo personaggio attuale!", show_alert=True)
            return
        
        price = trans_entry.wumpa_cost if trans_entry.wumpa_cost is not None else 0
        
        owned = session.query(UserCharacter).filter_by(user_id=user_id, character_id=trans_id).first()
        if owned:
            session.close()
            safe_answer("✅ Possiedi già questa trasformazione!", show_alert=True)
            return
        
        if utente.points < price:
            session.close()
            safe_answer(f"❌ Non hai abbastanza Wumpa! Serve: {price} 🍑", show_alert=True)
            return
        
        user_service.add_points(utente, -price)
        new_ownership = UserCharacter(
            user_id=user_id,
            character_id=trans_id,
            obtained_at=datetime.datetime.now().date()
        )
        session.add(new_ownership)
        session.commit()
        session.close()
        
        safe_answer(f"✅ {character['nome']} acquistato!")
        bot.send_message(user_id, f"🎉 Hai acquistato **{character['nome']}** per {price} 🍑!", parse_mode='markdown')

    return True # Handled
