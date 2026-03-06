
from services.user_service import UserService
from telebot import types

class StatBuildService:
    def __init__(self):
        self.user_service = UserService()
        # In-memory storage for temporary edits: {user_id: {stat: value, ...}}
        self._temp_edits = {} 

    def start_editing(self, user_id):
        """Initialize editing session with current stats"""
        user = self.user_service.get_user(user_id)
        if not user:
            return None
            
        current_stats = {
            'health': user.allocated_health or 0,
            'mana': user.allocated_mana or 0,
            'damage': user.allocated_damage or 0,
            'resistance': user.allocated_resistance or 0,
            'crit': user.allocated_crit or 0,
            'speed': user.allocated_speed or 0,
            'spent_points': (user.allocated_health or 0) + (user.allocated_mana or 0) + 
                            (user.allocated_damage or 0) + (user.allocated_resistance or 0) + 
                            (user.allocated_crit or 0) + (user.allocated_speed or 0),
            'total_points': user.stat_points + ((user.allocated_health or 0) + (user.allocated_mana or 0) + 
                            (user.allocated_damage or 0) + (user.allocated_resistance or 0) + 
                            (user.allocated_crit or 0) + (user.allocated_speed or 0))
        }
        
        self._temp_edits[user_id] = current_stats
        return current_stats

    def get_temp_stats(self, user_id):
        """Get current temp stats or initialize if missing"""
        if user_id not in self._temp_edits:
            return self.start_editing(user_id)
        return self._temp_edits[user_id]

    def update_temp_stat(self, user_id, stat, change):
        """Update a stat temporarily (+1 or -1)"""
        stats = self.get_temp_stats(user_id)
        if not stats:
            return False, "Utente non trovato"
            
        current_val = stats.get(stat, 0)
        new_val = current_val + change
        
        if new_val < 0:
            return False, "Non puoi scendere sotto 0."
            
        # Calculate used points
        used = 0
        for s in ['health', 'mana', 'damage', 'resistance', 'crit', 'speed']:
            if s == stat:
                used += new_val
            else:
                used += stats.get(s, 0)
                
        if used > stats['total_points']:
            return False, "Punti insufficienti!"
            
        # Specific Limits (e.g. Resistance 75%)
        # Logic: Base resistance is 0. Each point is 1%.
        # We need to know base resistance from items/buffs? 
        # Typically resistance cap is global. 
        # For now, let's assume raw allocation limit if needed, 
        # but the cap is usually on the final value.
        # Let's trust the user or check cap during apply.
        if stat == 'resistance' and new_val > 75:
             return False, "Limite resistenza raggiunto (75%)"
        if stat == 'crit' and new_val > 100:
             return False, "Limite critico raggiunto (100%)"

        # Apply
        stats[stat] = new_val
        stats['spent_points'] = used
        return True, "OK"

    def set_temp_stat(self, user_id, stat, value):
        """Set a stat to an absolute value in the temporary editor."""
        stats = self.get_temp_stats(user_id)
        if not stats:
            return False, "Utente non trovato"
        if stat not in ['health', 'mana', 'damage', 'resistance', 'crit', 'speed']:
            return False, "Stat non valida."
        if value < 0:
            return False, "Non puoi scendere sotto 0."

        if stat == 'resistance' and value > 75:
            return False, "Limite resistenza raggiunto (75%)"
        if stat == 'crit' and value > 100:
            return False, "Limite critico raggiunto (100%)"

        used = 0
        for s in ['health', 'mana', 'damage', 'resistance', 'crit', 'speed']:
            used += value if s == stat else stats.get(s, 0)

        if used > stats['total_points']:
            return False, "Punti insufficienti!"

        stats[stat] = value
        stats['spent_points'] = used
        return True, "OK"

    def max_temp_stat(self, user_id, stat):
        """Assign all currently available points to one stat (respecting caps)."""
        stats = self.get_temp_stats(user_id)
        if not stats:
            return False, "Utente non trovato"
        if stat not in ['health', 'mana', 'damage', 'resistance', 'crit', 'speed']:
            return False, "Stat non valida."

        others_used = 0
        for s in ['health', 'mana', 'damage', 'resistance', 'crit', 'speed']:
            if s != stat:
                others_used += stats.get(s, 0)

        max_by_points = max(0, stats['total_points'] - others_used)
        if stat == 'resistance':
            target_value = min(75, max_by_points)
        elif stat == 'crit':
            target_value = min(100, max_by_points)
        else:
            target_value = max_by_points

        return self.set_temp_stat(user_id, stat, target_value)

    def get_presets(self):
        """Return available presets definition"""
        return {
            'Ladro': {'desc': '🗡️ Ladro (Danno/Vel)', 'ratios': {'damage': 0.4, 'speed': 0.4, 'crit': 0.2}},
            'Tank': {'desc': '🛡️ Tank (Vita/Res)', 'ratios': {'health': 0.5, 'resistance': 0.3, 'mana': 0.2}},
            'Paladino': {'desc': '⚔️ Paladino (Danno/Res)', 'ratios': {'damage': 0.5, 'resistance': 0.5}},
            'Stregone': {'desc': '🔮 Stregone (Mana/Danno)', 'ratios': {'mana': 0.5, 'damage': 0.5}},
            'Mago': {'desc': '⚡ Mago (Mana/Vel)', 'ratios': {'mana': 0.5, 'speed': 0.5}},
            'Arcimago': {'desc': '🧙 Arcimago (Mana/Crit)', 'ratios': {'mana': 0.5, 'crit': 0.5}},
            'Bilanciato': {'desc': '⚖️ Bilanciato', 'ratios': {'health': 0.2, 'mana': 0.2, 'damage': 0.2, 'resistance': 0.2, 'speed': 0.2}},
        }

    def apply_preset(self, user_id, preset_name):
        """Apply a preset to the temporary stats"""
        stats = self.get_temp_stats(user_id)
        presets = self.get_presets()
        
        if preset_name not in presets:
            return False, "Preset non trovato."
            
        ratio = presets[preset_name]['ratios']
        total_p = stats['total_points']
        
        # Reset all
        for s in ['health', 'mana', 'damage', 'resistance', 'crit', 'speed']:
            stats[s] = 0
            
        # Distribute
        used = 0
        remaining = total_p
        
        sorted_keys = sorted(ratio.keys(), key=lambda k: ratio[k], reverse=True)
        
        for key in sorted_keys:
            r = ratio[key]
            points = int(total_p * r)
            
            # Cap check helper
            if key == 'resistance' and points > 75:
                points = 75
            if key == 'crit' and points > 100:
                points = 100
                
            if points > remaining:
                points = remaining
                
            stats[key] = points
            used += points
            remaining -= points
            
        # If points remain (rounding), dump into primary stat 
        if remaining > 0:
            primary = sorted_keys[0]
            # Check res cap again
            if primary == 'resistance':
                space = 75 - stats['resistance']
                to_add = min(remaining, space)
                stats['resistance'] += to_add
                remaining -= to_add
                # If still remaining, dump to second best or just health/damage
                if remaining > 0:
                    fallback = 'damage' if 'damage' in ratio else 'health'
                    stats[fallback] = stats.get(fallback, 0) + remaining
            elif primary == 'crit':
                space = 100 - stats['crit']
                to_add = min(remaining, space)
                stats['crit'] += to_add
                remaining -= to_add
                if remaining > 0:
                    fallback = 'damage' if 'damage' in ratio else 'health'
                    stats[fallback] = stats.get(fallback, 0) + remaining
            else:
                 stats[primary] += remaining
                 used += remaining

        stats['spent_points'] = stats['total_points'] # Should be full now
        return True, f"Preset {preset_name} applicato!"

    def save_changes(self, user_id):
        """Commit changes to DB"""
        if user_id not in self._temp_edits:
            return False, "Nessuna modifica pendente."
            
        stats = self._temp_edits[user_id]
        
        # Calculate remaining free points
        free_points = stats['total_points'] - stats['spent_points']
        
        updates = {
            'allocated_health': stats['health'],
            'allocated_mana': stats['mana'],
            'allocated_damage': stats['damage'],
            'allocated_resistance': stats['resistance'],
            'allocated_crit': stats['crit'],
            'allocated_speed': stats['speed'],
            'stat_points': free_points
        }
        
        self.user_service.update_user(user_id, updates)
        # Recalculate derived stats
        self.user_service.recalculate_stats(user_id)
        
        # Clear temp
        del self._temp_edits[user_id]
        return True, "Statistiche salvate con successo!"

    def reset_temp(self, user_id):
        """Reset all allocated points in temp to 0"""
        stats = self.get_temp_stats(user_id)
        for s in ['health', 'mana', 'damage', 'resistance', 'crit', 'speed']:
            stats[s] = 0
        stats['spent_points'] = 0
        return True, "Statistiche resettate!"

