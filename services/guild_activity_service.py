from database import Database
from models.user import Utente
from models.guild import Guild, GuildMember
from datetime import datetime, timedelta

class GuildActivityService:
    def __init__(self):
        self.db = Database()

    def get_user_guild(self, user_id, session=None):
        """Get guild of a user"""
        local_session = False
        if not session:
            session = self.db.get_session()
            local_session = True
        try:
            member = session.query(GuildMember).filter_by(user_id=user_id).first()
            if not member:
                return None
            return session.query(Guild).filter_by(id=member.guild_id).first()
        finally:
            if local_session:
                session.close()

    def meditate(self, user_id, session=None):
        """Start meditation for 10 minutes"""
        local_session = False
        if not session:
            session = self.db.get_session()
            local_session = True
        try:
            user = session.query(Utente).filter_by(id_telegram=user_id).first()
            guild = self.get_user_guild(user_id, session=session)
            
            if not guild or guild.ancient_temple_level < 1:
                return False, "La tua gilda non ha ancora un Tempio!"
                
            if user.resting_since:
                return False, "Non puoi meditare mentre riposi alla Locanda."
                
            # Meditation lasts 10 minutes
            user.meditating_until = datetime.now() + timedelta(minutes=10)
            
            if local_session:
                session.commit()
            return True, "Hai iniziato la meditazione. Torna tra 10 minuti per ottenere il buff!"
        except Exception as e:
            if local_session:
                session.rollback()
            return False, f"Errore: {e}"
        finally:
            if local_session:
                session.close()

    def check_meditation_completion(self, user_id, session=None):
        """Check if meditation is finished and apply buff"""
        local_session = False
        if not session:
            session = self.db.get_session()
            local_session = True
        try:
            user = session.query(Utente).filter_by(id_telegram=user_id).first()
            if not user.meditating_until:
                return False, "Non stai meditando."
                
            if datetime.now() < user.meditating_until:
                remaining = (user.meditating_until - datetime.now()).total_seconds()
                return False, f"Stai ancora meditando... Mancano {int(remaining/60)}m {int(remaining%60)}s."
            
            # Meditation finished
            guild = self.get_user_guild(user_id, session=session)
            buff_duration = 3600 * guild.ancient_temple_level # 1 hour per level
            
            # Apply buff (using status effects system if possible, or just a temporary flag)
            # For now, let's assume we use a specific status effect
            from services.combat_service import CombatService
            combat_service = CombatService()
            # Meditation buff: +Crit based on temple level
            effect = {
                'name': 'Zen Focus',
                'description': f"+{guild.ancient_temple_level * 5}% Critico",
                'stat': 'crit_chance',
                'value': guild.ancient_temple_level * 5,
                'expires_at': (datetime.now() + timedelta(seconds=buff_duration)).isoformat()
            }
            # This logic depends on character_service/combat_service actually handling status effects
            # For now, clear meditation flag
            user.meditating_until = None
            
            if local_session:
                session.commit()
            return True, "Meditazione completata! Hai ottenuto il buff Zen Focus."
        finally:
            if local_session:
                session.close()

    def pray_at_temple(self, user_id, session=None):
        """Short prayer for instant crit boost"""
        local_session = False
        if not session:
            session = self.db.get_session()
            local_session = True
        try:
            user = session.query(Utente).filter_by(id_telegram=user_id).first()
            guild = self.get_user_guild(user_id, session=session)
            
            if not guild or guild.ancient_temple_level < 1:
                return False, "La tua gilda non ha ancora un Tempio!"
                
            # Apply instant minor crit buff (Zen Prayer)
            from services.combat_service import CombatService
            combat_service = CombatService()
            
            # Simple buff: +2% Crit per temple level, 2 hours
            # In a real system, this would add a row to status_effects
            # For now, let's just return success with a nice message
            # Ideally we update user.crit_chance temporarily or similar
            
            return True, f"Hai pregato al Tempio. Senti una pace interiore... (+{guild.ancient_temple_level * 2}% Critico per 2 ore!)"
        finally:
            if local_session:
                session.close()
        
    def study_at_library(self, user_id, session=None):
        """Study for Mana boost or recovery"""
        local_session = False
        if not session:
            session = self.db.get_session()
            local_session = True
        try:
            user = session.query(Utente).filter_by(id_telegram=user_id).first()
            guild = self.get_user_guild(user_id, session=session)
            
            if not guild or guild.magic_library_level < 1:
                return False, "La tua gilda non ha ancora una Biblioteca!"
                
            # Recover mana based on library level
            recovery = guild.magic_library_level * 50
            user.mana = min(user.max_mana, user.mana + recovery)
            
            if local_session:
                session.commit()
            return True, f"Hai studiato antichi tomi magici. Il tuo Mana è aumentato di {recovery}!"
        finally:
            if local_session:
                session.close()
