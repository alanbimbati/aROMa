"""
Boss Phase Manager - Manages boss phase transitions and mechanics.
"""

import json

class BossPhaseManager:
    """Manages boss phase transitions and mechanics"""
    
    # Boss phase configurations
    BOSS_PHASES = {
        'Drago Antico': {
            'phase2': {
                'hp_threshold': 50,
                'announcement': '🔥 Il Drago Antico spicca il volo! Le sue fiamme si intensificano!',
                'stat_changes': {
                    'attack_damage_mult': 1.5,
                    'speed_mult': 1.2
                }
            },
            'phase3': {
                'hp_threshold': 25,
                'announcement': '💀 Il Drago Antico entra in FURIA! Attenzione!',
                'stat_changes': {
                    'attack_damage_mult': 2.0,
                    'resistance_add': 20
                },
                'heal_percent': 0.25
            }
        },
        'Lich King': {
            'phase2': {
                'hp_threshold': 50,
                'announcement': '☠️ Il Lich King evoca i non-morti!',
                'summon_mobs': ['Skeleton Warrior', 'Skeleton Warrior']
            },
            'phase3': {
                'hp_threshold': 25,
                'announcement': '🧊 Il Lich King congela l\'arena!',
                'stat_changes': {
                    'resistance_add': 30
                }
            }
        }
    }
    
    @staticmethod
    def check_phase_transition(mob):
        """
        Check if mob should transition to next phase
        
        Args:
            mob: Mob object
            
        Returns:
            Tuple of (should_transition, phase_name, phase_config)
        """
        if not mob.is_boss:
            return False, None, None
        
        # Get boss phase config from database column
        phase_thresholds_raw = getattr(mob, 'phase_thresholds', '{}')
        if not phase_thresholds_raw:
            return False, None, None
            
        try:
            phase_thresholds = json.loads(phase_thresholds_raw)
        except:
            return False, None, None
            
        if not phase_thresholds:
            return False, None, None
        
        # Calculate HP percentage
        hp_percent = (mob.health / mob.max_health) * 100 if mob.max_health > 0 else 0
        current_phase = getattr(mob, 'current_phase', 1)
        
        # Check each phase in the thresholds
        # Thresholds are { "70": "phase2", "30": "phase3" }
        for threshold_str, phase_name in sorted(phase_thresholds.items(), key=lambda x: int(x[0]), reverse=True):
            threshold = int(threshold_str)
            phase_num = int(phase_name.replace('phase', ''))
            
            # Transition if HP below threshold and not already in this phase
            if hp_percent <= threshold and current_phase < phase_num:
                # Get generic phase config or specific if available
                # For now, we'll use a generic config based on the phase number
                # but we could also store full configs in the DB
                phase_config = BossPhaseManager.get_default_phase_config(mob, phase_num)
                return True, phase_name, phase_config
        
        return False, None, None

    @staticmethod
    def get_default_phase_config(mob, phase_num):
        """Get default phase configuration based on phase number"""
        if phase_num == 2:
            return {
                'announcement': f'🔥 {mob.name} entra nella FASE 2!',
                'stat_changes': {
                    'attack_damage_mult': 1.3,
                    'speed_mult': 1.1
                }
            }
        elif phase_num == 3:
            return {
                'announcement': f'💀 {mob.name} entra nella FASE 3! È FURIA!',
                'stat_changes': {
                    'attack_damage_mult': 1.6,
                    'resistance_add': 15
                },
                'heal_percent': 0.15
            }
        elif phase_num >= 4:
            return {
                'announcement': f'⚡ {mob.name} ha raggiunto la sua FORMA FINALE!',
                'stat_changes': {
                    'attack_damage_mult': 2.0,
                    'resistance_add': 25,
                    'speed_mult': 1.3
                },
                'heal_percent': 0.25
            }
        return {}
    
    @staticmethod
    def apply_phase_transition(mob, phase_name, phase_config):
        """
        Apply phase transition effects to mob
        
        Args:
            mob: Mob object
            phase_name: Name of phase (e.g., 'phase2')
            phase_config: Phase configuration dictionary
            
        Returns:
            List of messages describing phase changes
        """
        messages = []
        
        # Announcement
        announcement = phase_config.get('announcement')
        if announcement:
            messages.append(announcement)
        
        # Update phase number
        phase_num = int(phase_name.replace('phase', ''))
        mob.current_phase = phase_num
        
        # Apply stat changes
        stat_changes = phase_config.get('stat_changes', {})
        for stat, value in stat_changes.items():
            if stat == 'attack_damage_mult':
                mob.attack_damage = int(mob.attack_damage * value)
                messages.append(f"⚔️ Danno aumentato a {mob.attack_damage}!")
            elif stat == 'speed_mult':
                mob.speed = int(mob.speed * value)
                messages.append(f"⚡ Velocità aumentata a {mob.speed}!")
            elif stat == 'resistance_add':
                mob.resistance = min(90, mob.resistance + value)
                messages.append(f"🛡️ Resistenza aumentata al {mob.resistance}%!")
        
        # Heal
        heal_percent = phase_config.get('heal_percent')
        if heal_percent:
            heal_amount = int(mob.max_health * heal_percent)
            mob.health = min(mob.max_health, mob.health + heal_amount)
            messages.append(f"💚 {mob.name} si rigenera! (+{heal_amount} HP)")
        
        # Summon mobs (would need integration with spawn system)
        summon_mobs = phase_config.get('summon_mobs', [])
        if summon_mobs:
            messages.append(f"⚠️ {mob.name} evoca rinforzi!")
            # TODO: Integrate with mob spawning system
        
        return messages
    
    @staticmethod
    def get_phase_display(mob):
        """
        Get display string for current boss phase
        
        Args:
            mob: Mob object
            
        Returns:
            String describing current phase
        """
        if not mob.is_boss:
            return ""
        
        current_phase = getattr(mob, 'current_phase', 1)
        if current_phase == 1:
            return ""
        
        return f" [FASE {current_phase}]"
