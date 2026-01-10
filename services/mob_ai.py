"""
Mob AI System - Handles mob behavior and ability selection.
"""

import random
import json

class MobAI:
    """AI system for mob behavior"""
    
    BEHAVIORS = ['aggressive', 'tactical', 'defensive']
    
    @staticmethod
    def select_action(mob, active_players, mob_abilities=None):
        """
        Determine mob's next action based on AI behavior
        
        Args:
            mob: Mob object
            active_players: List of active player objects
            mob_abilities: List of MobAbility objects (optional)
            
        Returns:
            Dictionary with action type and details
        """
        if not active_players:
            return {'action': 'idle'}
        
        # Get mob behavior
        behavior = getattr(mob, 'ai_behavior', 'aggressive')
        
        # Get available abilities
        active_ability_ids = json.loads(getattr(mob, 'active_abilities', None) or '[]')
        
        # If no abilities or no ability data, use basic attack
        if not active_ability_ids or not mob_abilities:
            target = MobAI.select_target(mob, active_players, 'random')
            return {'action': 'basic_attack', 'target': target}
        
        # Filter available abilities
        available_abilities = [a for a in mob_abilities if a.id in active_ability_ids]
        
        if not available_abilities:
            target = MobAI.select_target(mob, active_players, 'random')
            return {'action': 'basic_attack', 'target': target}
        
        # Behavior-based ability selection
        if behavior == 'aggressive':
            # Prioritize damage abilities (70% chance)
            if random.random() < 0.7:
                damage_abilities = [a for a in available_abilities if a.damage > 0]
                if damage_abilities:
                    ability = random.choice(damage_abilities)
                    targets = MobAI.select_ability_targets(ability, active_players)
                    return {'action': 'ability', 'ability': ability, 'targets': targets}
        
        elif behavior == 'tactical':
            # Use abilities strategically based on HP
            hp_percent = (mob.health / mob.max_health) * 100 if mob.max_health > 0 else 0
            
            if hp_percent < 50:
                # Low HP: use defensive/healing abilities
                defensive = [a for a in available_abilities if a.buff_type in ['defense', 'evasion', 'heal']]
                if defensive and random.random() < 0.8:
                    ability = random.choice(defensive)
                    return {'action': 'ability', 'ability': ability, 'targets': [mob]}
            else:
                # High HP: use debuff abilities
                debuff = [a for a in available_abilities if a.status_effect]
                if debuff and random.random() < 0.5:
                    ability = random.choice(debuff)
                    targets = MobAI.select_ability_targets(ability, active_players)
                    return {'action': 'ability', 'ability': ability, 'targets': targets}
        
        elif behavior == 'defensive':
            # Prefer buffs and debuffs over damage (60% chance)
            support = [a for a in available_abilities if a.buff_type or a.status_effect]
            if support and random.random() < 0.6:
                ability = random.choice(support)
                if ability.buff_type:
                    return {'action': 'ability', 'ability': ability, 'targets': [mob]}
                else:
                    targets = MobAI.select_ability_targets(ability, active_players)
                    return {'action': 'ability', 'ability': ability, 'targets': targets}
        
        elif behavior == 'boss':
            # Boss behavior: High damage, AoE, and tactical
            hp_percent = (mob.health / mob.max_health) * 100 if mob.max_health > 0 else 0
            
            # 40% chance to use AoE if many players
            if len(active_players) >= 3 and random.random() < 0.4:
                aoe_abilities = [a for a in available_abilities if getattr(a, 'target_type', 'single') == 'aoe']
                if aoe_abilities:
                    ability = random.choice(aoe_abilities)
                    targets = MobAI.select_ability_targets(ability, active_players)
                    return {'action': 'ability', 'ability': ability, 'targets': targets}
            
            # 60% chance to use strongest ability
            if random.random() < 0.6:
                strongest = max(available_abilities, key=lambda a: a.damage)
                targets = MobAI.select_ability_targets(strongest, active_players)
                return {'action': 'ability', 'ability': strongest, 'targets': targets}
            
            # 20% chance to heal/buff if low HP
            if hp_percent < 30 and random.random() < 0.2:
                defensive = [a for a in available_abilities if a.buff_type in ['defense', 'heal']]
                if defensive:
                    ability = random.choice(defensive)
                    return {'action': 'ability', 'ability': ability, 'targets': [mob]}
        
        # Default: basic attack
        target = MobAI.select_target(mob, active_players, 'random')
        return {'action': 'basic_attack', 'target': target}
    
    @staticmethod
    def select_target(mob, active_players, strategy='random'):
        """
        Select target based on strategy
        
        Args:
            mob: Mob object
            active_players: List of player objects
            strategy: Target selection strategy
            
        Returns:
            Selected player object
        """
        if not active_players:
            return None
        
        if strategy == 'random':
            return random.choice(active_players)
        elif strategy == 'lowest_hp':
            return min(active_players, key=lambda p: getattr(p, 'current_hp', getattr(p, 'health', 100)))
        elif strategy == 'highest_damage':
            # Would need damage tracking
            return random.choice(active_players)
        
        return random.choice(active_players)
    
    @staticmethod
    def select_ability_targets(ability, active_players):
        """
        Select targets for an ability
        
        Args:
            ability: MobAbility object
            active_players: List of player objects
            
        Returns:
            List of selected targets
        """
        if not active_players:
            return []
        
        target_type = getattr(ability, 'target_type', 'single')
        max_targets = getattr(ability, 'max_targets', 1)
        
        if target_type == 'single':
            return [random.choice(active_players)]
        elif target_type == 'aoe':
            # Hit all players up to max_targets
            return active_players[:max_targets] if max_targets < len(active_players) else active_players
        elif target_type == 'random':
            # Random number of targets up to max
            num_targets = random.randint(1, min(max_targets, len(active_players)))
            return random.sample(active_players, num_targets)
        elif target_type == 'lowest_hp':
            # Target lowest HP players
            sorted_players = sorted(active_players, key=lambda p: getattr(p, 'current_hp', 100))
            return sorted_players[:max_targets]
        
        return [random.choice(active_players)]
