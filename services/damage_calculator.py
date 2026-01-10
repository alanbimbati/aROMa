"""
Damage Calculator - Enhanced damage calculation with elemental types, crits, and resistances.
"""

import random

class DamageCalculator:
    """Enhanced damage calculation system"""
    
    # Elemental effectiveness chart (Pokemon-style)
    ELEMENTAL_CHART = {
        'Fire': {'Grass': 2.0, 'Water': 0.5, 'Ice': 2.0, 'Fire': 0.5},
        'Water': {'Fire': 2.0, 'Grass': 0.5, 'Electric': 0.5, 'Water': 0.5},
        'Grass': {'Water': 2.0, 'Fire': 0.5, 'Flying': 0.5, 'Grass': 0.5},
        'Electric': {'Water': 2.0, 'Grass': 0.5, 'Ground': 0.0, 'Electric': 0.5},
        'Ice': {'Grass': 2.0, 'Fire': 0.5, 'Water': 0.5, 'Ice': 0.5},
        'Dark': {'Psychic': 2.0, 'Light': 0.5, 'Dark': 0.5},
        'Light': {'Dark': 2.0, 'Psychic': 0.5, 'Light': 0.5},
        'Psychic': {'Fighting': 2.0, 'Dark': 0.5, 'Psychic': 0.5},
        'Fighting': {'Normal': 2.0, 'Flying': 0.5, 'Psychic': 0.5},
        'Flying': {'Grass': 2.0, 'Electric': 0.5, 'Fighting': 2.0},
        'Ground': {'Electric': 2.0, 'Fire': 2.0, 'Grass': 0.5, 'Flying': 0.0},
        'Normal': {},  # Neutral to all
        'physical': {},  # Alias for Normal
        'magic': {},  # Neutral
        'ranged': {},  # Neutral
        'explosive': {}  # Neutral
    }
    
    @staticmethod
    def calculate_damage(attacker, defender, ability=None, is_special=False):
        """
        Calculate damage with all modifiers
        
        Args:
            attacker: User object or wrapper with damage stats
            defender: Mob object or wrapper with defense stats
            ability: CharacterAbility object (optional)
            is_special: Boolean for special attack
            
        Returns:
            Dictionary with damage, is_crit, effectiveness, elemental_type
        """
        # Base damage
        base_dmg = getattr(attacker, 'base_damage', 10)
        base_dmg += getattr(attacker, 'allocated_damage', 0)
        
        # Ability modifier
        if ability:
            base_dmg += getattr(ability, 'damage', 0)
            elemental_type = getattr(ability, 'elemental_type', 'Normal')
        else:
            # Get from attacker's character or default
            elemental_type = getattr(attacker, 'elemental_type', 'Normal')
        
        # Character damage bonus (if attacker has character equipped)
        if hasattr(attacker, 'damage_total'):
            base_dmg = getattr(attacker, 'damage_total', base_dmg)
        
        # Critical Hit Check
        crit_chance = getattr(attacker, 'allocated_crit_rate', 0)
        
        # Add character crit chance
        if hasattr(attacker, 'crit_chance'):
            crit_chance += getattr(attacker, 'crit_chance', 0)
        
        # Add ability crit chance
        if ability:
            crit_chance += getattr(ability, 'crit_chance', 0)
        
        is_crit = random.randint(1, 100) <= crit_chance
        crit_multiplier = 1.0
        
        if is_crit:
            if ability and hasattr(ability, 'crit_multiplier'):
                crit_multiplier = ability.crit_multiplier
            elif hasattr(attacker, 'crit_multiplier'):
                crit_multiplier = attacker.crit_multiplier
            else:
                crit_multiplier = 1.5
            
            base_dmg *= crit_multiplier
        
        # Elemental Effectiveness
        defender_type = getattr(defender, 'attack_type', 'Normal')
        effectiveness = DamageCalculator.get_elemental_effectiveness(elemental_type, defender_type)
        base_dmg *= effectiveness
        
        # Defender Resistance
        resistance = getattr(defender, 'resistance', 0)
        if resistance > 0:
            resistance_reduction = resistance / 100
            base_dmg *= (1 - resistance_reduction)
        
        # Defender Defense (if has defense_total attribute)
        if hasattr(defender, 'defense_total'):
            defense = getattr(defender, 'defense_total', 0)
            # Defense reduces damage by a percentage (max 50%)
            defense_reduction = min(defense / 200, 0.5)
            base_dmg *= (1 - defense_reduction)
        
        # Random variance (±10%)
        variance = random.uniform(0.9, 1.1)
        final_damage = int(base_dmg * variance)
        
        return {
            'damage': max(1, final_damage),  # Minimum 1 damage
            'is_crit': is_crit,
            'crit_multiplier': crit_multiplier if is_crit else 1.0,
            'effectiveness': effectiveness,
            'elemental_type': elemental_type,
            'defender_type': defender_type
        }
    
    @staticmethod
    def get_elemental_effectiveness(attacker_type, defender_type):
        """
        Get elemental effectiveness multiplier
        
        Args:
            attacker_type: Elemental type of attack
            defender_type: Elemental type of defender
            
        Returns:
            Effectiveness multiplier (0.0, 0.5, 1.0, or 2.0)
        """
        if attacker_type not in DamageCalculator.ELEMENTAL_CHART:
            return 1.0
        
        effectiveness_map = DamageCalculator.ELEMENTAL_CHART[attacker_type]
        return effectiveness_map.get(defender_type, 1.0)
    
    @staticmethod
    def format_damage_message(damage_result, attacker_name, defender_name, ability_name=None):
        """
        Format damage result into a readable message
        
        Args:
            damage_result: Result from calculate_damage
            attacker_name: Name of attacker
            defender_name: Name of defender
            ability_name: Name of ability used (optional)
            
        Returns:
            Formatted message string
        """
        damage = damage_result['damage']
        is_crit = damage_result['is_crit']
        effectiveness = damage_result['effectiveness']
        
        # Base message
        if ability_name:
            message = f"💥 {attacker_name} usa {ability_name} su {defender_name} per {damage} danni"
        else:
            message = f"💥 {attacker_name} attacca {defender_name} per {damage} danni"
        
        # Add crit indicator
        if is_crit:
            message += " ⚡ **CRITICO!**"
        
        # Add effectiveness indicator
        if effectiveness > 1.0:
            message += " 🔥 *Super efficace!*"
        elif effectiveness < 1.0 and effectiveness > 0:
            message += " 💧 *Poco efficace...*"
        elif effectiveness == 0:
            message += " 🚫 *Nessun effetto!*"
        
        return message
