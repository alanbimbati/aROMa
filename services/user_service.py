from database import Database
from models.user import Utente, Admin
from models.system import Livello, Domenica
from models.game import GiocoUtente
from sqlalchemy import desc, asc
import datetime
from dateutil.relativedelta import relativedelta
from settings import PointsName

class UserService:
    def __init__(self):
        self.db = Database()

    def get_user(self, target):
        session = self.db.get_session()
        utente = None
        target = str(target)

        if target.startswith('@'):
            utente = session.query(Utente).filter_by(username=target).first()
        else:
            chatid = int(target) if target.isdigit() else None
            if chatid is not None:
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

    def update_user(self, chatid, kwargs):
        session = self.db.get_session()
        utente = session.query(Utente).filter_by(id_telegram=chatid).first()
        if utente:
            for key, value in kwargs.items():
                setattr(utente, key, value)
            session.commit()
        session.close()

    def add_points(self, utente, points):
        try:
            self.update_user(utente.id_telegram, {'points': int(utente.points) + int(points)})
        except Exception as e:
            print(e)

    def add_exp(self, utente, exp):
        self.update_user(utente.id_telegram, {'exp': utente.exp + exp})

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
        if not utente_sorgente:
            return "L'utente non esiste"

        utente = self.get_user(utente_sorgente.id_telegram)
        session = self.db.get_session()
        info_lv = session.query(Livello).filter_by(livello=utente.livello).first()
        selected_level = session.query(Livello).filter_by(id=utente.livello_selezionato).first()
        giochi_utente = session.query(GiocoUtente).filter_by(id_telegram=utente.id_telegram).all()
        session.close()

        nome_utente = utente.nome if utente.username is None else utente.username
        answer = f"🎖 Utente Premium\n" if utente.premium == 1 else ''
        answer += f"✅ Abbonamento attivo (fino al {str(utente_sorgente.scadenza_premium)[:11]})\n" if utente.abbonamento_attivo == 1 else ''

        if info_lv is not None:
            answer += f"*👤 {nome_utente}*: {utente.points} {PointsName}\n"
            answer += f"*💪🏻 Exp*: {utente.exp}/{info_lv.exp_required if hasattr(info_lv, 'exp_required') else info_lv.exp_to_lv}\n"
            answer += f"*🎖 Lv. *{utente.livello} - {selected_level.nome if selected_level else 'N/A'}\n"
        else:
            answer += f"*👤 {nome_utente}*: {utente.points} {PointsName}\n"
            answer += f"*💪🏻 Exp*: {utente.exp}\n"
            answer += f"*🎖 Lv. *{utente.livello}\n"
        
        # RPG Stats
        answer += f"\n*❤️ Vita*: {utente.health}/{utente.max_health}\n"
        answer += f"*💙 Mana*: {utente.mana}/{utente.max_mana}\n"
        answer += f"*⚔️ Danno Base*: {utente.base_damage}\n"
        
        if utente.stat_points > 0:
            answer += f"*📊 Punti Stat*: {utente.stat_points} (usa /stats)\n"
        
        # Check fatigue
        if self.check_fatigue(utente):
            answer += "\n⚠️ *SEI AFFATICATO!* Riposa per recuperare vita.\n"
        
        # Special attack info
        if selected_level and selected_level.special_attack_name:
            answer += f"\n*✨ Attacco Speciale*: {selected_level.special_attack_name}\n"
            answer += f"  Danno: {selected_level.special_attack_damage} | Mana: {selected_level.special_attack_mana_cost}\n"

        if giochi_utente:
            answer += '\n\n👾 Nome in Game 👾\n'
            answer += '\n'.join(f"*🎮 {giocoutente.piattaforma}:* `{giocoutente.nome}`" for giocoutente in giochi_utente)

        return answer

    def check_is_sunday(self, utente):
        session = self.db.get_session()
        chatid = utente.id_telegram
        oggi = datetime.datetime.today().date()
        is_sunday = False
        
        if oggi.strftime('%A') == 'Sunday':
            exist = session.query(Domenica).filter_by(utente=chatid).first()
            if exist is None:
                try:
                    domenica = Domenica()
                    domenica.last_day = oggi
                    domenica.utente = chatid
                    session.add(domenica)
                    session.commit()
                    self.add_points(utente, 1)
                    is_sunday = True
                except:
                    session.rollback()
                finally:
                    pass
            elif exist.last_day != oggi:
                exist.last_day = oggi
                session.commit()
                self.add_points(utente, 1)
                is_sunday = True
        
        session.close()
        return is_sunday

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
    
    def check_fatigue(self, utente):
        """Check if user is fatigued (0 health = can't earn rewards)"""
        return utente.health <= 0
    
    def damage_health(self, utente, damage):
        """Reduce user health"""
        new_health = max(0, utente.health - damage)
        self.update_user(utente.id_telegram, {'health': new_health})
        return new_health
    
    def restore_health(self, utente, amount):
        """Restore health (from items/etc)"""
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
        """Allocate a stat point to HP, Mana, or Damage"""
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
        else:
            return False, "Statistica non valida!"
        
        self.update_user(utente.id_telegram, updates)
        return True, msg
    
    def reset_stats(self, utente, paid=True):
        """Reset stat allocations (costs Wumpa if not free)"""
        RESET_COST = 500
        
        if paid and utente.points < RESET_COST:
            return False, f"Non hai abbastanza {PointsName}! Costo: {RESET_COST}"
        
        # Calculate stats to refund
        points_to_refund = utente.allocated_health + utente.allocated_mana + utente.allocated_damage
        
        # Reset to base values
        updates = {
            'max_health': 100 + (utente.livello * 5),  # Base + level bonus
            'max_mana': 50 + (utente.livello * 2),
            'base_damage': 10 + (utente.livello * 1),
            'allocated_health': 0,
            'allocated_mana': 0,
            'allocated_damage': 0,
            'stat_points': utente.stat_points + points_to_refund
        }
        
        if paid:
            updates['points'] = utente.points - RESET_COST
        
        self.update_user(utente.id_telegram, updates)
        return True, f"Statistiche resettate! {points_to_refund} punti restituiti."
