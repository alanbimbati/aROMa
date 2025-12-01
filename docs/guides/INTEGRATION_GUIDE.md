# INTEGRATION GUIDE FOR NEW CHARACTER SYSTEM
# Instructions for integrating the new handlers into main.py

## STEP 1: Add new command mappings to BotCommands.__init__

In the comandi_privati dictionary, add:
```python
"👤 Profilo": self.handle_profile,
```

In the comandi_generici dictionary, add  
```python
"/profile": self.handle_profile,
"!profile": self.handle_profile,
```

## STEP 2: Replace handle_choose_character method

Replace the existing handle_choose_character method (around line 554) with the new paginated version from new_handlers.py (handle_choose_character_new, renamed to handle_choose_character)

## STEP 3: Add new methods to BotCommands class

Add these new methods to the BotCommands class:
- handle_profile() - from new_handlers.py
- (Note: handle_choose_character is REPLACED, not added)

## STEP 4: Extend handle_inline_buttons function

In the handle_inline_buttons function (around line 662), add these new callback handlers BEFORE the existing handlers:

```python
@bot.callback_query_handler(func=lambda call: True)
def handle_inline_buttons(call):
    action = call.data
    user_id = call.from_user.id
    utente = user_service.get_user(user_id)
    
    # NEW HANDLERS - Add at the top
    if action.startswith("char_page|"):
        handle_char_page_callback(call, user_id, utente)
        return
    
    elif action == "char_already_equipped":
        bot.answer_callback_query(call.id, "⭐ Questo personaggio è già equipaggiato!")
        return
    
    elif action == "char_page_info":
        bot.answer_callback_query(call.id, "Usa le frecce per navigare")
        return
    
    elif action.startswith("char_select|"):
        handle_char_select_callback(call, user_id, utente)
        return
    
    elif action == "stats_menu":
        handle_stats_menu_callback(call, user_id, utente)
        return
    
    elif action.startswith("stat_alloc|"):
        handle_stat_alloc_callback(call, user_id, utente)
        return
    
    elif action.startswith("reset_stats"):
        handle_reset_stats_callback(call, user_id, utente)
        return
    
    elif action == "transform_menu":
        handle_transform_menu_callback(call, user_id, utente)
        return
    
    elif action == "transform_locked":
        bot.answer_callback_query(call.id, "🔒 Non puoi attivare questa trasformazione!")
        return
    
    elif action.startswith("transform|"):
        handle_transform_activate_callback(call, user_id, utente)
        return
    
    # EXISTING HANDLERS BELOW
    if action.startswith("use|"):
        ...
```

## STEP 5: Add callback handler functions (GLOBAL SCOPE)

Add these callback handler functions as GLOBAL functions (like process_character_selection), NOT inside BotCommands class:

From new_handlers.py:
- handle_char_page_callback
- handle_char_select_callback
- handle_stats_menu_callback
- handle_stat_alloc_callback
- handle_reset_stats_callback
- handle_transform_menu_callback
- handle_transform_activate_callback

## STEP 6: Update get_start_markup

In get_start_markup function, add the profile button:
```python
markup.add('ℹ️ info', '👤 Profilo', '🎮 Nome in Game')
```

## QUICK INTEGRATION SCRIPT (to be manually applied):

Due to the size of main.py, a complete rewrite would be risky. Instead:

1. Back up current main.py
2. Apply changes following the steps above
3. Test each component individually
4. Verify all imports are working

The new_handlers.py file contains all the necessary handler code ready to be integrated.
