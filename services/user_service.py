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

class UserService:
    # Class-level dictionary to track activity with timestamps
    # Format: {(user_id, chat_id): timestamp}
    _recent_activities = {}
    _exp_required_column_exists = None  # Cache per verificare se la colonna esiste

    def __init__(self):
        self.db = Database()
        self.recent_activities = UserService._recent_activities
        self.event_dispatcher = EventDispatcher()

    def get_user_by_username(self, username):
        """Get user by username (case insensitive)"""
        session = self.db.get_session()
        user = session.query(Utente).filter(func.lower(Utente.username) == username.lower()).first()
        session.close()
        return user
    
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
            
        key = (user_id, chat_id)
        self.recent_activities[key] = datetime.datetime.now()
        print(f"[DEBUG] track_activity: user_id={user_id}, chat_id={chat_id}")
        
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

    def get_user(self, target):
        session = self.db.get_session()
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
            chatid = int(target)
            utente = session.query(Utente).filter_by(id_telegram=chatid).first()
            
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
        try:
            self.update_user(utente.id_telegram, {'points': int(utente.points) + int(points)})
        except Exception as e:
            print(e)

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

    def add_points_by_id(self, user_id, points, is_drop=False):
        """
        Add points to a user by their Telegram ID
        Args:
            user_id: Telegram ID
            points: Amount of Wumpa to add
            is_drop: If True, counts towards daily cap
        """
        session = self.db.get_session()
        utente = session.query(Utente).filter_by(id_telegram=user_id).first()
        if utente:
            # Check for daily reset
            self.check_daily_reset(utente)
            
            # Add points
            utente.points = int(utente.points) + int(points)
            
            # Track daily earnings if it's a drop
            if is_drop:
                utente.daily_wumpa_earned = (utente.daily_wumpa_earned or 0) + int(points)
            
            session.commit()
            
            # NEW: Log point gain event
            self.event_dispatcher.log_event(
                event_type='point_gain',
                user_id=user_id,
                value=points,
                context={'is_drop': is_drop, 'new_total': utente.points}
            )
        session.close()

    def add_exp(self, utente, exp):
        self.update_user(utente.id_telegram, {'exp': utente.exp + exp})

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

    def add_exp_by_id(self, user_id, exp):
        """Add experience to a user by their Telegram ID and check for level-up"""
        session = self.db.get_session()
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
                loader = get_character_loader()
                chars = loader.get_characters_by_level(level)
                if chars:
                    # All characters of same level should have same exp req, take first
                    return chars[0].get('exp_required', 100)
                
                # Fallback to DB if loader fails (unlikely if CSV is good)
                level_data = self._get_livello_by_level(session, level)
                if level_data and hasattr(level_data, 'exp_required') and level_data.exp_required is not None:
                    return level_data.exp_required
                
                # Final fallback: Formula
                return 100 * (level ** 2)

            # Check for level-up
            next_exp_req = get_exp_required_for_level(utente.livello + 1)
            
            while next_exp_req is not None and utente.exp >= next_exp_req:
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
                
                # Increase base stats
                utente.max_health += 10
                utente.max_mana += 10
                utente.base_damage += 2
                
                # Full Heal on Level Up
                utente.health = utente.max_health
                if hasattr(utente, 'current_hp'):
                    utente.current_hp = utente.max_health
                utente.mana = utente.max_mana
                
                leveled_up = True
                new_level = utente.livello
                
                # NEW: Log level up event
                self.event_dispatcher.log_event(
                    event_type='level_up',
                    user_id=user_id,
                    value=new_level,
                    context={'exp': utente.exp},
                    session=session
                )
                
                # Check for next level
                next_exp_req = get_exp_required_for_level(utente.livello + 1)
            
            # Get next level exp requirement for display
            next_level_exp = next_exp_req
            
            session.commit()
        session.close()
        
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
        """Get formatted user info string"""
        if not utente_sorgente:
            return "L'utente non esiste"

        utente = self.get_user(utente_sorgente.id_telegram)
        from services.character_loader import get_character_loader
        char_loader = get_character_loader()
        
        info_lv = char_loader.get_characters_by_level(utente.livello)
        info_lv = info_lv[0] if info_lv else None
        selected_level = char_loader.get_character_by_id(utente.livello_selezionato)
        
        # Get game names
        session = self.db.get_session()
        giochi_utente = session.query(GiocoUtente).filter_by(id_telegram=utente.id_telegram).all()
        session.close()

        nome_utente = utente.nome if utente.username is None else utente.username
        answer = f"🎖 Utente Premium\n" if utente.premium == 1 else ''
        answer += f"✅ Abbonamento attivo (fino al {str(utente_sorgente.scadenza_premium)[:11]})\n" if utente.abbonamento_attivo == 1 else ''

        if info_lv is not None:
            answer += f"*👤 {nome_utente}*: {utente.points} {PointsName}\n"
            
            # Calculate next level exp
            next_lv_num = utente.livello + 1
            next_lv_row = char_loader.get_characters_by_level(next_lv_num)
            next_lv_row = next_lv_row[0] if next_lv_row else None
            
            if next_lv_row:
                exp_req = next_lv_row.get('exp_required', 100)
            else:
                # Formula for levels beyond DB
                exp_req = 100 * (next_lv_num ** 2)
            
            answer += f"*💪🏻 Exp*: {utente.exp}/{exp_req}\n"
            answer += f"*🎖 Lv. *{utente.livello} - {selected_level['nome'] if selected_level else 'N/A'}\n"
        else:
            answer += f"*👤 {nome_utente}*: {utente.points} {PointsName}\n"
            answer += f"*💪🏻 Exp*: {utente.exp}\n"
            answer += f"*🎖 Lv. *{utente.livello}\n"
        
        # RPG Stats Card
        current_hp = utente.current_hp if hasattr(utente, 'current_hp') and utente.current_hp is not None else utente.health
        user_speed = getattr(utente, 'speed', 0) or 0
        cooldown_seconds = int(60 / (1 + user_speed * 0.05))
        
        card = f"╔══════🕹 **{nome_utente.upper()}** ══════╗\n"
        card += f" ❤️ **Vita**: {current_hp}/{utente.max_health}\n"
        card += f" ⚡ **Velocità**: {user_speed} (CD: {cooldown_seconds}s)\n"
        card += f" 🌀 **Mana**: {utente.mana}/{utente.max_mana}\n"
        card += f" ⚔️ **Danno**: {utente.base_damage}\n"
        card += "          *aROMa*\n"
        card += "╚═══════════════════════╝"
        
        answer += f"\n{card}\n"
        
        if utente.stat_points > 0:
            answer += f"*📊 Punti Stat*: {utente.stat_points} (usa /stats)\n"
        
        # Check fatigue
        if self.check_fatigue(utente):
            answer += "\n⚠️ *SEI AFFATICATO!* Riposa per recuperare vita.\n"
        
        # Special attack info  
        if selected_level and selected_level.get('special_attack_name'):
            answer += f"\n*✨ Speciale*: {selected_level['special_attack_name']}\n"
            answer += f"  Danno: {selected_level['special_attack_damage']} | Mana: {selected_level['special_attack_mana_cost']}\n"

        if giochi_utente:
            answer += '\n\n👾 Nome in Game 👾\n'
            answer += '\n'.join(f"*🎮 {giocoutente.piattaforma}:* `{giocoutente.nome}`" for giocoutente in giochi_utente)

        return answer

    def get_username_at_least_name(self, utente):
        if utente is not None:
            if utente.username is None:
                nome = utente.nome
            else:
                nome = utente.username
            return nome
        else:
            return "Nessun nome"
    
    # === RPG METHODS ===
    
    def restore_daily_health(self, utente):
        """Restore health based on time elapsed since last restore"""
        session = self.db.get_session()
        user = session.query(Utente).filter_by(id_telegram=utente.id_telegram).first()
        
        if not user:
            session.close()
            return False
        
        now = datetime.datetime.now()
        last_restore = user.last_health_restore
        
        # First time or after 1+ days
        if not last_restore or (now - last_restore).total_seconds() >= 86400:
            # Restore 20% max health per day
            health_to_restore = int(user.max_health * 0.2)
            new_health = min(user.health + health_to_restore, user.max_health)
            
            user.health = new_health
            user.last_health_restore = now
            session.commit()
            session.close()
            return True, health_to_restore
        
        session.close()
        return False, 0
    
    def is_invincible(self, user):
        """Check if user is currently invincible"""
        if not user or not user.invincible_until:
            return False
        return datetime.datetime.now() < user.invincible_until

    def check_fatigue(self, utente):
        """Check if user is fatigued (0 current_hp = can't fight)"""
        # Check current_hp if available, fallback to health
        if hasattr(utente, 'current_hp') and utente.current_hp is not None:
            return utente.current_hp <= 0
        return utente.health <= 0
    
    def damage_health(self, utente, damage, session=None):
        """Reduce user health. Returns (new_health, died)"""
        # Check invincibility
        if self.is_invincible(utente):
            current_hp = utente.current_hp if hasattr(utente, 'current_hp') and utente.current_hp is not None else utente.health
            return current_hp, False

        # Shield Logic
        actual_damage = damage
        
        # Check if shield is active
        if utente.shield_hp and utente.shield_hp > 0:
            # Check expiration
            if utente.shield_end_time and utente.shield_end_time > datetime.datetime.now():
                # Shield is active: Apply Resistance Boost (+25%, capped at 75%)
                # ... (logic same as before)
                
                mitigation = 0.25
                actual_damage = int(damage * (1 - mitigation))
                
                # Absorb into shield
                if utente.shield_hp >= actual_damage:
                    utente.shield_hp -= actual_damage
                    self.update_user(utente.id_telegram, {'shield_hp': utente.shield_hp}, session=session)
                    # No HP damage
                    current_hp = utente.current_hp if hasattr(utente, 'current_hp') and utente.current_hp is not None else utente.health
                    return current_hp, False
                else:
                    # Shield breaks
                    remaining_damage = actual_damage - utente.shield_hp
                    utente.shield_hp = 0
                    utente.shield_end_time = None # Shield broken
                    self.update_user(utente.id_telegram, {'shield_hp': 0, 'shield_end_time': None}, session=session)
                    actual_damage = remaining_damage
            else:
                # Expired
                utente.shield_hp = 0
                self.update_user(utente.id_telegram, {'shield_hp': 0}, session=session)

        # Use current_hp if available
        if hasattr(utente, 'current_hp') and utente.current_hp is not None:
            new_health = max(0, utente.current_hp - actual_damage)
            self.update_user(utente.id_telegram, {'current_hp': new_health}, session=session)
            return new_health, new_health <= 0
            
        # Fallback to old health
        new_health = max(0, utente.health - actual_damage)
        self.update_user(utente.id_telegram, {'health': new_health}, session=session)
        return new_health, new_health <= 0

    def cast_shield(self, utente, amount, duration_minutes=10):
        """Cast a shield on the user"""
        now = datetime.datetime.now()
        end_time = now + datetime.timedelta(minutes=duration_minutes)
        
        updates = {
            'shield_hp': amount,
            'shield_max_hp': amount,
            'shield_end_time': end_time,
            'last_shield_cast': now
        }
        self.update_user(utente.id_telegram, updates)
        return True
    
    def restore_health(self, utente, amount):
        """Restore health (from items/etc)"""
        # Use current_hp if available
        if hasattr(utente, 'current_hp') and utente.current_hp is not None:
            new_health = min(utente.current_hp + amount, utente.max_health)
            self.update_user(utente.id_telegram, {'current_hp': new_health})
            return new_health
            
        # Fallback to old health
        new_health = min(utente.health + amount, utente.max_health)
        self.update_user(utente.id_telegram, {'health': new_health})
        return new_health
    
    def use_mana(self, utente, cost):
        """Use mana for special attacks"""
        if utente.mana >= cost:
            new_mana = utente.mana - cost
            self.update_user(utente.id_telegram, {'mana': new_mana})
            return True
        return False
    
    def restore_mana(self, utente, amount):
        """Restore mana"""
        new_mana = min(utente.mana + amount, utente.max_mana)
        self.update_user(utente.id_telegram, {'mana': new_mana})
        return new_mana
    
    def allocate_stat_point(self, utente, stat_type):
        """Allocate a stat point to HP, Mana, Damage, Resistance, Crit, or Speed"""
        if utente.stat_points <= 0:
            return False, "Non hai punti statistica disponibili!"
        
        updates = {'stat_points': utente.stat_points - 1}
        
        if stat_type == "health":
            updates['max_health'] = utente.max_health + 10
            updates['allocated_health'] = utente.allocated_health + 1
            msg = "Max Health +10!"
        elif stat_type == "mana":
            updates['max_mana'] = utente.max_mana + 5
            updates['allocated_mana'] = utente.allocated_mana + 1
            msg = "Max Mana +5!"
        elif stat_type == "damage":
            updates['base_damage'] = utente.base_damage + 2
            updates['allocated_damage'] = utente.allocated_damage + 1
            msg = "Base Damage +2!"
        elif stat_type == "resistance":
            # Cap resistance at 75% to prevent immortality
            current_resistance = getattr(utente, 'resistance', 0) or 0
            if current_resistance >= 75:
                return False, "⚠️ Resistenza massima raggiunta (75%)!"
            updates['resistance'] = current_resistance + 1
            updates['allocated_resistance'] = (utente.allocated_resistance or 0) + 1
            msg = "Resistenza +1%!"
        elif stat_type == "crit":
            updates['crit_chance'] = (utente.crit_chance or 0) + 1
            updates['allocated_crit'] = (utente.allocated_crit or 0) + 1
            msg = "Critico +1%!"
        elif stat_type == "speed":
            updates['speed'] = (utente.speed or 0) + 5
            updates['allocated_speed'] = (utente.allocated_speed or 0) + 1
            msg = "Velocità +5!"
        else:
            return False, "Statistica non valida!"
        
        self.update_user(utente.id_telegram, updates)
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
        
        # Reset to base values
        updates = {
            'max_health': 100 + (utente.livello * 5),  # Base + level bonus
            'max_mana': 50 + (utente.livello * 2),
            'base_damage': 10 + (utente.livello * 1),
            'allocated_health': 0,
            'allocated_mana': 0,
            'allocated_damage': 0,
            'allocated_resistance': 0,
            'allocated_crit': 0,
            'allocated_speed': 0,
            'resistance': 0,
            'crit_chance': 0,
            'speed': 0,
            'stat_points': utente.livello * 2
        }
        
        if paid:
            updates['points'] = utente.points - RESET_COST
        
        self.update_user(utente.id_telegram, updates)
        return True, f"Statistiche resettate! {points_to_refund} punti restituiti."
    def start_resting(self, user_id):
        """Start resting in the public inn"""
        session = self.db.get_session()
        user = session.query(Utente).filter_by(id_telegram=user_id).first()
        if not user:
            session.close()
            return False, "Utente non trovato."
        
        if user.resting_since:
            session.close()
            return False, "Stai già riposando!"
            
        user.resting_since = datetime.datetime.now()
        session.commit()
        session.close()
        return True, "Hai iniziato a riposare nella Locanda Pubblica. Recupererai 1 HP e 1 Mana al minuto."

    def get_resting_status(self, user_id):
        """Check how much HP/Mana would be recovered if resting stopped now"""
        session = self.db.get_session()
        user = session.query(Utente).filter_by(id_telegram=user_id).first()
        if not user or not user.resting_since:
            session.close()
            return None
            
        now = datetime.datetime.now()
        elapsed_minutes = int((now - user.resting_since).total_seconds() / 60)
        
        # 1 HP and 1 Mana per minute
        current_hp = user.current_hp if user.current_hp is not None else user.health
        hp_to_recover = min(elapsed_minutes, user.max_health - current_hp)
        mana_to_recover = min(elapsed_minutes, user.max_mana - user.mana)
        
        session.close()
        return {
            'minutes': elapsed_minutes,
            'hp': hp_to_recover,
            'mana': mana_to_recover
        }

    def stop_resting(self, user_id):
        """Stop resting and apply recovery"""
        session = self.db.get_session()
        user = session.query(Utente).filter_by(id_telegram=user_id).first()
        if not user or not user.resting_since:
            session.close()
            return False, "Non stai riposando."
            
        status = self.get_resting_status(user_id)
        
        # Update HP
        if hasattr(user, 'current_hp') and user.current_hp is not None:
            user.current_hp = min(user.current_hp + status['hp'], user.max_health)
        else:
            user.health = min(user.health + status['hp'], user.max_health)
            
        # Update Mana
        user.mana = min(user.mana + status['mana'], user.max_mana)
        
        # Clear resting status
        user.resting_since = None
        
        session.commit()
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
                session=None
            )
            
        return True, f"Hai smesso di riposare. Hai recuperato {status['hp']} HP e {status['mana']} Mana in {status['minutes']} minuti."

    def add_title(self, user_id, title):
        """Add a title to the user's unlocked titles list"""
        import json
        session = self.db.get_session()
        user = session.query(Utente).filter_by(id_telegram=user_id).first()
        
        if not user:
            session.close()
            return False
            
        try:
            titles = json.loads(user.titles) if user.titles else []
        except:
            titles = []
            
        if title not in titles:
            titles.append(title)
            user.titles = json.dumps(titles)
            session.commit()
            
        session.close()
        return True
