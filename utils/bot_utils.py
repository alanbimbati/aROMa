import telebot
from telebot.apihelper import ApiTelegramException

class SafeTeleBot(telebot.TeleBot):
    def __init__(self, token, parse_mode=None, threaded=True, skip_pending=False, num_threads=2, next_step_backend=None, reply_backend=None, exception_handler=None, last_update_id=0, suppress_middleware_excep=False, state_storage=None, use_class_middlewares=False, disable_web_page_preview=None, disable_notification=None, protect_content=None, allow_sending_without_reply=None, strict_kwargs=False):
        super().__init__(token, parse_mode, threaded, skip_pending, num_threads, next_step_backend, reply_backend, exception_handler, last_update_id, suppress_middleware_excep, state_storage, use_class_middlewares, disable_web_page_preview, disable_notification, protect_content, allow_sending_without_reply, strict_kwargs)
        
    def send_message(self, chat_id, text, parse_mode='Markdown', **kwargs):
        """Override to ensure safe markdown or fallback"""
        try:
            return super().send_message(chat_id, text, parse_mode=parse_mode, **kwargs)
        except ApiTelegramException as e:
            if "can't parse entities" in str(e) and parse_mode == 'Markdown':
                # Fallback to plain text if markdown fails
                print(f"[SafeTeleBot] Markdown error: {e}. Falling back to plain text.")
                return super().send_message(chat_id, text, parse_mode=None, **kwargs)
            raise e

    def reply_to(self, message, text, parse_mode='Markdown', **kwargs):
        try:
            return super().reply_to(message, text, parse_mode=parse_mode, **kwargs)
        except ApiTelegramException as e:
            if "can't parse entities" in str(e) and parse_mode == 'Markdown':
                print(f"[SafeTeleBot] Markdown error in reply: {e}. Falling back to plain text.")
                return super().reply_to(message, text, parse_mode=None, **kwargs)
            raise e
            
def escape_markdown(text):
    """Helper to escape markdown special characters"""
    if not text: return ""
    chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
    for c in chars:
        text = text.replace(c, f"\\{c}")
    return text
