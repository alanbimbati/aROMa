from database import Database
from models.pve import Mob, Raid, RaidParticipation
from models.system import Livello
from services.user_service import UserService
from services.item_service import ItemService
import datetime
import random
import csv
from settings import PointsName

class PvEService:
    def __init__(self):
        self.db = Database()
        self.user_service = UserService()
        self.item_service = ItemService()
        self.mob_data = self.load_mob_data()
        self.boss_data = self.load_boss_data()

    def load_mob_data(self):
        """Load mob data from CSV"""
        mobs = []
        try:
            with open('data/mobs.csv', 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    mobs.append(row)
        except Exception as e:
            print(f"Error loading mobs: {e}")
        return mobs
    
    def load_boss_data(self):
        """Load boss data from CSV"""
        bosses = []
        try:
            with open('data/bosses.csv', 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    bosses.append(row)
        except Exception as e:
            print(f"Error loading bosses: {e}")
        return bosses

    def spawn_daily_mob(self):
        session = self.db.get_session()
        # Check if active mob exists
        active_mob = session.query(Mob).filter_by(is_dead=False).first()
        if active_mob:
            session.close()
            return None # Already active
        
        if not self.mob_data:
            session.close()
            return None
        
        mob_info = random.choice(self.mob_data)
        
        mob = Mob(
            name=mob_info['nome'],
            health=int(mob_info['hp']),
            max_health=int(mob_info['hp']),
            attack_damage=int(mob_info['attack_damage']),
            attack_type=mob_info['attack_type'],
            difficulty_tier=int(mob_info['difficulty'])
        )
        session.add(mob)
        session.commit()
        mob_id = mob.id
        session.close()
        return mob_id

    def attack_mob(self, user, damage, use_special=False):
        """Attack current mob"""
        session = self.db.get_session()
        mob = session.query(Mob).filter_by(is_dead=False).first()
        
        if not mob:
            session.close()
            return False, "Nessun mostro nei paraggi."
        
        # Check fatigue
        if self.user_service.check_fatigue(user):
            session.close()
            return False, "Sei troppo affaticato per combattere! Riposa."
        
        # Mob attacks back
        mob_damage = mob.attack_damage if mob.attack_damage else 10
        self.user_service.damage_health(user, mob_damage)
        
        mob.health -= damage
        msg = f"⚔️ Hai inflitto {damage} danni a {mob.name}!"
        msg += f"💥 {mob.name} ti attacca per {mob_damage} danni!"
        
        if mob.health <= 0:
            mob.health = 0
            mob.is_dead = True
            mob.killer_id = user.id_telegram
            msg += f"\n🎉 Hai ucciso {mob.name}!"
            
            # Rewards based on difficulty
            difficulty = mob.difficulty_tier if mob.difficulty_tier else 1
            xp = random.randint(30, 60) * difficulty
            wumpa = random.randint(15, 30) * difficulty
            
            self.user_service.add_exp(user, xp)
            self.user_service.add_points(user, wumpa)
            
            # Item reward
            items_data = self.item_service.load_items_from_csv()
            if items_data:
                weights = [1/item['rarita'] for item in items_data]
                reward_item = random.choices(items_data, weights=weights, k=1)[0]
                self.item_service.add_item(user.id_telegram, reward_item['nome'])
                msg += f"🏆 Ricompensa: {xp} Exp, {wumpa} {PointsName}, {reward_item['nome']}!"
            else:
                msg += f"🏆 Ricompensa: {xp} Exp, {wumpa} {PointsName}!"
        else:
            msg += f"❤️ Vita rimanente: {mob.health}/{mob.max_health}"

        session.commit()
        session.close()
        return True, msg

    def use_special_attack(self, user, target_type="mob"):
        """Use character's special attack"""
        session = self.db.get_session()
        character = session.query(Livello).filter_by(id=user.livello_selezionato).first()
        session.close()
        
        if not character or not character.special_attack_name:
            return False, "Il tuo personaggio non ha un attacco speciale!"
        
        mana_cost = character.special_attack_mana_cost
        if not self.user_service.use_mana(user, mana_cost):
            return False, f"Mana insufficiente! Serve: {mana_cost}, Hai: {user.mana}"
        
        damage = character.special_attack_damage + user.base_damage
        
        if target_type == "mob":
            success, msg = self.attack_mob(user, damage, use_special=True)
            if success:
                msg = f"✨ {character.special_attack_name}! ✨" + msg
            return success, msg
        else:  # raid
            success, msg = self.attack_raid_boss(user, damage)
            if success:
                msg = f"✨ {character.special_attack_name}! ✨" + msg
            return success, msg

    def spawn_raid_boss(self):
        session = self.db.get_session()
        active_raid = session.query(Raid).filter_by(is_active=True).first()
        if active_raid:
            session.close()
            return None
        
        if not self.boss_data:
            session.close()
            return None
        
        boss_info = random.choice(self.boss_data)
        
        raid = Raid(
            boss_name=boss_info['nome'],
            health=int(boss_info['hp']),
            max_health=int(boss_info['hp']),
            attack_damage=int(boss_info['attack_damage']),
            attack_type=boss_info['attack_type'],
            description=boss_info['description']
        )
        session.add(raid)
        session.commit()
        raid_id = raid.id
        session.close()
        return raid_id

    def attack_raid_boss(self, user, damage):
        session = self.db.get_session()
        raid = session.query(Raid).filter_by(is_active=True).first()
        
        if not raid:
            session.close()
            return False, "Nessun raid attivo."
        
        # Check fatigue
        if self.user_service.check_fatigue(user):
            session.close()
            return False, "Sei troppo affaticato! Riposa prima di combattere."
        
        # Boss attacks back (less damage per attack since it's shared)
        boss_damage = (raid.attack_damage if raid.attack_damage else 20) // 2
        self.user_service.damage_health(user, boss_damage)
        
        raid.health -= damage
        
        # Track participation
        participation = session.query(RaidParticipation).filter_by(raid_id=raid.id, user_id=user.id_telegram).first()
        if not participation:
            participation = RaidParticipation(raid_id=raid.id, user_id=user.id_telegram, damage_dealt=0)
            session.add(participation)
        
        participation.damage_dealt += damage
        msg = f"⚔️ Hai inflitto {damage} danni a {raid.boss_name}!"
        msg += f"💥 {raid.boss_name} contrattacca per {boss_damage} danni!"
        
        if raid.health <= 0:
            raid.health = 0
            raid.is_active = False
            raid.end_time = datetime.datetime.now()
            msg += f"\n🎉 {raid.boss_name} è stato sconfitto!"
            
            # Distribute rewards
            self.distribute_raid_rewards(raid.id)
            msg += "Ricompense distribuite a tutti i partecipanti!"
        else:
            msg += f"❤️ Vita Boss: {raid.health}/{raid.max_health}"
            
        session.commit()
        session.close()
        return True, msg

    def distribute_raid_rewards(self, raid_id):
        session = self.db.get_session()
        raid = session.query(Raid).filter_by(id=raid_id).first()
        parts = session.query(RaidParticipation).filter_by(raid_id=raid_id).all()
        
        if not parts:
            session.close()
            return
        
        total_damage = sum(p.damage_dealt for p in parts)
        
        # Get boss loot from data
        boss_info = next((b for b in self.boss_data if b['nome'] == raid.boss_name), None)
        if boss_info:
            TOTAL_POOL_WUMPA = int(boss_info.get('loot_wumpa', 5000))
            TOTAL_POOL_XP = int(boss_info.get('loot_exp', 1000))
        else:
            TOTAL_POOL_WUMPA = 5000
            TOTAL_POOL_XP = 1000
        
        for p in parts:
            share = p.damage_dealt / total_damage if total_damage > 0 else 0
            wumpa_reward = int(TOTAL_POOL_WUMPA * share)
            xp_reward = int(TOTAL_POOL_XP * share)
            
            user = self.user_service.get_user(p.user_id)
            if user:
                self.user_service.add_points(user, wumpa_reward)
                self.user_service.add_exp(user, xp_reward)
        
        session.close()

    def get_current_mob_status(self):
        """Get current mob info for display"""
        session = self.db.get_session()
        mob = session.query(Mob).filter_by(is_dead=False).first()
        session.close()
        
        if not mob:
            return None
        
        return {
            'name': mob.name,
            'health': mob.health,
            'max_health': mob.max_health,
            'attack': mob.attack_damage,
            'type': mob.attack_type
        }
    
    def get_current_raid_status(self):
        """Get current raid info for display"""
        session = self.db.get_session()
        raid = session.query(Raid).filter_by(is_active=True).first()
        session.close()
        
        if not raid:
            return None
        
        return {
            'name': raid.boss_name,
            'health': raid.health,
            'max_health': raid.max_health,
            'attack': raid.attack_damage,
            'description': raid.description
        }
