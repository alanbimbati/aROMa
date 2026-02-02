
import threading
import time

class TrapService:
    def __init__(self):
        # {chat_id: {'state': 'armed'|'volatile', 'placer_id': int, 'timer': Timer}}
        self._active_traps = {}

    def arm_trap(self, chat_id, placer_id, duration=3.0, on_timeout=None, trap_type='TNT'):
        """Arm a trap for the given chat."""
        if chat_id in self._active_traps:
            self.cancel_trap(chat_id)
            
        # Create timer
        t = threading.Timer(duration, lambda: self._handle_timeout(chat_id, on_timeout))
        t.start()
        
        self._active_traps[chat_id] = {
            'state': 'armed',
            'placer_id': placer_id,
            'timer': t,
            'trap_type': trap_type
        }
        return True
    
    def cancel_trap(self, chat_id):
        """Cancel any active trap without triggering."""
        if chat_id in self._active_traps:
            trap = self._active_traps[chat_id]
            try:
                trap['timer'].cancel()
            except:
                pass
            del self._active_traps[chat_id]
            return True
        return False

    def _handle_timeout(self, chat_id, callback):
        """Internal callback for timer."""
        # Only proceed if trap is still known (might have been defused mostly concurrently)
        if chat_id in self._active_traps:
            # Check if it was already cancelled? (threading race)
            # But we are in the timer thread.
            trap = self._active_traps[chat_id]
            trap['state'] = 'volatile'
            
            if callback:
                try:
                    callback(chat_id)
                except Exception as e:
                    print(f"[ERROR] Trap timeout callback failed: {e}")

    def defuse_trap(self, chat_id, user_id):
        """Attempt to defuse the trap. Returns (success, message_code)."""
        if chat_id in self._active_traps:
            trap = self._active_traps[chat_id]
            if trap['state'] == 'armed':
                # Success
                try: trap['timer'].cancel()
                except: pass
                del self._active_traps[chat_id]
                return True, "defused"
            else:
                # Volatile - too late
                return False, "volatile"
        return False, "no_trap"
        
    def has_volatile_trap(self, chat_id):
        """Check if a volatile trap exists (peek)."""
        if chat_id in self._active_traps:
            return self._active_traps[chat_id]['state'] == 'volatile'
        return False

    def trigger_trap(self, chat_id, user_id):
        """Trigger the trap and return its data. Returns None if no volatile trap."""
        if chat_id in self._active_traps:
            trap = self._active_traps[chat_id]
            if trap['state'] == 'volatile':
                del self._active_traps[chat_id]
                return trap
        return None
        
    # Validation helpers
    def is_trap_active(self, chat_id):
        return chat_id in self._active_traps
