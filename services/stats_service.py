"""
Stats Service
Handles user stat point allocation and reset
"""
from database import Database
from services.user_service import UserService
from settings import PointsName
import datetime

class StatsService:
    def __init__(self):
        self.db = Database()
        self.user_service = UserService()
    
    # Stat point values
    HEALTH_PER_POINT = 10
    MANA_PER_POINT = 5
    DAMAGE_PER_POINT = 2
    SPEED_PER_POINT = 1      # Reduces cooldown
    RESISTANCE_PER_POINT = 1 # Reduces damage taken %
    CRIT_RATE_PER_POINT = 1  # Increases crit chance %
    RESET_COST = 0
    
    def get_available_stat_points(self, user):
        """
        Calculate available stat points
        User gets 1 point per level
        """
        total_points = user.livello
        used_points = (user.allocated_health + user.allocated_mana + user.allocated_damage + 
                      getattr(user, 'allocated_speed', 0) + 
                      getattr(user, 'allocated_resistance', 0) + 
                      getattr(user, 'allocated_crit_rate', 0))
        available = total_points - used_points
        
        return {
            'total': total_points,
            'used': used_points,
            'available': max(0, available)
        }
    
    def allocate_stat_point(self, user, stat_type):
        """
        Allocate one stat point to health/mana/damage/speed/res/crit
        Returns (success: bool, message: str)
        """
        # Check if user has available points
        points_info = self.get_available_stat_points(user)
        if points_info['available'] <= 0:
            return False, "Non hai punti disponibili! Sali di livello per ottenerne altri."
        
        # Allocate based on type
        if stat_type == 'health':
            new_allocated = user.allocated_health + 1
            self.user_service.update_user(user.id_telegram, {'allocated_health': new_allocated})
            
            # Update max health and current health
            new_max_health = user.max_health + self.HEALTH_PER_POINT
            new_health = min(user.health + self.HEALTH_PER_POINT, new_max_health)
            self.user_service.update_user(user.id_telegram, {
                'max_health': new_max_health,
                'health': new_health
            })
            return True, f"✅ +{self.HEALTH_PER_POINT} Vita Max! Nuova Vita: {new_max_health} HP"
            
        elif stat_type == 'mana':
            new_allocated = user.allocated_mana + 1
            self.user_service.update_user(user.id_telegram, {'allocated_mana': new_allocated})
            
            # Update max mana and current mana
            new_max_mana = user.max_mana + self.MANA_PER_POINT
            new_mana = min(user.mana + self.MANA_PER_POINT, new_max_mana)
            self.user_service.update_user(user.id_telegram, {
                'max_mana': new_max_mana,
                'mana': new_mana
            })
            return True, f"✅ +{self.MANA_PER_POINT} Mana Max! Nuovo Mana: {new_max_mana}"
            
        elif stat_type == 'damage':
            new_allocated = user.allocated_damage + 1
            self.user_service.update_user(user.id_telegram, {'allocated_damage': new_allocated})
            
            # Update base damage
            new_damage = user.base_damage + self.DAMAGE_PER_POINT
            self.user_service.update_user(user.id_telegram, {'base_damage': new_damage})
            return True, f"✅ +{self.DAMAGE_PER_POINT} Danno! Nuovo Danno Base: {new_damage}"
            
        elif stat_type == 'speed':
            new_allocated = getattr(user, 'allocated_speed', 0) + 1
            self.user_service.update_user(user.id_telegram, {'allocated_speed': new_allocated})
            return True, f"✅ +{self.SPEED_PER_POINT} Velocità! Riduci il cooldown attacchi."
            
        elif stat_type == 'resistance':
            new_allocated = getattr(user, 'allocated_resistance', 0) + 1
            self.user_service.update_user(user.id_telegram, {'allocated_resistance': new_allocated})
            return True, f"✅ +{self.RESISTANCE_PER_POINT}% Resistenza! Subisci meno danni."
            
        elif stat_type == 'crit_rate':
            new_allocated = getattr(user, 'allocated_crit_rate', 0) + 1
            self.user_service.update_user(user.id_telegram, {'allocated_crit_rate': new_allocated})
            return True, f"✅ +{self.CRIT_RATE_PER_POINT}% Crit Rate! Più probabilità di critico."
        
        else:
            return False, "Tipo di statistica non valido!"
    
    def reset_stat_points(self, user):
        """
        Reset all allocated stat points (FREE)
        Returns (success: bool, message: str)
        """
        # Calculate stats to remove
        health_to_remove = user.allocated_health * self.HEALTH_PER_POINT
        mana_to_remove = user.allocated_mana * self.MANA_PER_POINT
        damage_to_remove = user.allocated_damage * self.DAMAGE_PER_POINT
        
        points_returned = (user.allocated_health + user.allocated_mana + user.allocated_damage +
                          getattr(user, 'allocated_speed', 0) + 
                          getattr(user, 'allocated_resistance', 0) + 
                          getattr(user, 'allocated_crit_rate', 0))
        
        # Reset allocated points
        self.user_service.update_user(user.id_telegram, {
            'allocated_health': 0,
            'allocated_mana': 0,
            'allocated_damage': 0,
            'allocated_speed': 0,
            'allocated_resistance': 0,
            'allocated_crit_rate': 0,
            'last_stat_reset': datetime.datetime.now()
        })
        
        # Update stats back to base
        new_max_health = user.max_health - health_to_remove
        new_max_mana = user.max_mana - mana_to_remove
        new_base_damage = user.base_damage - damage_to_remove
        
        # Ensure current health/mana don't exceed new max
        new_health = min(user.health, new_max_health)
        new_mana = min(user.mana, new_max_mana)
        
        self.user_service.update_user(user.id_telegram, {
            'max_health': new_max_health,
            'health': new_health,
            'max_mana': new_max_mana,
            'mana': new_mana,
            'base_damage': new_base_damage
        })
        
        return True, f"🔄 Statistiche resettate!\n\n💰 Costo: Gratuito\n📊 Punti restituiti: {points_returned}\n\nOra puoi riallocarli come preferisci!"
    
    def get_stat_allocation_summary(self, user):
        """
        Get formatted summary of stat allocation
        Returns formatted string
        """
        points_info = self.get_available_stat_points(user)
        
        msg = f"📊 **ALLOCAZIONE STATISTICHE**\n\n"
        msg += f"🎯 Punti Totali: {points_info['total']} (Livello {user.livello})\n"
        msg += f"✅ Punti Usati: {points_info['used']}\n"
        msg += f"🆓 Punti Disponibili: {points_info['available']}\n\n"
        
        msg += f"**Allocati:**\n"
        msg += f"❤️ Vita: {user.allocated_health} (+{user.allocated_health * self.HEALTH_PER_POINT} HP)\n"
        msg += f"💙 Mana: {user.allocated_mana} (+{user.allocated_mana * self.MANA_PER_POINT} MP)\n"
        msg += f"⚔️ Danno: {user.allocated_damage} (+{user.allocated_damage * self.DAMAGE_PER_POINT} DMG)\n"
        msg += f"⚡ Velocità: {getattr(user, 'allocated_speed', 0)} (+{getattr(user, 'allocated_speed', 0) * self.SPEED_PER_POINT})\n"
        msg += f"🛡️ Resistenza: {getattr(user, 'allocated_resistance', 0)} (+{getattr(user, 'allocated_resistance', 0) * self.RESISTANCE_PER_POINT}%)\n"
        msg += f"🎯 Crit Rate: {getattr(user, 'allocated_crit_rate', 0)} (+{getattr(user, 'allocated_crit_rate', 0) * self.CRIT_RATE_PER_POINT}%)\n\n"
        
        if points_info['available'] > 0:
            msg += f"💡 Hai {points_info['available']} punto/i da allocare!"
        else:
            msg += f"✨ Tutti i punti sono stati allocati!"
        
        return msg
    
    def get_total_stats(self, user):
        """
        Get total stats including base + allocated
        """
        return {
            'max_health': user.max_health,
            'health': user.health,
            'max_mana': user.max_mana,
            'mana': user.mana,
            'base_damage': user.base_damage,
            'speed': getattr(user, 'allocated_speed', 0) * self.SPEED_PER_POINT,
            'resistance': getattr(user, 'allocated_resistance', 0) * self.RESISTANCE_PER_POINT,
            'crit_rate': getattr(user, 'allocated_crit_rate', 0) * self.CRIT_RATE_PER_POINT
        }
