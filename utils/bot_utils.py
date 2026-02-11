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

    def delete_message(self, chat_id, message_id, timeout=None):
        """Override to handle rate limits and 'message not found' gracefully"""
        import time
        max_retries = 3
        for attempt in range(max_retries):
            try:
                return super().delete_message(chat_id, message_id, timeout=timeout)
            except ApiTelegramException as e:
                err_msg = str(e).lower()
                if "too many requests" in err_msg:
                    if attempt < max_retries - 1:
                        # Extract wait time if possible, else default
                        import re
                        wait_match = re.search(r'retry after (\d+)', err_msg)
                        wait_time = int(wait_match.group(1)) if wait_match else 1
                        print(f"[SafeTeleBot] Rate limited on delete. Waiting {wait_time}s...")
                        time.sleep(wait_time)
                        continue
                elif any(x in err_msg for x in ["message to delete not found", "message can't be deleted", "chat not found"]):
                    # These are expected if message was already deleted or chat is gone
                    return False
                raise e
        return False
            
def escape_markdown(text):
    """Helper to escape markdown characters for Telegram (V1)"""
    if not text:
        return ""
    # Characters to escape for Markdown (V1)
    # _, *, [, `
    return str(text).replace("_", "\\_").replace("*", "\\*").replace("[", "\\[").replace("`", "\\`")

def get_mention_markdown(user_id, name):
    """Create a safe markdown mention that works with underscores and triggers notifications"""
    if not name:
        name = f"User {user_id}"
    
    # Prepend @ if it looks like a username (no spaces) and doesn't have it
    display_name = str(name)
    if display_name and not display_name.startswith('@') and ' ' not in display_name:
        display_name = '@' + display_name
        
    safe_name = escape_markdown(display_name)
    return f"[{safe_name}](tg://user?id={user_id})"
