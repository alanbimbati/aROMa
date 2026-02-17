from telebot import types
from settings import *
from services.market_service import MarketService
from services.item_service import ItemService
from utils.markup_utils import safe_answer_callback, safe_edit_message, get_mention_markdown

def handle_market_cmd(bot, message):
    """Show market menu"""
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("📜 Mostra Annunci", callback_data="market_list|1"))
    markup.add(types.InlineKeyboardButton("➕ Vendi Oggetto", callback_data="market_sell_menu"))
    
    bot.send_message(message.chat.id, "🏪 **MERCATO GLOBALE**\n\nBenvenuto nel mercato globale dei giocatori!\nQui puoi vendere i tuoi oggetti o acquistare quelli degli altri.", reply_markup=markup, parse_mode='markdown')

def handle_market_callbacks(bot, call):
    """Handle market callbacks"""
    action = call.data
    user_id = call.from_user.id
    
    market_service = MarketService()
    
    if action.startswith("market_list|"):
        try:
            page_str = action.split("|")[1]
            page = int(page_str)
        except (IndexError, ValueError):
            page = 1
            
        limit = 5
        listings, total = market_service.get_active_listings(page, limit)
        
        msg = f"🏪 **MERCATO GLOBALE (Pagina {page})**\n\n"
        
        if not listings:
            msg += "⚠️ Nessun annuncio attivo al momento."
        
        # Listings are usually objects from SQLAlchemy query, need to verify
        # Assuming listings is a list of objects or dicts. 
        # Code needs adaptation if they are objects.
        # Based on diff: listings, total = market_service.get_active_listings(page, limit)
        # Assuming get_active_listings returns objects with attributes.
        
        import math
        total_pages = math.ceil(total / limit)
        
        markup = types.InlineKeyboardMarkup()
        
        # Add listings buttons directly? 
        if listings:
            for item in listings:
                # item is likely an object from DB model (MarketListing)
                # Attributes: id, item_name, quantity, price, seller_id, seller_name (if joined)
                # Let's assume attributes exist.
                try:
                    i_name = item.item_name
                    qty = item.quantity
                    price = item.price
                    s_id = item.seller_id
                    list_id = item.id
                    # Seller name might be tricky if not joined.
                except AttributeError:
                    # Fallback to dict access if dict
                    i_name = item['item_name']
                    qty = item['quantity']
                    price = item['price']
                    s_id = item['seller_id']
                    list_id = item['id']

                btn_text = f"{i_name} x{qty} ({price}W)"
                if s_id == user_id:
                    btn_text = f"❌ {btn_text}"
                    cb = f"cancel_listing|{list_id}"
                else:
                    btn_text = f"🛒 {btn_text}"
                    cb = f"buy_item|{list_id}"
                    
                markup.add(types.InlineKeyboardButton(btn_text, callback_data=cb))
                
        nav_row = []
        if page > 1:
            nav_row.append(types.InlineKeyboardButton("⬅️ Prec", callback_data=f"market_list|{page-1}"))
        if page < total_pages:
            nav_row.append(types.InlineKeyboardButton("Succ ➡️", callback_data=f"market_list|{page+1}"))
        
        if nav_row:
            markup.row(*nav_row)

        markup.add(types.InlineKeyboardButton("🔙 Menu Mercato", callback_data="market_menu"))
        
        safe_edit_message(bot, msg, call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode='markdown')
        safe_answer_callback(bot, call.id)
        return True
    
    elif action == "market_menu":
         markup = types.InlineKeyboardMarkup()
         markup.add(types.InlineKeyboardButton("📜 Mostra Annunci", callback_data="market_list|1"))
         markup.add(types.InlineKeyboardButton("➕ Vendi Oggetto", callback_data="market_sell_menu"))
         msg = "🏪 **MERCATO GLOBALE**"
         safe_edit_message(bot, msg, call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode='markdown')
         safe_answer_callback(bot, call.id)
         return True

    elif action.startswith("buy_item|"):
        try:
            listing_id = int(action.split("|")[1])
            success, result_msg = market_service.buy_item(user_id, listing_id)
            
            if success:
                safe_answer_callback(bot, call.id, "Acquisto effettuato!")
                bot.send_message(call.message.chat.id, result_msg)
            else:
                safe_answer_callback(bot, call.id, "Errore!")
                bot.send_message(call.message.chat.id, f"❌ {result_msg}")
        except Exception as e:
            print(f"Error buying item: {e}")
            safe_answer_callback(bot, call.id, "Errore server.")
        return True

    elif action.startswith("cancel_listing|"):
        try:
            listing_id = int(action.split("|")[1])
            success, result_msg = market_service.cancel_listing(user_id, listing_id)
            
            if success:
                safe_answer_callback(bot, call.id, "Annuncio ritirato!")
                bot.send_message(call.message.chat.id, result_msg)
            else:
                safe_answer_callback(bot, call.id, "Errore!")
                bot.send_message(call.message.chat.id, f"❌ {result_msg}")
        except Exception as e:
            print(f"Error cancelling listing: {e}")
            safe_answer_callback(bot, call.id, "Errore durante la cancellazione.")
        return True

    elif action == "market_sell_menu":
         item_svc = ItemService()
         inventory = item_svc.get_inventory(user_id)
         
         msg = "📦 **VENDITA OGGETTO**\nScegli cosa vendere dal tuo inventario:"
         markup = types.InlineKeyboardMarkup()
         
         if not inventory:
             msg += "\n🚫 Il tuo inventario è vuoto."
         else:
             count = 0
             for item in inventory:
                 if count >= 30: break # Limit
                 
                 # Inventory items are usually objects
                 try:
                     obj = item.oggetto
                     qty = item.quantita
                 except: 
                     obj = item['oggetto']
                     qty = item['quantita']
                     
                 emoji = "🔹"
                 if "Pozione" in obj or "Elisir" in obj:
                     emoji = "🧪"
                 
                 btn_text = f"{emoji} {obj} (x{qty})"
                 markup.add(types.InlineKeyboardButton(btn_text, callback_data=f"market_sell_select|{obj}"))
                 count += 1
         
         markup.add(types.InlineKeyboardButton("🔙 Menu Mercato", callback_data="market_menu"))
         
         safe_edit_message(bot, msg, call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode='markdown')
         safe_answer_callback(bot, call.id)
         return True

    elif action.startswith("market_sell_select|"):
         item_name = action.split("|")[1]
         msg = bot.send_message(call.message.chat.id, f"💰 Hai scelto di vendere **{item_name}**.\n\nQuanti ne vuoi vendere? (Scrivi un numero, es: 1)", parse_mode='markdown')
         
         bot.register_next_step_handler(msg, process_market_sell_quantity, bot, item_name)
         safe_answer_callback(bot, call.id)
         return True
         
    return False

