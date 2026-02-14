
import json
from services.status_effects import StatusEffect
from services.combat_service import CombatService
from types import SimpleNamespace

def test_jiren_effect_logic():
    print("Testing Jiren Effect (buff_attack) Logic...")
    
    # Mock attacker with Jiren's stats
    attacker = SimpleNamespace(
        id_telegram=123,
        nome="Jiren",
        damage_total=100,
        crit_chance=25,
        crit_multiplier=2.0,
        active_status_effects='[]',
        livello_selezionato=151
    )
    
    # Mock defender
    defender = SimpleNamespace(
        name="Mock Mob",
        defense_total=0,
        elemental_type="Normal"
    )
    
    cs = CombatService()
    
    # 1. Base Damage (No Buff)
    dmg1 = cs.calculate_damage(attacker, defender)
    print(f"Base Damage: {dmg1['damage']}")
    
    # 2. Apply Buff
    StatusEffect.apply_status(attacker, 'buff_attack')
    print(f"Status Effects after application: {attacker.active_status_effects}")
    
    # 3. Damage with Buff
    dmg2 = cs.calculate_damage(attacker, defender)
    print(f"Damage with Buff: {dmg2['damage']}")
    
    expected_dmg = int(dmg1['damage'] * 1.2)
    if dmg2['damage'] == expected_dmg:
        print("✅ Jiren's buff_attack (+20%) logic verified!")
    else:
        print(f"❌ Damage mismatch! Expected {expected_dmg}, got {dmg2['damage']}")

if __name__ == "__main__":
    test_jiren_effect_logic()
