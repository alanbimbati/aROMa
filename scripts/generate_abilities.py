import csv
import random

def generate_abilities():
    characters = []
    try:
        with open('data/characters.csv', 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                characters.append(row)
    except FileNotFoundError:
        print("data/characters.csv not found!")
        return

    abilities = []
    ability_id = 1

    # Effect definitions
    effects = [
        {'type': 'stun', 'chance': 15, 'duration': 1, 'desc': 'Stuns enemy'},
        {'type': 'poison', 'chance': 25, 'duration': 3, 'desc': 'Poison damage'},
        {'type': 'burn', 'chance': 25, 'duration': 3, 'desc': 'Burn damage'},
        {'type': 'freeze', 'chance': 20, 'duration': 2, 'desc': 'Freezes enemy'},
        {'type': 'life_drain', 'chance': 100, 'duration': 0, 'desc': 'Drains HP'},
        {'type': 'wumpa_steal', 'chance': 50, 'duration': 0, 'desc': 'Steals Wumpa'},
        {'type': 'buff_attack', 'chance': 100, 'duration': 3, 'desc': 'Increases ATK'},
        {'type': 'buff_defense', 'chance': 100, 'duration': 3, 'desc': 'Increases DEF'},
        {'type': 'crit_boost', 'chance': 100, 'duration': 2, 'desc': 'Boosts Crit'},
        {'type': '', 'chance': 0, 'duration': 0, 'desc': ''} # No effect
    ]

    for char in characters:
        char_id = int(char['id'])
        name = char['nome']
        group = char['character_group']
        element = char['elemental_type']
        
        # Determine skill based on group/element/name
        skill_name = char['special_attack_name'] if char['special_attack_name'] else f"{name} Strike"
        damage = int(char['special_attack_damage']) if char['special_attack_damage'] else 20
        mana = int(char['special_attack_mana_cost']) if char['special_attack_mana_cost'] else 10
        
        # Default stats
        crit_chance = 10
        crit_mult = 1.5
        effect = {'type': '', 'chance': 0, 'duration': 0}

        # Assign effects based on logic
        if 'Pokemon' in group:
            if element == 'Electric':
                effect = {'type': 'stun', 'chance': 20, 'duration': 1}
            elif element == 'Fire':
                effect = {'type': 'burn', 'chance': 30, 'duration': 3}
            elif element == 'Water' or element == 'Ice':
                effect = {'type': 'freeze', 'chance': 15, 'duration': 2}
            elif element == 'Grass' or element == 'Poison':
                effect = {'type': 'poison', 'chance': 40, 'duration': 4}
            elif 'Psychic' in name or 'Mewtwo' in name:
                effect = {'type': 'stun', 'chance': 25, 'duration': 1}
        
        elif 'Final Fantasy' in group:
            crit_chance = 15
            crit_mult = 1.8
            if 'Fire' in skill_name or 'Ifrit' in name:
                effect = {'type': 'burn', 'chance': 40, 'duration': 3}
            elif 'Ice' in skill_name or 'Shiva' in name:
                effect = {'type': 'freeze', 'chance': 30, 'duration': 2}
            elif 'Thunder' in skill_name or 'Ramuh' in name:
                effect = {'type': 'stun', 'chance': 25, 'duration': 1}
            elif 'Cure' in skill_name or 'Aerith' in name or 'Yuna' in name:
                effect = {'type': 'heal', 'chance': 100, 'duration': 0} # Custom logic needed for heal?
            elif 'Drain' in skill_name:
                effect = {'type': 'life_drain', 'chance': 100, 'duration': 0}

        elif 'Crash' in group:
            effect = {'type': 'wumpa_steal', 'chance': 30, 'duration': 0}
            
        elif 'Spyro' in group:
            effect = {'type': 'burn', 'chance': 35, 'duration': 3}
            
        elif 'Mario' in group:
            if 'Fire' in skill_name:
                effect = {'type': 'burn', 'chance': 25, 'duration': 3}
                
        elif 'Zelda' in group:
            crit_chance = 20
            if 'Ganondorf' in name:
                effect = {'type': 'stun', 'chance': 20, 'duration': 1}
                
        elif 'Metroid' in group:
            if 'Ice' in skill_name:
                effect = {'type': 'freeze', 'chance': 40, 'duration': 2}
                
        elif 'Persona' in group or 'Shin Megami' in group:
             effect = {'type': 'buff_attack', 'chance': 50, 'duration': 3}

        elif 'Dragon Ball' in group:
             crit_chance = 25
             crit_mult = 2.0
             damage = int(damage * 1.1)
             effect = {'type': 'buff_attack', 'chance': 20, 'duration': 2}

        # Fallback random effect for high level chars if no effect assigned
        if effect['type'] == '' and int(char['livello']) > 20:
             # Small chance for random effect
             if random.random() < 0.3:
                 eff_template = random.choice([e for e in effects if e['type'] != ''])
                 effect = {'type': eff_template['type'], 'chance': eff_template['chance'], 'duration': eff_template['duration']}

        abilities.append({
            'id': ability_id,
            'character_id': char_id,
            'name': skill_name,
            'damage': damage,
            'mana_cost': mana,
            'elemental_type': element if element else 'Normal',
            'crit_chance': crit_chance,
            'crit_multiplier': crit_mult,
            'status_effect': effect['type'],
            'status_chance': effect['chance'],
            'status_duration': effect['duration'],
            'description': f"Uses {skill_name}."
        })
        ability_id += 1
        
        # Add a second skill for high level/premium characters?
        # For now just 1 skill per char to match existing structure, but system supports multiple.
        
    # Write to CSV
    with open('data/abilities.csv', 'w', newline='', encoding='utf-8') as f:
        fieldnames = ['id', 'character_id', 'name', 'damage', 'mana_cost', 'elemental_type', 
                      'crit_chance', 'crit_multiplier', 'status_effect', 'status_chance', 
                      'status_duration', 'description']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(abilities)
        
    print(f"Generated {len(abilities)} abilities.")

if __name__ == "__main__":
    generate_abilities()
