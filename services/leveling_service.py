from database import Database
from models.user import Utente
from services.event_dispatcher import EventDispatcher

class LevelingService:
    def __init__(self):
        self.db = Database()
        self.event_dispatcher = EventDispatcher()

    def get_xp_requirement(self, level: int) -> int:
        """
        Total cumulative EXP required to reach 'level'.
        
        New Curve:
        Approximates a balanced grind up to level 100.
        """
        if level <= 1:
            return 0

        A = 10
        p = 2.5

        return int(A * (level ** p))

    def add_chat_exp(self, user_id, amount):
        """Add chat EXP to user and return new total"""
        session = self.db.get_session()
        utente = session.query(Utente).filter_by(id_telegram=user_id).first()
        new_total = 0
        if utente:
            utente.chat_exp = (utente.chat_exp or 0) + amount
            new_total = utente.chat_exp
            session.commit()
        session.close()
        return new_total

    def add_exp_by_id(self, user_id, exp, session=None):
        """Add experience to a user by their Telegram ID and check for level-up"""
        local_session = False
        if not session:
            session = self.db.get_session()
            local_session = True
        
        utente = session.query(Utente).filter_by(id_telegram=user_id).first()
        leveled_up = False
        new_level = None
        next_level_exp = None
        
        if utente:
            current_exp = utente.exp if utente.exp is not None else 0
            utente.exp = int(current_exp) + int(exp)
            
            if utente.livello is None:
                utente.livello = 1
            
            # Check for level-up
            next_exp_req = self.get_xp_requirement(utente.livello + 1)
            
            # Loop to handle multiple level-ups
            loop_guard = 0
            while next_exp_req is not None and utente.exp >= int(next_exp_req) and loop_guard < 500:
                loop_guard += 1
                # Level up!
                utente.livello += 1
                
                # Stat Points Logic: Always Level * 2
                spent_points = (
                    (utente.allocated_health or 0) + 
                    (utente.allocated_mana or 0) + 
                    (utente.allocated_damage or 0) +
                    (utente.allocated_resistance or 0) +
                    (utente.allocated_crit or 0) +
                    (utente.allocated_speed or 0)
                )
                utente.stat_points = (utente.livello * 2) - spent_points
                
                leveled_up = True
                new_level = utente.livello
                
                # Commit intermediate state to ensure level is saved
                if local_session:
                    session.commit()
                else:
                    session.flush()
                    
                # Recalculate stats via UserService
                from services.user_service import UserService
                user_service = UserService()
                self.recalculate_level(user_id, session=session)
                user_service.recalculate_stats(user_id, session=session)
                
                # Refresh user object
                if local_session:
                    try:
                        session.refresh(utente)
                    except:
                        # Re-query if refresh fails (detached)
                        utente = session.query(Utente).filter_by(id_telegram=user_id).first()
                else:
                    # Just expire to force reload on access
                    session.expire(utente)

                # Full Heal logic
                utente.health = utente.max_health
                utente.mana = utente.max_mana
                utente.current_hp = utente.max_health
                utente.current_mana = utente.max_mana
                
                # Log level up event
                self.event_dispatcher.log_event(
                    event_type='level_up',
                    user_id=user_id,
                    value=new_level,
                    context={'exp': utente.exp},
                    session=session
                )
                
                # Check for NEXT level
                next_exp_req = self.get_xp_requirement(utente.livello + 1)
            
            # Get next level exp requirement for display
            next_level_exp = next_exp_req
            
            if local_session:
                session.commit()
                
        if local_session:
            session.close()
        
        return {
            'leveled_up': leveled_up,
            'new_level': new_level,
            'next_level_exp': next_level_exp
        }

    def add_exp(self, utente, exp):
        """Add experience to a user object"""
        return self.add_exp_by_id(utente.id_telegram, exp)

    def check_level_up(self, user_id, session=None):
        """Force check for level up (helper method)"""
        # We reuse add_exp_by_id with 0 exp to trigger the check loop
        return self.add_exp_by_id(user_id, 0, session=session)

    def recalculate_level(self, user_id, session=None):
        """Ricalcola il livello corretto a partire dall'exp totale"""
        local_session = False
        if not session:
            session = self.db.get_session()
            local_session = True

        try:
            from models.user import Utente
            u = session.query(Utente).filter_by(id_telegram=user_id).first()
            if not u or u.exp is None:
                return

            exp_total = int(u.exp)
            livello = 1

            # Trova il livello corretto dalla nuova curva
            while True:
                next_req = self.get_xp_requirement(livello + 1)
                if next_req is None or exp_total < next_req:
                    break
                livello += 1

            u.livello = livello

            # Ricalcolo punti stat disponibili
            spent_points = (
                (u.allocated_health or 0) + 
                (u.allocated_mana or 0) + 
                (u.allocated_damage or 0) +
                (u.allocated_resistance or 0) +
                (u.allocated_crit or 0) +
                (u.allocated_speed or 0)
            )
            u.stat_points = (u.livello * 2) - spent_points

            if local_session:
                session.commit()
            else:
                session.flush()

            print(f"Recalculated level for {user_id}: Livello {u.livello}, Exp {u.exp}/{self.get_xp_requirement(u.livello + 1)}")
        except Exception as e:
            print(f"Error in recalculate_level for {user_id}: {e}")
            import traceback
            traceback.print_exc()
        finally:
            if local_session:
                session.close()
