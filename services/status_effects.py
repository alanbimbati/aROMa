"""
Status Effects System - Handles all status effects (burn, poison, stun, confusion, etc.)
"""

import random
import json

class StatusEffect:
    """Status effect handler"""
    
    # Status effect configurations
    EFFECTS = {
        'burn': {
            'damage_per_turn': lambda level: 5 + level * 2,
            'duration': 3,
            'stackable': False,
            'message': '🔥 {target} brucia! (-{damage} HP)',
            'icon': '🔥'
        },
        'poison': {
            'damage_per_turn': lambda level: 3 + level,
            'duration': 5,
            'stackable': True,
            'max_stacks': 3,
            'message': '☠️ {target} è avvelenato! (-{damage} HP)',
            'icon': '☠️'
        },
        'stun': {
            'skip_turn': True,
            'duration': 1,
            'stackable': False,
            'message': '⚡ {target} è stordito! Perde il turno!',
            'icon': '⚡'
        },
        'confusion': {
            'self_damage_chance': 50,
            'duration': 2,
            'stackable': False,
            'message': '😵 {target} è confuso! Si colpisce da solo!',
            'icon': '😵'
        },
        'mind_control': {
            'attack_allies': True,
            'duration': 2,
            'stackable': False,
            'message': '🧠 {target} è sotto controllo mentale! Attacca gli alleati!',
            'icon': '🧠'
        },
        'freeze': {
            'skip_turn': True,
            'break_chance': 30,  # 30% chance to break each turn
            'duration': 999,  # Until broken
            'stackable': False,
            'message': '❄️ {target} è congelato!',
            'icon': '❄️'
        },
        'bleed': {
            'damage_per_turn': lambda level: 10 + level * 3,
            'duration': 4,
            'stackable': True,
            'max_stacks': 5,
            'message': '🩸 {target} sanguina! (-{damage} HP)',
            'icon': '🩸'
        },
        'slow': {
            'speed_reduction': 50,  # Percentage
            'duration': 3,
            'stackable': False,
            'message': '🐌 {target} è rallentato!',
            'icon': '🐌'
        },
        'weakness': {
            'damage_reduction': 30,  # Percentage reduction to damage dealt
            'duration': 3,
            'stackable': False,
            'message': '💔 {target} è indebolito!',
            'icon': '💔'
        },
        'defense_up': {
            'resistance_bonus': 5,  # +5% Resistance
            'duration': 1, # 1 turn (or until next attack processed)
            'stackable': False,
            'message': '🛡️ {target} è in Difesa!',
            'icon': '🛡️'
        }
    }
    
    @staticmethod
    def apply_status(target, effect_name, duration=None, source_level=1, source_id=None):
        """
        Apply status effect to target
        
        Args:
            target: User or Mob object
            effect_name: Name of effect to apply
            duration: Override duration (optional)
            source_level: Level of source for damage scaling
            source_id: ID of the source (User ID or Mob ID)
            
        Returns:
            Boolean success
        """
        if effect_name not in StatusEffect.EFFECTS:
            return False
        
        effect_config = StatusEffect.EFFECTS[effect_name]
        
        # Load existing effects
        effects = json.loads(getattr(target, 'active_status_effects', None) or '[]')
        
        # Check if stackable
        existing = next((e for e in effects if e.get('effect') == effect_name or e.get('id') == effect_name), None)
        
        if existing:
            if effect_config.get('stackable', False):
                max_stacks = effect_config.get('max_stacks', 999)
                if existing['stacks'] < max_stacks:
                    existing['stacks'] += 1
                    existing['duration'] = duration or effect_config['duration']
            else:
                # Refresh duration
                existing['duration'] = duration or effect_config['duration']
                # Update source if new application overwrites
                if source_id:
                     existing['source_id'] = source_id
        else:
            # Add new effect
            effects.append({
                'effect': effect_name,
                'duration': duration or effect_config['duration'],
                'stacks': 1,
                'source_level': source_level,
                'source_id': source_id
            })
        
        target.active_status_effects = json.dumps(effects)
        return True
    
    @staticmethod
    def process_turn_effects(target):
        """
        Process all status effects at turn start
        
        Args:
            target: User or Mob object
            
        Returns:
            Dictionary with messages, damage, skip_turn, attack_allies flags
        """
        effects = json.loads(getattr(target, 'active_status_effects', None) or '[]')
        messages = []
        total_damage = 0
        skip_turn = False
        attack_allies = False
        speed_modifier = 1.0
        damage_modifier = 1.0
        
        remaining_effects = []
        
        for effect_data in effects:
            effect_name = effect_data.get('effect') or effect_data.get('id')
            effect_config = StatusEffect.EFFECTS.get(effect_name)
            
            if not effect_config:
                continue
            
            # Process damage over time
            if 'damage_per_turn' in effect_config:
                dmg = effect_config['damage_per_turn'](effect_data['source_level'])
                dmg *= effect_data['stacks']
                total_damage += dmg
                messages.append(effect_config['message'].format(
                    target=getattr(target, 'nome', getattr(target, 'name', 'Target')),
                    damage=dmg
                ))
            
            # Process turn skip
            if effect_config.get('skip_turn'):
                skip_turn = True
                messages.append(effect_config['message'].format(
                    target=getattr(target, 'nome', getattr(target, 'name', 'Target'))
                ))
            
            # Process mind control
            if effect_config.get('attack_allies'):
                attack_allies = True
                messages.append(effect_config['message'].format(
                    target=getattr(target, 'nome', getattr(target, 'name', 'Target'))
                ))
            
            # Process speed reduction
            if 'speed_reduction' in effect_config:
                speed_modifier *= (1 - effect_config['speed_reduction'] / 100)
            
            # Process damage reduction
            if 'damage_reduction' in effect_config:
                damage_modifier *= (1 - effect_config['damage_reduction'] / 100)
            
            # Decrease duration
            effect_data['duration'] -= 1
            
            # Check if effect persists
            if effect_data['duration'] > 0:
                # Check break chance (for freeze, etc.)
                break_chance = effect_config.get('break_chance', 0)
                if break_chance and random.randint(1, 100) <= break_chance:
                    messages.append(f"✨ {getattr(target, 'nome', getattr(target, 'name', 'Target'))} si libera da {effect_name}!")
                else:
                    remaining_effects.append(effect_data)
            else:
                # Effect expired
                messages.append(f"⏰ L'effetto {effect_name} su {getattr(target, 'nome', getattr(target, 'name', 'Target'))} è terminato")
        
        # Update target
        target.active_status_effects = json.dumps(remaining_effects)
        
        # Apply damage
        if total_damage > 0:
            if hasattr(target, 'current_hp'):
                target.current_hp = max(0, target.current_hp - total_damage)
            elif hasattr(target, 'health'):
                target.health = max(0, target.health - total_damage)
        
        return {
            'messages': messages,
            'damage': total_damage,
            'skip_turn': skip_turn,
            'attack_allies': attack_allies,
            'speed_modifier': speed_modifier,
            'damage_modifier': damage_modifier
        }
    
    @staticmethod
    def get_active_effects(target):
        """Get list of active effects on target"""
        effects = json.loads(getattr(target, 'active_status_effects', None) or '[]')
        return effects
    
    @staticmethod
    def has_effect(target, effect_name):
        """Check if target has specific effect"""
        effects = StatusEffect.get_active_effects(target)
        return any(e.get('effect') == effect_name or e.get('id') == effect_name for e in effects)
    
    @staticmethod
    def remove_effect(target, effect_name):
        """Remove specific effect from target"""
        effects = json.loads(getattr(target, 'active_status_effects', None) or '[]')
        effects = [e for e in effects if e.get('effect') != effect_name and e.get('id') != effect_name]
        target.active_status_effects = json.dumps(effects)
        return True
    
    @staticmethod
    def clear_all_effects(target):
        """Remove all effects from target"""
        target.active_status_effects = json.dumps([])
        return True
    
    @staticmethod
    def format_effects_display(target):
        """Format active effects for display"""
        effects = StatusEffect.get_active_effects(target)
        
        if not effects:
            return "Nessun effetto attivo"
        
        display_parts = []
        for effect_data in effects:
            effect_name = effect_data.get('effect') or effect_data.get('id')
            effect_config = StatusEffect.EFFECTS.get(effect_name)
            
            if not effect_config:
                continue
            
            icon = effect_config.get('icon', '•')
            stacks = effect_data.get('stacks', 1)
            duration = effect_data.get('duration', 0)
            
            if stacks > 1:
                display_parts.append(f"{icon} {effect_name} x{stacks} ({duration} turni)")
            else:
                display_parts.append(f"{icon} {effect_name} ({duration} turni)")
        
        return " | ".join(display_parts)
