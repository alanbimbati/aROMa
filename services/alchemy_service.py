"""
Alchemy Service - Handle potion crafting (brewing)
"""
import csv
import os
import json
import datetime
from database import Database
from models.user import Utente
from models.alchemy import AlchemyQueue
from models.stats import UserStat
from models.resources import Resource, UserResource
from sqlalchemy import func

# Dynamic path resolution
SERVICE_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(SERVICE_DIR)

class AlchemyService:
    def __init__(self):
        self.db = Database()
        self.recipes = self.load_recipes()
    
    def load_recipes(self):
        """Load alchemy recipes from CSV"""
        recipes = {}
        try:
            csv_path = os.path.join(BASE_DIR, 'data', 'alchemy_recipes.csv')
            if os.path.exists(csv_path):
                with open(csv_path, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        recipes[row['potion_name']] = {
                            'required_resources': json.loads(row['required_resources']),
                            'crafting_time': int(row['crafting_time']),
                            'xp_gain': int(row['xp_gain'])
                        }
        except Exception as e:
            print(f"Error loading alchemy recipes: {e}")
        return recipes

    def get_recipes(self):
        return self.recipes

    def get_recipe(self, potion_name):
        return self.recipes.get(potion_name)

    def brew_potion(self, user_id, potion_name):
        """Start brewing a potion"""
        recipe = self.get_recipe(potion_name)
        if not recipe:
            return False, "Ricetta non trovata."

        session = self.db.get_session()
        try:
            # 1. Check resources
            for res_name, qty_needed in recipe['required_resources'].items():
                resource = session.query(Resource).filter_by(name=res_name).first()
                if not resource:
                    return False, f"Risorsa {res_name} non trovata nel database."
                
                user_res = session.query(UserResource).filter_by(user_id=user_id, resource_id=resource.id).first()
                if not user_res or user_res.quantity < qty_needed:
                    return False, f"Non hai abbastanza {res_name}! (Richiesti: {qty_needed})"

            # 2. Consume resources
            for res_name, qty_needed in recipe['required_resources'].items():
                resource = session.query(Resource).filter_by(name=res_name).first()
                user_res = session.query(UserResource).filter_by(user_id=user_id, resource_id=resource.id).first()
                user_res.quantity -= qty_needed

            # 3. Add to queue (Apply Guild Bonus)
            from services.guild_service import GuildService
            guild_service = GuildService()
            speed_mult = guild_service.get_laboratory_bonus(user_id)
            
            crafting_time = int(recipe['crafting_time'] / speed_mult)
            completion_time = datetime.datetime.now() + datetime.timedelta(seconds=crafting_time)
            
            new_job = AlchemyQueue(
                user_id=user_id,
                potion_name=potion_name,
                completion_time=completion_time,
                xp_gain=recipe['xp_gain'],
                status='in_progress'
            )
            session.add(new_job)
            session.commit()
            
            # Format time remaining
            finish_str = completion_time.strftime('%H:%M:%S')
            bonus_msg = ""
            if speed_mult > 1.0:
                bonus_msg = f" (Velocità x{speed_mult:.1f} grazie al Laboratorio di Gilda!)"
                
            return True, f"Inizio a bollire la tua {potion_name}! Sarà pronta alle {finish_str}.{bonus_msg}"
        except Exception as e:
            session.rollback()
            return False, f"Errore durante la produzione: {e}"
        finally:
            session.close()

    def process_queue(self):
        """Find all jobs that are done and mark as completed"""
        session = self.db.get_session()
        try:
            now = datetime.datetime.now()
            ready_jobs = session.query(AlchemyQueue).filter(
                AlchemyQueue.status == 'in_progress',
                AlchemyQueue.completion_time <= now
            ).all()
            
            completed_info = []
            for job in ready_jobs:
                completed_info.append({
                    'user_id': job.user_id,
                    'potion_name': job.potion_name
                })
                job.status = 'completed'
            
            session.commit()
            return completed_info
        except Exception as e:
            print(f"Error processing alchemy queue: {e}")
            return []
        finally:
            session.close()

    def claim_potions(self, user_id):
        """Claim all completed potions for a user"""
        self.process_queue()
        
        session = self.db.get_session()
        try:
            jobs = session.query(AlchemyQueue).filter_by(user_id=user_id, status='completed').all()
            if not jobs:
                return False, "Nessuna pozione pronta da ritirare."

            from services.item_service import ItemService
            item_service = ItemService()
            
            total_xp = 0
            potions_claimed = {}
            
            for job in jobs:
                potion_name = job.potion_name
                item_service.add_item(user_id, potion_name) # Internal session handled in ItemService? Better use same session.
                # item_service.add_item typically handles its own session. Let's assume it works or fix if needed.
                
                total_xp += job.xp_gain
                potions_claimed[potion_name] = potions_claimed.get(potion_name, 0) + 1
                job.status = 'claimed'

            # Update Alchemy XP
            self.add_alchemy_xp(user_id, total_xp, session=session)
            
            # Log events for achievements
            from services.event_dispatcher import EventDispatcher
            dispatcher = EventDispatcher()
            
            for name, qty in potions_claimed.items():
                dispatcher.log_event(
                    event_type="alchemy_brew",
                    user_id=user_id,
                    value=qty,
                    context={"potion_name": name},
                    session=session
                )
            
            session.commit()
            
            result_msg = "🧪 **Pozioni Ritirate!**\n\n"
            for name, qty in potions_claimed.items():
                result_msg += f"- {name} x{qty}\n"
            result_msg += f"\n✨ Hai guadagnato **{total_xp} XP Alchimia**!"
            
            return True, result_msg
        except Exception as e:
            session.rollback()
            return False, f"Errore nel ritiro: {e}"
        finally:
            session.close()

    def get_alchemy_info(self, user_id):
        """Get user alchemy level and XP"""
        session = self.db.get_session()
        try:
            xp_stat = session.query(UserStat).filter_by(user_id=user_id, stat_key='alchemy_xp').first()
            level_stat = session.query(UserStat).filter_by(user_id=user_id, stat_key='alchemy_level').first()
            
            return {
                "level": int(level_stat.value) if level_stat else 1, 
                "xp": int(xp_stat.value) if xp_stat else 0
            }
        finally:
            session.close()

    def add_alchemy_xp(self, user_id, amount, session=None):
        """Add XP to user's alchemy and check for level up"""
        local_session = False
        if not session:
            session = self.db.get_session()
            local_session = True
            
        try:
            info = self.get_alchemy_info(user_id)
            current_xp = info['xp']
            current_level = info['level']
            
            MAX_ALCHEMY_LEVEL = 50
            if current_level >= MAX_ALCHEMY_LEVEL:
                return False
            
            new_xp = current_xp + amount
            new_level = current_level
            
            while True:
                if new_level >= MAX_ALCHEMY_LEVEL:
                    new_level = MAX_ALCHEMY_LEVEL
                    break
                
                xp_needed = 100 * (new_level * (new_level + 1) // 2)
                if new_xp >= xp_needed:
                    new_level += 1
                else:
                    break
            
            # Update XP
            xp_entry = session.query(UserStat).filter_by(user_id=user_id, stat_key='alchemy_xp').first()
            if xp_entry:
                xp_entry.value = new_xp
            else:
                xp_entry = UserStat(user_id=user_id, stat_key='alchemy_xp', value=new_xp)
                session.add(xp_entry)
            
            # Update Level
            lvl_entry = session.query(UserStat).filter_by(user_id=user_id, stat_key='alchemy_level').first()
            if lvl_entry:
                lvl_entry.value = new_level
            else:
                lvl_entry = UserStat(user_id=user_id, stat_key='alchemy_level', value=new_level)
                session.add(lvl_entry)
            
            if local_session:
                session.commit()
            
            return new_level > current_level
        finally:
            if local_session:
                session.close()

    def get_alchemy_status(self, user_id):
        """Get current brewing queue status"""
        session = self.db.get_session()
        try:
            jobs = session.query(AlchemyQueue).filter(
                AlchemyQueue.user_id == user_id,
                AlchemyQueue.status != 'claimed'
            ).all()
            
            queue_data = []
            now = datetime.datetime.now()
            
            for job in jobs:
                time_left = (job.completion_time - now).total_seconds()
                is_ready = time_left <= 0
                
                queue_data.append({
                    'potion_name': job.potion_name,
                    'status': 'ready' if is_ready else 'brewing',
                    'time_left': max(0, int(time_left)),
                    'xp_gain': job.xp_gain
                })
                
            return queue_data
        finally:
            session.close()
