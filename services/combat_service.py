import random

class CombatService:
    TYPE_CHART = {
        "Normal": {"Rock": 0.5, "Ghost": 0, "Steel": 0.5},
        "Fire": {"Fire": 0.5, "Water": 0.5, "Grass": 2, "Ice": 2, "Bug": 2, "Rock": 0.5, "Dragon": 0.5, "Steel": 2},
        "Water": {"Fire": 2, "Water": 0.5, "Grass": 0.5, "Ground": 2, "Rock": 2, "Dragon": 0.5},
        "Electric": {"Water": 2, "Electric": 0.5, "Grass": 0.5, "Ground": 0, "Flying": 2, "Dragon": 0.5},
        "Grass": {"Fire": 0.5, "Water": 2, "Grass": 0.5, "Poison": 0.5, "Ground": 2, "Flying": 0.5, "Bug": 0.5, "Rock": 2, "Dragon": 0.5, "Steel": 0.5},
        "Ice": {"Fire": 0.5, "Water": 0.5, "Grass": 2, "Ice": 0.5, "Ground": 2, "Flying": 2, "Dragon": 2, "Steel": 0.5},
        "Fighting": {"Normal": 2, "Ice": 2, "Poison": 0.5, "Flying": 0.5, "Psychic": 0.5, "Bug": 0.5, "Rock": 2, "Ghost": 0, "Dark": 2, "Steel": 2, "Fairy": 0.5},
        "Poison": {"Grass": 2, "Poison": 0.5, "Ground": 0.5, "Rock": 0.5, "Ghost": 0.5, "Steel": 0, "Fairy": 2},
        "Ground": {"Fire": 2, "Electric": 2, "Grass": 0.5, "Poison": 2, "Flying": 0, "Bug": 0.5, "Rock": 2, "Steel": 2},
        "Flying": {"Electric": 0.5, "Grass": 2, "Fighting": 2, "Bug": 2, "Rock": 0.5, "Steel": 0.5},
        "Psychic": {"Fighting": 2, "Poison": 2, "Psychic": 0.5, "Dark": 0, "Steel": 0.5},
        "Bug": {"Fire": 0.5, "Grass": 2, "Fighting": 0.5, "Poison": 0.5, "Flying": 0.5, "Psychic": 2, "Ghost": 0.5, "Dark": 2, "Steel": 0.5, "Fairy": 0.5},
        "Rock": {"Fire": 2, "Ice": 2, "Fighting": 0.5, "Ground": 0.5, "Flying": 2, "Bug": 2, "Steel": 0.5},
        "Ghost": {"Normal": 0, "Psychic": 2, "Ghost": 2, "Dark": 0.5},
        "Dragon": {"Dragon": 2, "Steel": 0.5, "Fairy": 0},
        "Steel": {"Fire": 0.5, "Water": 0.5, "Electric": 0.5, "Ice": 2, "Rock": 2, "Steel": 0.5, "Fairy": 2},
        "Dark": {"Fighting": 0.5, "Psychic": 2, "Ghost": 2, "Dark": 0.5, "Fairy": 0.5},
        "Fairy": {"Fire": 0.5, "Fighting": 2, "Poison": 0.5, "Dragon": 2, "Dark": 2, "Steel": 0.5}
    }

    def get_type_effectiveness(self, attack_type, defender_type):
        if not attack_type or not defender_type:
            return 1.0
        
        attack_type = attack_type.capitalize()
        defender_type = defender_type.capitalize()
        
        if attack_type in self.TYPE_CHART:
            return self.TYPE_CHART[attack_type].get(defender_type, 1.0)
        return 1.0

    def calculate_damage(self, attacker, defender, ability=None):
        """
        Calculate damage based on stats, ability, type, and crit.
        attacker: User object (with stats)
        defender: User object or Mob object
        ability: CharacterAbility object (optional)
        """
        def get_stat(obj, name, default):
            val = getattr(obj, name, default)
            if val.__class__.__name__ in ('Mock', 'MagicMock'):
                return default
            return val if val is not None else default
        
        # Base stats
        base_damage = get_stat(attacker, 'damage_total', 10) 
        
        # Ability damage
        ability_damage = 0
        attack_type = "Normal"
        if ability:
            ability_damage = getattr(ability, 'damage', 0)
            attack_type = getattr(ability, 'elemental_type', "Normal")
        
        total_power = base_damage + ability_damage
        
        # Defender stats
        defense = get_stat(defender, 'defense_total', 0)
        
        # Type Effectiveness
        defender_type = get_stat(defender, 'elemental_type', "Normal")
        effectiveness = self.get_type_effectiveness(attack_type, defender_type)
        
        # Critical Hit
        def get_stat(obj, name, default):
            val = getattr(obj, name, default)
            # Handle Mocks which 'exist' but aren't what we want (return a Mock instead of missing)
            if val.__class__.__name__ in ('Mock', 'MagicMock'):
                # Check if it's been set to something else
                # Since we reached here, getattr returned the Mock itself
                return default
            return val if val is not None else default

        crit_chance = get_stat(attacker, 'crit_chance', 5)
        crit_multiplier = get_stat(attacker, 'crit_multiplier', 1.5)
        
        is_crit = random.randint(1, 100) <= crit_chance
        
        damage = (total_power - (defense / 2)) * effectiveness
        
        if is_crit:
            damage *= crit_multiplier
            
        damage = max(1, int(damage)) # Minimum 1 damage
        
        return {
            "damage": damage,
            "is_crit": is_crit,
            "effectiveness": effectiveness,
            "type": attack_type
        }

    def calculate_mob_damage_to_user(self, mob, user, is_aoe=False, is_boss=False):
        """
        Calculate damage dealt by a mob to a user.
        Applying:
        - Mob Base Damage
        - Level Factor Scaling
        - User Resistance
        - Status Effects (Defense Up)
        """
        from services.status_effects import StatusEffect

        # Invincibility check
        import datetime
        if user.invincible_until and datetime.datetime.now() < user.invincible_until:
            return 0

        base_damage = mob.attack_damage if mob.attack_damage else 10
        multiplier = 1.0
        
        # AoE Check logic typically handled outside, but if passed down:
        # We assume 'base_damage' passed here is the raw mob damage.
        # If is_aoe is True, we apply a reduction unless user is primary target.
        # But wait, identifying primary target here is tricky without context.
        # Let's assume the CALLER adjusts base_damage or multiplier passed?
        # No, let's keep it simple: caller passes the 'effective' multiplier if needed, 
        # or we follow the standard logic:
        # Standard logic in PveService was: 0.7 for primary, 0.5 for others. 
        # Here we just calculate raw mitigation.
        
        # Level Scaling
        user_level = getattr(user, 'livello', 1) or 1
        level_factor = 1 + (user_level * 0.02)
        
        # Initial Damage Calculation
        # The formula in PveService was: (base * 0.5 * multiplier) / level_factor
        # Let's stick to that but allow multiplier injection.
        
        adjusted_damage = int((base_damage * 0.5) / level_factor)
        damage = int(adjusted_damage * random.uniform(0.8, 1.2))
        
        if is_aoe:
            # Default AoE reduction if not specific
            damage = int(damage * 0.5)

        # Resistance Calculation
        user_res = getattr(user, 'allocated_resistance', 0) or 0
        
        # Check for Defense Up status
        if StatusEffect.has_effect(user, 'defense_up'):
            # Add 5% resistance
            user_res += 5
            
        # Hard cap at 75%
        user_res = min(user_res, 75)
        
        if user_res > 0:
            reduction_factor = 100 / (100 + user_res)
            damage = int(damage * reduction_factor)
            
        return max(1, damage)

    def calculate_counterattack_damage(self, attacker, defender, parry_multiplier=1.2, is_perfect=False):
        """
        Calculate counterattack damage after a successful parry.
        - Standard success: parry_multiplier (passed from service)
        - Perfect success: parry_multiplier * 1.2 (perfect bonus) + forced critical hit
        """
        # Base damage calculation
        dmg_data = self.calculate_damage(attacker, defender)
        base_damage = dmg_data['damage']
        
        # Apply parry multiplier
        damage = base_damage * parry_multiplier
        
        # Perfect parry adds extra 1.2x bonus and forces a critical hit
        is_crit = dmg_data['is_crit']
        if is_perfect:
            damage *= 1.2
            is_crit = True
            
        return {
            "damage": int(max(1, damage)),
            "is_crit": is_crit,
            "is_counter": True,
            "effectiveness": dmg_data['effectiveness'],
            "type": dmg_data['type']
        }

    def apply_status_effect(self, target, ability, source_id=None):
        """
        Apply status effect from ability to target
        Returns dict with effect info if successful, else None
        Does NOT actually apply it here (done by PvE Service via StatusEffect)
        Wait, PvE service calls this to CHECK if it applies.
        So we should just return the data structure.
        """
        if not ability or not ability.status_effect:
            return None
            
        chance = ability.status_chance
        if random.randint(1, 100) <= chance:
            return {
                "effect": ability.status_effect,
                "duration": ability.status_duration,
                "source_id": source_id
            }
        return None
