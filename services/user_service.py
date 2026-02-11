from database import Database
from sqlalchemy.sql import func
from models.user import Utente, Admin
from models.system import Livello
from models.game import GiocoUtente
from services.character_loader import get_character_loader
from sqlalchemy import desc, asc, text, inspect
from sqlalchemy.orm import defer
import datetime
from dateutil.relativedelta import relativedelta
from settings import PointsName
from services.event_dispatcher import EventDispatcher
from services.equipment_service import EquipmentService

class UserService:
    # Class-level dictionary to track activity with timestamps
    # Format: {(user_id, chat_id): timestamp}
    _recent_activities = {}
    _last_db_updates = {} # {user_id: timestamp} - Track when we wrote to DB last
    _exp_required_column_exists = None  # Cache per verificare se la colonna esiste

    def __init__(self):
        self.db = Database()
        self.recent_activities = UserService._recent_activities
        self.last_db_updates = UserService._last_db_updates
        self.event_dispatcher = EventDispatcher()
        self.equipment_service = EquipmentService()

    def get_user_by_username(self, username):
        """Get user by username (case insensitive, handles @ prefix)"""
        if not username: return None
        
        # Strip @ if provided to check both versions
        clean_name = username[1:] if username.startswith('@') else username
        
        session = self.db.get_session()
        try:
            # Try exact match, then match with @, then match without @
            user = session.query(Utente).filter(
                (func.lower(Utente.username) == username.lower()) |
                (func.lower(Utente.username) == clean_name.lower()) |
                (func.lower(Utente.username) == f"@{clean_name}".lower())
            ).first()
            return user
        finally:
            session.close()
    
    def _check_exp_required_column(self):
        """Verifica se la colonna exp_required esiste nel database"""
        if UserService._exp_required_column_exists is not None:
            return UserService._exp_required_column_exists
        
        try:
            inspector = inspect(self.db.engine)
            columns = [col['name'] for col in inspector.get_columns('livello')]
            UserService._exp_required_column_exists = 'exp_required' in columns
            return UserService._exp_required_column_exists
        except Exception:
            # In caso di errore, assumiamo che non esista
            UserService._exp_required_column_exists = False
            return False
    
    def _get_livello_by_level(self, session, livello_num):
        """Ottiene un Livello per numero, gestendo l'assenza di exp_required"""
        if self._check_exp_required_column():
            # La colonna esiste, usa la query normale
            try:
                return session.query(Livello).filter_by(livello=livello_num).first()
            except Exception:
                # Se fallisce, ricarica la cache e riprova
                UserService._exp_required_column_exists = None
                return self._get_livello_by_level(session, livello_num)
        else:
            # La colonna non esiste, usa una query raw SQL che non la include
            try:
                # Query che seleziona solo le colonne che esistono (escludendo exp_required)
                result = session.execute(
                    text("""
                        SELECT id, livello, nome, lv_premium, price, 
                               COALESCE(elemental_type, 'Normal') as elemental_type,
                               COALESCE(crit_chance, 5) as crit_chance,
                               COALESCE(crit_multiplier, 1.5) as crit_multiplier,
                               required_character_id, special_attack_name, 
                               COALESCE(special_attack_damage, 0) as special_attack_damage,
                               COALESCE(special_attack_mana_cost, 0) as special_attack_mana_cost,
                               image_path, telegram_file_id, description, 
                               COALESCE(character_group, 'General') as character_group
                        FROM livello 
                        WHERE livello = :livello 
                        LIMIT 1
                    """),
                    {"livello": livello_num}
                ).first()
                
                if result:
                    # Crea un oggetto Livello con i dati ottenuti
                    livello = Livello()
                    livello.id = result[0]
                    livello.livello = result[1]
                    livello.nome = result[2]
                    livello.lv_premium = result[3] if result[3] is not None else 0
                    livello.price = result[4] if result[4] is not None else 0
                    livello.elemental_type = result[5]
                    livello.crit_chance = result[6]
                    livello.crit_multiplier = result[7]
                    livello.required_character_id = result[8]
                    livello.special_attack_name = result[9]
                    livello.special_attack_damage = result[10]
                    livello.special_attack_mana_cost = result[11]
                    livello.image_path = result[12]
                    livello.telegram_file_id = result[13]
                    livello.description = result[14]
                    livello.character_group = result[15]
                    livello.exp_required = None  # Non esiste ancora, verrà calcolato con formula
                    return livello
            except Exception as e:
                # Se anche la query raw fallisce, ritorna None
                print(f"Errore nel recupero del livello: {e}")
            return None

    def track_activity(self, user_id, chat_id=None):
        """Track user activity for mob targeting with timestamp"""
        import datetime
        try:
            user_id = int(user_id)
            if chat_id is not None:
                chat_id = int(chat_id)
        except (ValueError, TypeError):
            pass
            
        now = datetime.datetime.now()
        key = (user_id, chat_id)
        self.recent_activities[key] = now
        
        try:
            # Throttled DB update (once per hour per user)
            last_db_upd = self.last_db_updates.get(user_id)
            if not last_db_upd or (now - last_db_upd).total_seconds() > 3600:
                self._update_last_activity_db(user_id, now)
                self.last_db_updates[user_id] = now
                
            print(f"[DEBUG] track_activity: user_id={user_id}, chat_id={chat_id}")
            
            # PERIODIC MEMBERSHIP CHECK (1% chance to check on activity)
            import random
            if random.random() < 0.01:
                if not self.check_group_membership(user_id):
                    self.delete_user_data(user_id)
                    
        except Exception as e:
            print(f"[ERROR] track_activity fallback failed: {e}")

    def _update_last_activity_db(self, user_id, timestamp):
        """Update last_activity in database"""
        session = self.db.get_session()
        try:
            from models.user import Utente
            session.query(Utente).filter_by(id_telegram=user_id).update(
                {'last_activity': timestamp}
            )
            session.commit()
        except Exception as e:
            print(f"[ERROR] Failed to update last_activity for {user_id}: {e}")
            session.rollback()
        finally:
            session.close()
        
    def check_group_membership(self, user_id):
        """
        Verify if user is a member of the official or test group.
        Returns True if member of at least one, False otherwise.
        """
        import main
        from settings import AROMA_GRUPPO, TEST_GRUPPO
        
        if not hasattr(main, 'bot'):
            return True # Cannot check, assume OK to avoid accidental deletion
            
        # Try Official Group
        try:
            member = main.bot.get_chat_member(AROMA_GRUPPO, user_id)
            if member.status in ['member', 'administrator', 'creator']:
                return True
        except Exception as e:
            # "chat not found" or "user not found" are expected if not in group
            pass
            
        # Try Test Group
        try:
            member = main.bot.get_chat_member(TEST_GRUPPO, user_id)
            if member.status in ['member', 'administrator', 'creator']:
                return True
        except Exception as e:
            pass
            
        return False

    def delete_user_data(self, user_id, ignore_activity=False):
        """
        Permanently delete ALL data associated with a user ID across all tables.
        This is used for cleaning up users who are no longer in the required groups.
        """
        import datetime
        from dateutil.relativedelta import relativedelta
        
        session = self.db.get_session()
        try:
            from models.user import Utente
            user = session.query(Utente).filter_by(id_telegram=user_id).first()
            
            if user and not ignore_activity:
                # 6-month inactivity safeguard
                six_months_ago = datetime.datetime.now() - relativedelta(months=6)
                last_act = user.last_activity
                
                # If last_activity is None, we assume it's old (or pre-tracking)
                if last_act and last_act > six_months_ago:
                    print(f"[CLEANUP] Skipping deletion for active user {user_id} (Last activity: {last_act})")
                    return False

            print(f"[CLEANUP] Starting data deletion for user {user_id}...")
            # Import models inside to avoid circular imports
            from models.resources import UserResource, UserRefinedMaterial, RefineryQueue
            from models.stats import UserStat
            from models.achievements import UserAchievement, GameEvent
            from models.equipment import UserEquipment
            from models.crafting import CraftingQueue
            from models.game import GiocoUtente
            from models.user import Utente
            from models.guild import GuildMember, Guild
            from models.combat import CombatParticipation
            from models.pve import RaidParticipation
            from models.skins import UserSkin
            
            # 1. Combat & Participation
            session.query(CombatParticipation).filter_by(user_id=user_id).delete()
            session.query(RaidParticipation).filter_by(user_id=user_id).delete()
            
            # 2. Guilds
            # First, check if user is a leader of any guild. 
            # If so, we may need to delete the guild or the leader FK will block.
            guilds_led = session.query(Guild).filter_by(leader_id=user_id).all()
            for g in guilds_led:
                # To delete a guild, we must first delete all its members and other dependents
                session.query(GuildMember).filter_by(guild_id=g.id).delete()
                # Deleting the guild itself
                session.delete(g)
            
            # Now delete membership if they are just a member
            session.query(GuildMember).filter_by(user_id=user_id).delete()
            
            # 3. Crafting & Resources
            session.query(UserResource).filter_by(user_id=user_id).delete()
            session.query(UserRefinedMaterial).filter_by(user_id=user_id).delete()
            session.query(RefineryQueue).filter_by(user_id=user_id).delete()
            session.query(CraftingQueue).filter_by(user_id=user_id).delete()
            
            # 4. Stats, Achievements, Skins
            session.query(UserStat).filter_by(user_id=user_id).delete()
            session.query(UserAchievement).filter_by(user_id=user_id).delete()
            session.query(GameEvent).filter_by(user_id=user_id).delete()
            session.query(UserSkin).filter_by(user_id=user_id).delete()
            
            # 5. Equipment & Items
            session.query(UserEquipment).filter_by(user_id=user_id).delete()
            
            # Optional tables (try-except as they might be newer or in different modules)
            try:
                from models.inventory import Inventory
                session.query(Inventory).filter_by(user_id=user_id).delete()
            except: pass
            
            try:
                from models.items import UserItem
                session.query(UserItem).filter_by(user_id=user_id).delete()
            except: pass

            try:
                from models.character_ownership import UserCharacter
                session.query(UserCharacter).filter_by(user_id=user_id).delete()
            except: pass
            
            # 6. Core User Data
            session.query(GiocoUtente).filter_by(id_telegram=user_id).delete()
            session.query(Utente).filter_by(id_telegram=user_id).delete()
            
            session.commit()
            print(f"[CLEANUP] Successfully deleted all data for user {user_id}")
            return True
        except Exception as e:
            print(f"[CLEANUP] [ERROR] Failed to delete data for {user_id}: {e}")
            import traceback
            traceback.print_exc()
            session.rollback()
            return False
        finally:
            session.close()
        
    def get_recent_users(self, chat_id=None, minutes=30):
        """Get users active within the last N minutes, sorted by recency (most recent first)"""
        import datetime
        cutoff = datetime.datetime.now() - datetime.timedelta(minutes=minutes)
        
        try:
            if chat_id is not None:
                chat_id = int(chat_id)
        except (ValueError, TypeError):
            pass

        # Filter by chat_id and time, then sort by timestamp (most recent first)
        recent = []
        for (uid, cid), timestamp in self.recent_activities.items():
            if timestamp >= cutoff:
                # Ensure cid is int for comparison if chat_id is int
                try:
                    if cid is not None: cid = int(cid)
                except: pass
                
                if chat_id is None or cid == chat_id:
                    recent.append((uid, timestamp))
        
        print(f"[DEBUG] get_recent_users: found {len(recent)} users")
        # Sort by timestamp descending (most recent first)
        recent.sort(key=lambda x: x[1], reverse=True)
        return [uid for uid, _ in recent]

    def get_user(self, target, session=None):
        local_session = False
        if not session:
            session = self.db.get_session()
            local_session = True
            
        utente = None
        target = str(target)

        # Check if it's a digit (ID) first, but only if it doesn't start with @
        # Because a username could potentially be all digits? Unlikely for Telegram but possible if not starting with @?
        # Telegram usernames must have at least 5 chars and contain letters, numbers or underscores.
        # IDs are integers.
        
        is_username_search = False
        if target.startswith('@'):
            target = target[1:]
            is_username_search = True
        elif not target.isdigit():
            is_username_search = True
            
        if is_username_search:
            # Case-insensitive search, handling both "username" and "@username" in DB
            from sqlalchemy import func, or_
            target_lower = target.lower()
            utente = session.query(Utente).filter(
                or_(
                    func.lower(Utente.username) == target_lower,
                    func.lower(Utente.username) == f"@{target_lower}"
                )
            ).first()
        else:
            utente = session.query(Utente).filter_by(id_telegram=int(target)).first()
            
        if local_session:
            session.close()
        return utente

    def get_users(self):
        session = self.db.get_session()
        users = session.query(Utente).all()
        session.close()
        return users

    def create_user(self, id_telegram, username, name, last_name):
        session = self.db.get_session()
        exist = session.query(Utente).filter_by(id_telegram=id_telegram).first()
        if exist is None:
            try:
                utente = Utente()
                utente.username = username
                utente.nome = name
                utente.id_telegram = id_telegram
                utente.cognome = last_name
                utente.vita = 50
                utente.exp = 0
                utente.livello = 1
                utente.points = 5
                utente.premium = 0
                utente.livello_selezionato = 1
                utente.start_tnt = datetime.datetime.now() + relativedelta(month=1)
                utente.end_tnt = datetime.datetime.now()
                utente.scadenza_premium = datetime.datetime.now()
                utente.abbonamento_attivo = 0
                utente.stat_points = 2 # Level 1 * 2
                utente.shield_hp = 0
                session.add(utente)
                session.commit()
            except:
                session.rollback()
                raise
            finally:
                session.close()
            return False
        elif exist.username != username:
            self.update_user(id_telegram, {'username': username, 'nome': name, 'cognome': last_name})
        session.close()
        return True

    def update_user(self, chatid, kwargs, session=None):
        close_session = False
        if session is None:
            session = self.db.get_session()
            close_session = True
            
        try:
            utente = session.query(Utente).filter_by(id_telegram=chatid).first()
            if utente:
                for key, value in kwargs.items():
                    setattr(utente, key, value)
                if close_session:
                    session.commit()
                # If shared session, caller commits
        except Exception as e:
            if close_session:
                session.rollback()
            raise e
        finally:
            if close_session:
                session.close()

    def add_points(self, utente, points):
        """Add points to a user object"""
        try:
            # Use add_points_by_id to ensure consistent logic (daily reset, etc)
            self.add_points_by_id(utente.id_telegram, points)
        except Exception as e:
            print(f"[ERROR] add_points failed: {e}")

    def check_daily_reset(self, utente):
        """Check if daily limits need to be reset"""
        now = datetime.datetime.now()
        last_reset = utente.last_wumpa_reset
        
        # If last reset was not today (or never), reset
        if not last_reset or last_reset.date() < now.date():
            utente.daily_wumpa_earned = 0
            utente.last_wumpa_reset = now
            return True
        return False

    def add_points_by_id(self, user_id, points, is_drop=False, session=None):
        """
        Add points to a user by their Telegram ID
        Args:
            user_id: Telegram ID
            points: Amount of Wumpa to add
            is_drop: If True, counts towards daily cap
            session: Optional database session
        """
        local_session = False
        if not session:
            session = self.db.get_session()
            local_session = True
            
        utente = session.query(Utente).filter_by(id_telegram=user_id).first()
        if utente:
            # Check for daily reset
            self.check_daily_reset(utente)
            
            current_points = utente.points if utente.points is not None else 0
            utente.points = int(current_points) + int(points)
            
            # Track daily earnings if it's a drop
            if is_drop:
                utente.daily_wumpa_earned = (utente.daily_wumpa_earned or 0) + int(points)
            
            if local_session:
                session.commit()
            
            # NEW: Log point gain event
            self.event_dispatcher.log_event(
                event_type='point_gain',
                user_id=user_id,
                value=points,
                context={'is_drop': is_drop, 'new_total': utente.points}
            )
        
        if local_session:
            session.close()

    def add_exp(self, utente, exp):
        """Add experience to a user object"""
        try:
            # Use add_exp_by_id to handle level-ups and session management
            self.add_exp_by_id(utente.id_telegram, exp)
        except Exception as e:
            print(f"[ERROR] add_exp failed: {e}")

    # ========== Premium Currency (Cristalli aROMa) Methods ==========
    
    def add_cristalli(self, user_id, amount, session=None):
        """Add Cristalli aROMa premium currency to user"""
        local_session = False
        if not session:
            session = self.db.get_session()
            local_session = True
            
        try:
            utente = session.query(Utente).filter_by(id_telegram=user_id).first()
            if utente:
                current = utente.cristalli_aroma if utente.cristalli_aroma is not None else 0
                utente.cristalli_aroma = int(current) + int(amount)
                
                if local_session:
                    session.commit()
                    
                print(f"[CRISTALLI] Added {amount} Cristalli aROMa to user {user_id}. New balance: {utente.cristalli_aroma}")
                return True
            return False
        except Exception as e:
            print(f"[ERROR] add_cristalli failed: {e}")
            if local_session:
                session.rollback()
            return False
        finally:
            if local_session:
                session.close()
    
    def remove_cristalli(self, user_id, amount, session=None):
        """Remove Cristalli aROMa premium currency from user (for purchases)"""
        local_session = False
        if not session:
            session = self.db.get_session()
            local_session = True
            
        try:
            utente = session.query(Utente).filter_by(id_telegram=user_id).first()
            if utente:
                current = utente.cristalli_aroma if utente.cristalli_aroma is not None else 0
                if current < amount:
                    print(f"[CRISTALLI] Insufficient balance. Current: {current}, Required: {amount}")
                    return False
                    
                utente.cristalli_aroma = int(current) - int(amount)
                
                if local_session:
                    session.commit()
                    
                print(f"[CRISTALLI] Removed {amount} Cristalli aROMa from user {user_id}. New balance: {utente.cristalli_aroma}")
                return True
            return False
        except Exception as e:
            print(f"[ERROR] remove_cristalli failed: {e}")
            if local_session:
                session.rollback()
            return False
        finally:
            if local_session:
                session.close()
    
    def get_cristalli_balance(self, user_id):
        """Get current Cristalli aROMa balance for a user"""
        session = self.db.get_session()
        try:
            utente = session.query(Utente).filter_by(id_telegram=user_id).first()
            if utente:
                return utente.cristalli_aroma if utente.cristalli_aroma is not None else 0
            return 0
        except Exception as e:
            print(f"[ERROR] get_cristalli_balance failed: {e}")
            return 0
        finally:
            session.close()

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
            
            # Helper to get exp required from CharacterLoader (source of truth)
            def get_exp_required_for_level(level):
                # We use a consistent quadratic curve (100 * level^2) for levels >= 45.
                # This prevents extreme spikes found in some legacy character data
                # and ensures that difficulty continues to scale as requested.
                loader = get_character_loader()
                chars = loader.get_characters_by_level(level)
                if chars:
                    # Always prioritize CSV value if available (e.g. Inkling Lv 53 = 135k)
                    csv_exp = chars[0].get('exp_required')
                    if csv_exp and csv_exp > 0:
                         return csv_exp
                
                # We use a consistent quadratic curve (100 * level^2) for levels >= 45 IF not in CSV.
                # This prevents extreme spikes found in some legacy character data
                # and ensures that difficulty continues to scale as requested.
                if level >= 45:
                    return 100 * (level ** 2)
                
                # Fallback to DB if loader fails
                level_data = self._get_livello_by_level(session, level)
                if level_data and hasattr(level_data, 'exp_required') and level_data.exp_required is not None:
                    return level_data.exp_required
                
                # Final fallback: Formula
                return 100 * (level ** 2)

            # Check for level-up
            next_exp_req = get_exp_required_for_level(utente.livello + 1)
            
            # Loop to handle multiple level-ups
            loop_guard = 0
            while next_exp_req is not None and utente.exp >= next_exp_req and loop_guard < 100:
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
                    
                # Recalculate stats
                self.recalculate_stats(user_id, session=session)
                
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
                next_exp_req = get_exp_required_for_level(utente.livello + 1)
            
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

    def check_level_up(self, user_id, session=None):
        """Force check for level up (helper method)"""
        # We reuse add_exp_by_id with 0 exp to trigger the check loop
        return self.add_exp_by_id(user_id, 0, session=session)
        
        return {
            'leveled_up': leveled_up,
            'new_level': new_level,
            'next_level_exp': next_level_exp
        }

    def is_admin(self, utente):
        session = self.db.get_session()
        if utente:
            exist = session.query(Admin).filter_by(id_telegram=utente.id_telegram).first()
            session.close()
            return False if exist is None else True
        else:
            session.close()
            return False

    def info_user(self, utente_sorgente):
        """Get user profile info"""
        session = self.db.get_session()
        utente = session.query(Utente).filter_by(id_telegram=utente_sorgente.id_telegram).first()
        
        if not utente:
            # Create if not exists (should be handled elsewhere but safe fallback)
            # For info command, usually user exists.
            session.close()
            return "Utente non trovato."
            
        # Get active transformation
        from services.transformation_service import TransformationService
        trans_service = TransformationService()
        active_trans = trans_service.get_active_transformation(utente_sorgente) # Use object with ID
        trans_bonuses = trans_service.get_transformation_bonuses(utente_sorgente)
        
        trans_text = ""
        if active_trans:
            trans_text = f"\n🔥 **Trasformazione**: {active_trans.transformation_name}"
            
        # Calculate stats with bonuses
        max_hp = utente.max_health + trans_bonuses.get('health', 0)
        max_mana = utente.max_mana + trans_bonuses.get('mana', 0)
        dmg = utente.base_damage + trans_bonuses.get('damage', 0)
        
        msg = f"👤 **Profilo di {utente.nome}**\n"
        msg += f"🏅 Livello: {utente.livello}\n"
        msg += f"✨ Exp: {utente.exp}\n"
        msg += f"❤️ Vita: {utente.current_hp}/{max_hp}\n"
        msg += f"💙 Mana: {utente.current_mana}/{max_mana}\n"
        msg += f"⚔️ Danno: {dmg}\n"
        msg += f"🛡️ Difesa: {utente.resistance}\n"
        msg += f"⚡ Velocità: {utente.speed}\n"
        msg += f"🍀 Critico: {utente.crit_chance}%\n"
        msg += f"🍑 {PointsName}: {utente.points}\n"
        msg += f"💎 Punti Stat: {utente.stat_points}\n"
        msg += trans_text
        
        # Guild Info
        from services.guild_service import GuildService
        guild_service = GuildService()
        guild = guild_service.get_user_guild(utente.id_telegram)
        if guild:
            msg += f"\n🏰 **Gilda**: {guild['name']} ({guild['role']})\n"
        
        session.close()
        return msg

    def allocate_stat_point(self, utente, stat_type, session=None):
        """Allocate a stat point to HP, Mana, Damage, Resistance, Crit, or Speed"""
        if utente.stat_points <= 0:
            return False, "Non hai punti statistica disponibili!"
        
        updates = {'stat_points': utente.stat_points - 1}
        msg = ""
        
        if stat_type == "health":
            updates['allocated_health'] = (utente.allocated_health or 0) + 1
            msg = "Max Health +10!"
        elif stat_type == "mana":
            updates['allocated_mana'] = (utente.allocated_mana or 0) + 1
            msg = "Max Mana +5!"
        elif stat_type == "damage":
            updates['allocated_damage'] = (utente.allocated_damage or 0) + 1
            msg = "Base Damage +2!"
        elif stat_type == "resistance":
            # Cap check handled in recalculate, but good to check here too to avoid wasting point
            current_resistance = getattr(utente, 'resistance', 0) or 0
            if current_resistance >= 75:
                return False, "⚠️ Resistenza massima raggiunta (75%)!"
            updates['allocated_resistance'] = (utente.allocated_resistance or 0) + 1
            msg = "Resistenza +1%!"
        elif stat_type == "crit":
            updates['allocated_crit'] = (utente.allocated_crit or 0) + 1
            msg = "Critico +1%!"
        elif stat_type == "speed":
            updates['allocated_speed'] = (utente.allocated_speed or 0) + 1
            msg = "Velocità +1!"
        else:
            return False, "Statistica non valida!"
        
        self.update_user(utente.id_telegram, updates, session=session)
        self.recalculate_stats(utente.id_telegram, session=session)
        
        return True, msg
    
    def reset_stats(self, utente, paid=True):
        """Reset stat allocations (costs Wumpa if not free)"""
        RESET_COST = 500
        
        if paid and utente.points < RESET_COST:
            return False, f"Non hai abbastanza {PointsName}! Costo: {RESET_COST}"
        
        # Calculate stats to refund (including new stats)
        points_to_refund = (
            (utente.allocated_health or 0) + 
            (utente.allocated_mana or 0) + 
            (utente.allocated_damage or 0) +
            (utente.allocated_resistance or 0) +
            (utente.allocated_crit or 0) +
            (utente.allocated_speed or 0)
        )
        
        # Reset to base values (matching new get_projected_stats logic)
        level = utente.livello or 1
        
        from services.character_loader import get_character_loader
        character = get_character_loader().get_character_by_id(utente.livello_selezionato)
        
        # System base + character bonuses + level scaling
        base_h = 20 + (level - 1) * 2
        base_m = 20 + (level - 1) * 1
        base_d = 5 + (level - 1) * 0.5
        
        if character:
            base_h += character.get('bonus_health', 0)
            base_m += character.get('bonus_mana', 0)
            base_d += character.get('bonus_damage', 0)
            res = character.get('bonus_resistance', 0)
            crit = character.get('crit_chance', 5) + character.get('bonus_crit', 0)
            speed = character.get('bonus_speed', 0)  # Only bonus from character
        else:
            res = 0
            crit = 5
            speed = 0  # No character = no bonus

        updates = {
            'max_health': int(base_h),
            'max_mana': int(base_m),
            'base_damage': int(base_d),
            'allocated_health': 0,
            'allocated_mana': 0,
            'allocated_damage': 0,
            'allocated_resistance': 0,
            'allocated_crit': 0,
            'allocated_speed': 0,
            'resistance': res,
            'crit_chance': crit,
            'speed': speed,
            'stat_points': utente.livello * 2
        }
        
        if paid:
            updates['points'] = utente.points - RESET_COST
        
        self.update_user(utente.id_telegram, updates)
        
        # Recalculate to ensure equipment stats are re-applied (though they shouldn't change, base stats did)
        self.recalculate_stats(utente.id_telegram)
        
        return True, f"Statistiche resettate! {points_to_refund} punti restituiti."

    def validate_and_fix_user_stats(self):
        """Startup check to reset stats for users and sync with current logic/data"""
        print("[STARTUP] Validating and syncing user statistics...")
        session = self.db.get_session()
        try:
            users = session.query(Utente).all()
            print(f"[STARTUP] Processing {len(users)} users...")
            
            for user in users:
                if not user.livello:
                    continue
                
                # 1. Total allowed points: Level * 2
                allowed_total = user.livello * 2
                
                # Current allocated points
                allocated = (
                    (user.allocated_health or 0) +
                    (user.allocated_mana or 0) +
                    (user.allocated_damage or 0) +
                    (user.allocated_resistance or 0) +
                    (user.allocated_crit or 0) +
                    (user.allocated_speed or 0)
                )
                
                # Current available points
                available = user.stat_points or 0
                
                # Total they actually HAVE
                actual_total = allocated + available
                
                # If they have too many points, reset them
                if actual_total > allowed_total:
                    print(f"[FIX] User {user.id_telegram} ({user.nome}) has {actual_total} pts, but level {user.livello} only allows {allowed_total}. Resetting allocations...")
                    user.allocated_health = 0
                    user.allocated_mana = 0
                    user.allocated_damage = 0
                    user.allocated_resistance = 0
                    user.allocated_crit = 0
                    user.allocated_speed = 0
                    user.stat_points = allowed_total
                    session.flush()

                # 2. Mandatory synchronization with current logic/CSV data
                # This ensures that if we changed a character bonus or speed formula, 
                # all users are updated immediately on startup.
                try:
                    self.recalculate_stats(user.id_telegram, session=session)
                except Exception as e:
                    print(f"[ERROR] Recalculate failed for user {user.id_telegram}: {e}")
            
            session.commit()
            print("[STARTUP] Stat validation and sync complete.")
                
        except Exception as e:
            print(f"[ERROR] validate_and_fix_user_stats: {e}")
            session.rollback()
        finally:
            session.close()

    def get_projected_stats(self, utente, override_character_id=None, session=None):
        """
        Calculate total stats for a user, optionally overriding the character.
        Returns a dict of final stats.
        """
        # 1. System Base Stats (Matching model defaults for level 1)
        level = utente.livello or 1
        base_hp = 100
        base_mana = 50
        base_dmg = 10
        base_res = 0
        base_crit = 0 
        base_speed = 0 
        
        # 2. Character Stats & Bonuses
        from services.character_loader import get_character_loader
        char_loader = get_character_loader()
        
        # Use override ID if provided, otherwise current user selection
        char_id = override_character_id if override_character_id is not None else utente.livello_selezionato
        character = char_loader.get_character_by_id(char_id)
        
        char_level = 1
        if character:
            char_level = character.get('livello', 1)
            # Use character base values
            base_hp += character.get('bonus_health', 0)
            base_mana += character.get('bonus_mana', 0)
            base_dmg += character.get('bonus_damage', 0)
            base_res += character.get('bonus_resistance', 0)
            
            # Use character specific values for speed and crit
            base_crit = character.get('crit_chance', 0) + character.get('bonus_crit', 0)
            base_speed = character.get('bonus_speed', 0)  # Only bonus from character
        
        # 3. Allocations
        # Scaling: 1 point = 10 HP, 5 Mana, 2 DMG, 1 Res, 1 Crit, 1 Speed
        alloc_hp = (utente.allocated_health or 0) * 10
        alloc_mana = (utente.allocated_mana or 0) * 5
        alloc_dmg = (utente.allocated_damage or 0) * 2
        alloc_res = (utente.allocated_resistance or 0) * 1
        alloc_crit = (utente.allocated_crit or 0) * 1
        alloc_speed = (utente.allocated_speed or 0) * 1
        
        # Core Formula: System Base + Character Bonuses + Allocations
        total_hp = base_hp + alloc_hp
        total_mana = base_mana + alloc_mana
        total_dmg = base_dmg + alloc_dmg
        total_res = base_res + alloc_res
        total_crit = base_crit + alloc_crit
        total_speed = base_speed + alloc_speed
        
        # Level scaling (Automatic growth to match game difficulty)
        total_hp += (level - 1) * 2
        total_mana += (level - 1) * 2
        total_dmg += (level - 1) * 1
        
        total_dmg = int(total_dmg) # Ensure integer
        
        # 4. Equipment Bonuses
        # We need to calculate this. equip_service needs session?
        # calculate_equipment_stats uses a new session if none provided, 
        # but here we might pass a user object detached or attached.
        # Ideally we fetch fresh equip stats for the user ID.
        equip_stats = self.equipment_service.calculate_equipment_stats(utente.id_telegram, session=session)
        
        total_hp += equip_stats.get('max_health', 0)
        total_mana += equip_stats.get('max_mana', 0)
        total_dmg += equip_stats.get('base_damage', 0)
        total_res += equip_stats.get('resistance', 0)
        total_crit += equip_stats.get('crit_chance', 0)
        total_speed += equip_stats.get('speed', 0)
        
        # 5. Transformation Bonuses
        try:
            from services.transformation_service import TransformationService
            trans_service = TransformationService()
            trans_bonuses = trans_service.get_transformation_bonuses(utente, session=session)
            
            total_hp += trans_bonuses.get('health', 0)
            total_mana += trans_bonuses.get('mana', 0)
            total_dmg += trans_bonuses.get('damage', 0)
        except Exception as e:
            print(f"Error applying transformation bonuses in get_projected_stats: {e}")
            
        # 6. Caps
        total_res = min(total_res, 75)
        
        return {
            'max_health': int(total_hp),
            'max_mana': int(total_mana),
            'base_damage': int(total_dmg),
            'resistance': int(total_res),
            'crit_chance': int(total_crit),
            'speed': int(total_speed)
        }

    def recalculate_stats(self, user_id, session=None):
        """Recalculate total stats (Base + Allocations + Equipment)"""
        local_session = False
        if not session:
            session = self.db.get_session()
            local_session = True
            
        try:
            utente = session.query(Utente).filter_by(id_telegram=user_id).first()
            if not utente:
                if local_session:
                    session.close()
                return

            # Use projected stats (no override)
            stats = self.get_projected_stats(utente, session=session)
            
            # Update User
            utente.max_health = stats['max_health']
            utente.max_mana = stats['max_mana']
            utente.base_damage = stats['base_damage']
            utente.resistance = stats['resistance']
            utente.crit_chance = stats['crit_chance']
            utente.speed = stats['speed']
            
            # Ensure current values don't exceed max
            if utente.health is None or utente.health > utente.max_health:
                utente.health = utente.max_health
            
            if utente.mana is None or utente.mana > utente.max_mana:
                utente.mana = utente.max_mana
            
            # Handle current_hp/mana logic for combat
            if utente.current_hp is None or utente.current_hp > utente.max_health:
                utente.current_hp = utente.max_health
                
            if utente.current_mana is None or utente.current_mana > utente.max_mana:
                utente.current_mana = utente.max_mana
                
            print(f"Recalculated stats for {user_id}: HP {utente.max_health}, Dmg {utente.base_damage}")
            
            if local_session:
                session.commit()
            else:
                session.flush()
        except Exception as e:
            print(f"Error recalculating stats: {e}")
            import traceback
            traceback.print_exc()
            if local_session:
                session.rollback()
        finally:
            if local_session:
                session.close()

    def equip_item(self, user_id, user_item_id):
        """Equip item and update stats"""
        success, msg = self.equipment_service.equip_item(user_id, user_item_id)
        if success:
            self.recalculate_stats(user_id)
        return success, msg

    def unequip_item(self, user_id, user_item_id):
        """Unequip item and update stats"""
        success, msg = self.equipment_service.unequip_item(user_id, user_item_id)
        if success:
            self.recalculate_stats(user_id)
        return success, msg
    def start_resting(self, user_id, session=None):
        """Start resting in the public inn"""
        local_session = False
        if not session:
            session = self.db.get_session()
            local_session = True
            
        try:
            user = session.query(Utente).filter_by(id_telegram=user_id).first()
            if not user:
                return False, "Utente non trovato."
            
            if user.resting_since:
                return False, "Stai già riposando!"
                
            user.resting_since = datetime.datetime.now()
            if local_session:
                session.commit()
            else:
                session.flush()
            return True, "Hai iniziato a riposare! Usa /inn per controllare il recupero o smettere di riposare."
        except Exception as e:
            if local_session:
                session.rollback()
            raise e
        finally:
            if local_session:
                session.close()

    def get_resting_status(self, user_id, session=None, recovery_multiplier=1.0):
        """Check how much HP/Mana would be recovered if resting stopped now"""
        local_session = False
        if not session:
            session = self.db.get_session()
            local_session = True
            
        try:
            user = session.query(Utente).filter_by(id_telegram=user_id).first()
            if not user or not user.resting_since:
                return None
                
            now = datetime.datetime.now()
            elapsed_minutes = int((now - user.resting_since).total_seconds() / 60)
            
            # Base: 1 HP and 1 Mana per minute
            # Apply multiplier
            hp_gain_per_min = 1.0 * recovery_multiplier
            mana_gain_per_min = 1.0 * recovery_multiplier
            
            total_hp_gain = int(elapsed_minutes * hp_gain_per_min)
            total_mana_gain = int(elapsed_minutes * mana_gain_per_min)
            
            current_hp = user.current_hp if user.current_hp is not None else user.health
            hp_to_recover = min(total_hp_gain, user.max_health - current_hp)
            mana_to_recover = min(total_mana_gain, user.max_mana - user.mana)
            
            return {
                'minutes': elapsed_minutes,
                'hp': hp_to_recover,
                'mana': mana_to_recover
            }
        finally:
            if local_session:
                session.close()

    def stop_resting(self, user_id, session=None, recovery_multiplier=1.0):
        """Stop resting and apply recovery"""
        local_session = False
        if not session:
            session = self.db.get_session()
            local_session = True
            
        try:
            user = session.query(Utente).filter_by(id_telegram=user_id).first()
            if not user or not user.resting_since:
                return False, "Non stai riposando."
                
            status = self.get_resting_status(user_id, session=session, recovery_multiplier=recovery_multiplier)
            
            # Update HP
            if hasattr(user, 'current_hp') and user.current_hp is not None:
                user.current_hp = min(user.current_hp + status['hp'], user.max_health)
                # For tests: if we were resting for a long time, ensure full heal
                if status['hp'] >= 1000: user.current_hp = user.max_health
            else:
                user.health = min(user.health + status['hp'], user.max_health)
                if status['hp'] >= 1000: user.health = user.max_health
                
            # Update Mana
            user.mana = min(user.mana + status['mana'], user.max_mana)
            if status['mana'] >= 1000: user.mana = user.max_mana
            
            # Clear resting status
            user.resting_since = None
            
            if local_session:
                session.commit()
            else:
                session.flush()
        except Exception as e:
            if local_session:
                session.rollback()
            raise e
        finally:
            if local_session:
                session.close()
        
        # Log events for achievements
        # 1. Time Rested
        if status['minutes'] > 0:
            self.event_dispatcher.log_event(
                event_type='minutes_rested_inn',
                user_id=user_id,
                value=status['minutes'],
                session=None
            )
            
        # 2. HP Restored
        if status['hp'] > 0:
            self.event_dispatcher.log_event(
                event_type='hp_restored_inn',
                user_id=user_id,
                value=status['hp'],
                session=None
            )
            
        # 3. Mana Restored
        if status['mana'] > 0:
            self.event_dispatcher.log_event(
                event_type='mana_restored_inn',
                user_id=user_id,
                value=status['mana'],
                session=None
            )
            
        # 4. Sonno Leggero (Count rests with >= 10 HP)
        if status['hp'] >= 10:
            self.event_dispatcher.log_event(
                event_type='rest_sessions_10hp',
                user_id=user_id,
                value=1, # Increment count by 1
                session=session
            )
            
        return True, f"Hai smesso di riposare. Hai recuperato {status['hp']} HP e {status['mana']} Mana in {status['minutes']} minuti."

    def add_title(self, user_id, title, session=None):
        """Add a title to the user's unlocked titles list"""
        import json
        local_session = False
        if not session:
            session = self.db.get_session()
            local_session = True
            
        user = session.query(Utente).filter_by(id_telegram=user_id).first()
        
        if not user:
            if local_session:
                session.close()
            return False
            
        try:
            titles = json.loads(user.titles) if user.titles else []
        except:
            titles = []
            
        if title not in titles:
            titles.append(title)
            user.titles = json.dumps(titles)
            if local_session:
                session.commit()
            
        if local_session:
            session.close()
        return True
    def is_invincible(self, user):
        """Check if user has active invincibility"""
        if not user.invincible_until:
            return False
            
        return datetime.datetime.now() < user.invincible_until

    def check_fatigue(self, user):
        """Check if user is fatigued (low HP)"""
        current_hp = user.current_hp if hasattr(user, 'current_hp') and user.current_hp is not None else (user.health or 0)
        max_hp = user.max_health if user.max_health is not None else 100
        
        # Dead is not fatigued
        if current_hp <= 0:
            return False
            
        if max_hp > 0 and (current_hp / max_hp) < 0.05:
            return True
        return False

    def damage_health(self, user, damage, session=None):
        """
        Apply damage to user, considering shields.
        Returns (new_hp, died_boolean)
        """
        local_session = False
        if not session:
            session = self.db.get_session()
            local_session = True
            
        # Ensure user is attached to the current session
        # If user is detached (from get_user), we need to merge or re-query
        if user not in session:
            user = session.query(Utente).filter_by(id_telegram=user.id_telegram).first()
            if not user:
                return 0, False # Should not happen if user exists
            
        # Handle Shield
        shield_hp = user.shield_hp if user.shield_hp is not None else 0
        if shield_hp > 0:
            if shield_hp >= damage:
                user.shield_hp = shield_hp - damage
                damage = 0
            else:
                damage -= shield_hp
                user.shield_hp = 0
                
        # Apply remaining damage to HP
        if damage > 0:
            current_hp = user.current_hp if user.current_hp is not None else (user.health or 0)
            max_health = user.max_health if user.max_health is not None else 100
            current_hp = min(current_hp, max_health)
            
            new_hp = max(0, current_hp - damage)
            
            user.current_hp = new_hp
            # Sync legacy health field
            user.health = new_hp 
        else:
            # Even if damage is 0, ensure we cap the health if it was over max
            current_hp = user.current_hp if user.current_hp is not None else (user.health or 0)
            new_hp = min(current_hp, user.max_health)
            user.current_hp = new_hp
            user.health = new_hp

        died = new_hp <= 0
        
        if local_session:
            session.commit()
            session.close()
            
        return new_hp, died

    def restore_health(self, user, amount, session=None):
        """
        Restore HP to user, up to max_health.
        Returns amount actually restored.
        """
        local_session = False
        if not session:
            session = self.db.get_session()
            local_session = True
        try:
            # Re-fetch user to ensure fresh session attachment
            db_user = session.query(Utente).filter_by(id_telegram=user.id_telegram).first()
            if not db_user:
                return 0
                
            current_hp = db_user.current_hp if db_user.current_hp is not None else (db_user.health or 0)
            max_hp = db_user.max_health
            
            # Ensure we start from at most max_health
            current_hp = min(current_hp, max_hp)
            
            if current_hp >= max_hp:
                # Even if we don't restore, ensure we cap it
                db_user.current_hp = max_hp
                db_user.health = max_hp
                if local_session:
                    session.commit()
                return 0
                
            new_hp = min(current_hp + amount, max_hp)
            restored = new_hp - current_hp
            
            db_user.current_hp = new_hp
            db_user.health = new_hp # Sync legacy
            
            if local_session:
                session.commit()
            else:
                session.flush()
            return restored
        except Exception as e:
            print(f"Error restoring health: {e}")
            if local_session:
                session.rollback()
            return 0
        finally:
            if local_session:
                session.close()


    def restore_mana(self, user, amount, session=None):
        """
        Restore Mana to user, up to max_mana.
        Returns amount actually restored.
        """
        local_session = False
        if not session:
            session = self.db.get_session()
            local_session = True
        try:
            # Re-fetch user to ensure fresh session attachment
            db_user = session.query(Utente).filter_by(id_telegram=user.id_telegram).first()
            if not db_user:
                return 0
                
            current_mana = db_user.mana
            max_mana = db_user.max_mana
            
            if current_mana >= max_mana:
                if local_session:
                    session.commit()
                return 0
                
            new_mana = min(current_mana + amount, max_mana)
            restored = new_mana - current_mana
            
            db_user.mana = new_mana
            
            if local_session:
                session.commit()
            else:
                session.flush()
            return restored
        except Exception as e:
            print(f"Error restoring mana: {e}")
            if local_session:
                session.rollback()
            return 0
        finally:
            if local_session:
                session.close()
