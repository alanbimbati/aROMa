import schedule
import threading
from database import Database
from models.user import Utente
from db_setup import init_database
from services.user_service import UserService
from services.leveling_service import LevelingService

class BootService:
    def __init__(self):
        self.db = Database()
        self.user_service = UserService()
        self.leveling_service = LevelingService()

    def run_startup_sequence(self, bot=None):
        """Esegue le operazioni intere di boot del sistema"""
        print("[BOOT] Starting aROMa Bot initialization sequence...")
        
        # 1. Inizializza DB (Schema + Seed)
        init_database()
        print("[BOOT] Database initialization complete.")
        
        # 2. Carica achievements (eseguito solitamente da chi detiene il tracker in main.py, 
        # ma può essere triggerato globalmente)
        from services.achievement_tracker import AchievementTracker
        tracker = AchievementTracker()
        tracker.load_from_csv()
        tracker.load_from_json()
        print("[BOOT] Achievements loaded.")
        
        # 3. Startup & clean utenti (ricalcolo livelli, stats)
        self.startup_and_clean()
        
        print("[BOOT] Initialization sequence finished successfully.")

    def startup_and_clean(self):
        """Ricalcola stats e livelli per tutti gli utenti all'avvio"""
        session = self.db.get_session()
        try:
            all_users = session.query(Utente).all()
            fixed_count = 0

            for u in all_users:
                # Fallback valori None a 0
                if u.exp is None:
                    u.exp = 0
                if u.livello is None:
                    u.livello = 1

                # Alloca punti Null-safe
                for attr in ['allocated_health', 'allocated_mana', 'allocated_damage',
                            'allocated_resistance', 'allocated_crit', 'allocated_speed']:
                    if getattr(u, attr) is None:
                        setattr(u, attr, 0)

                # Ricalcolo livello usando la nuova curva
                u.exp = min(u.exp or 0, 100000)
                self.leveling_service.recalculate_level(u.id_telegram, session=session)

                # Ricalcolo stats
                self.user_service.recalculate_stats(u.id_telegram, session=session)

                # Controllo livello massimo personaggio selezionato
                from services.character_loader import get_character_loader
                loader = get_character_loader()

                selected_char_id = u.livello_selezionato
                if selected_char_id is not None:
                    char_info = loader.get_character_by_id(selected_char_id)
                    if char_info:
                        required_level = char_info.get('livello', 1)
                        if u.livello < required_level:
                            print(f"[BOOT] User {u.id_telegram} level ({u.livello}) below character requirement ({required_level}). Resetting to Chocobo (1).")
                            u.livello_selezionato = 1 # Chocobo ID
                            
                            # Recalculate stats with the new character
                            self.user_service.recalculate_stats(u.id_telegram, session=session)

                fixed_count += 1

            session.commit()
            print(f"[BOOT] Cleaned stats and levels for {fixed_count} users.")
        except Exception as e:
            session.rollback()
            print(f"[BOOT] Error in startup_and_clean: {e}")
        finally:
            session.close()

