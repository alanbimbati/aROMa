from telebot import types
import json

btn = types.InlineKeyboardButton(text="Success", callback_data="test", style="success")
print(f"Button Dict: {json.dumps(btn.to_dict(), indent=2)}")
