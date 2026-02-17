def format_mob_stats(mob, show_full=False):
    """Format mob stats, obscuring sensitive info if not authorized"""
    level = mob.get('level', 1)
    
    if show_full:
        # Full stats (Scouter active)
        hp_text = f"{mob['health']}/{mob['max_health']}"
        mana_text = f"{mob.get('mana', 0)}/{mob.get('max_mana', 0)}"
        speed_text = f"{mob.get('speed', 30)}"
        res_text = f"{mob.get('resistance', 0)}%"
        atk_text = f"{mob['attack']}"
        # CD Details
        cd_total = mob.get('cooldown_total', 0)
        cd_next = mob.get('next_attack_in', 0)
        
        cd_info = f"\n⏱️ CD: {cd_total}s"
        if cd_next > 0:
            cd_info += f" | ⏳ Prossimo: {cd_next}s"
        else:
            cd_info += " | ⚠️ **ATTACCO IMMINENTE!**"
            
        extra = cd_info
        return f"📊 Lv. {level} | ⚡ Vel: {speed_text} | 🛡️ Res: {res_text}\n❤️ Salute: {hp_text} HP\n💙 Mana: {mana_text}\n⚔️ Danno: {atk_text}{extra}"
    else:
        # Obscured stats (Default)
        hp_text = "???"
        res_text = "???"
        atk_text = "???"
        extra = ""
        return f"📊 Lv. {level} | 🛡️ Res: {res_text}\n❤️ Salute: {hp_text} HP\n⚔️ Danno: {atk_text}{extra}"

def get_rarity_emoji(rarity):
    """Get emoji for rarity level (1-5)"""
    rarity = int(rarity) if rarity else 1
    if rarity == 1: return "⚪" # Comune
    if rarity == 2: return "🟢" # Non Comune
    if rarity == 3: return "🔵" # Raro
    if rarity == 4: return "🟣" # Epico
    if rarity == 5: return "🟠" # Leggendario
    return "⚪"