def process_market_sell_quantity(message, bot, item_name):
    """Step 1: Quantity"""
    try:
        qty = int(message.text)
        if qty <= 0:
            bot.reply_to(message, "❌ Quantità non valida.")
            return
            
        msg = bot.reply_to(message, f"💰 Prezzo totale per {qty}x {item_name}?\n(Inserisci il prezzo TOTALE in Wumpa, es: 100)")
        bot.register_next_step_handler(msg, process_market_sell_price, bot, item_name, qty)
    except ValueError:
         bot.reply_to(message, "❌ Inserisci un numero valido.")

def process_market_sell_price(message, bot, item_name, qty):
    """Step 2: Price and Confirm"""
    try:
        price_total = int(message.text)
        if price_total < 1:
            bot.reply_to(message, "❌ Prezzo non valido.")
            return

        ms = MarketService()
        user_id = message.from_user.id
        
        success, res_msg = ms.create_listing(user_id, item_name, qty, price_total)
        
        if success:
            bot.reply_to(message, f"✅ Annuncio creato!\n📦 **{item_name}** x{qty}\n💰 {price_total} Wumpa")
        else:
            bot.reply_to(message, f"❌ Errore: {res_msg}")
            
    except ValueError:
        bot.reply_to(message, "❌ Prezzo non valido.")
