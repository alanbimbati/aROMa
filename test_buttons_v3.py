from telebot import types
import json

# Refined monkey patch for pyTelegramBotAPI
_original_inline_init = types.InlineKeyboardButton.__init__
def _patched_inline_init(self, *args, **kwargs):
    self.style = kwargs.pop('style', None)
    _original_inline_init(self, *args, **kwargs)
types.InlineKeyboardButton.__init__ = _patched_inline_init

_original_inline_to_dict = types.InlineKeyboardButton.to_dict
def _patched_inline_to_dict(self):
    res = _original_inline_to_dict(self)
    if hasattr(self, 'style') and self.style:
        res['style'] = self.style
    return res
types.InlineKeyboardButton.to_dict = _patched_inline_to_dict

btn = types.InlineKeyboardButton(text="Success", callback_data="test", style="success")
print(f"Has style: {hasattr(btn, 'style')}")
print(f"Style value: {getattr(btn, 'style', 'None')}")
print(f"Patched Dict: {json.dumps(btn.to_dict(), indent=2)}")