def get_stat_editor_ui(stats):
    """Generate the UI for stat editing"""
    spent = stats.get('spent_points', 0)
    total = stats.get('total_points', 0)
    # Remaining points logic might need adjustment if total includes allocated
    # In start_editing: total_points = free + allocated. 
    # spent_points = sum(allocated).
    # So remaining = total - spent. Correct.
    remaining = total - spent
    
    msg = f"📊 **EDITOR STATISTICHE**\n\n"
    msg += f"Punti totali: {total}\n"
    msg += f"Utilizzati: {spent}\n"
    msg += f"Rimanenti: **{remaining}**\n\n"
    
    markup = types.InlineKeyboardMarkup()
    
    def row(key, label):
        val = stats.get(key, 0)
        markup.row(
            types.InlineKeyboardButton(f"➖", callback_data=f"stat_change|{key}|-1"),
            types.InlineKeyboardButton(f"➖10", callback_data=f"stat_change|{key}|-10"),
            types.InlineKeyboardButton(f"{label}: {val}", callback_data="ignore"),
            types.InlineKeyboardButton(f"➕10", callback_data=f"stat_change|{key}|10"),
            types.InlineKeyboardButton(f"➕", callback_data=f"stat_change|{key}|1")
        )

    # Order: Health, Mana, Damage, Defense(Res?), Speed, Crit
    # In service keys are: 'health', 'mana', 'damage', 'resistance', 'crit', 'speed'
    row('health', '❤️ HP')
    row('mana', '💙 MP')
    row('damage', '⚔️ ATK')
    row('resistance', '🛡️ RES')
    row('speed', '⚡ SPD')
    row('crit', '🔮 CRT')
    
    markup.add(types.InlineKeyboardButton("💾 SALVA MODIFICHE", callback_data="stat_save"))
    markup.add(types.InlineKeyboardButton("🔄 RESETTA", callback_data="stat_reset"))
    
    presets_row1 = [
        types.InlineKeyboardButton("🗡️ Ladro", callback_data="stat_preset|Ladro"),
        types.InlineKeyboardButton("🛡️ Tank", callback_data="stat_preset|Tank"),
        types.InlineKeyboardButton("⚔️ Paladino", callback_data="stat_preset|Paladino")
    ]
    presets_row2 = [
        types.InlineKeyboardButton("🔮 Stregone", callback_data="stat_preset|Stregone"),
        types.InlineKeyboardButton("⚡ Mago", callback_data="stat_preset|Mago"),
        types.InlineKeyboardButton("🧙 Arcimago", callback_data="stat_preset|Arcimago")
    ]
    markup.row(*presets_row1)
    markup.row(*presets_row2)
    
    markup.add(types.InlineKeyboardButton("🔙 Menu Profilo", callback_data="back_to_profile"))
    
    return msg, markup
