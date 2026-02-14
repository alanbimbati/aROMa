from telebot import types
import json

btn = types.InlineKeyboardButton(text="Success", callback_data="test", style="success")
print(f"Has style: {hasattr(btn, 'style')}")
print(f"Style value: {getattr(btn, 'style', 'None')}")

# Test monkey patch
_original_inline_to_dict = types.InlineKeyboardButton.to_dict
def _patched_inline_to_dict(self):
    res = _original_inline_to_dict(self)
    if hasattr(self, 'style') and self.style:
        res['style'] = self.style
    return res
types.InlineKeyboardButton.to_dict = _patched_inline_to_dict

print(f"Patched Dict: {json.dumps(btn.to_dict(), indent=2)}")
