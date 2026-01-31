from database import Database
from models.user import Utente
from models.pve import Mob
from models.combat import CombatParticipation
from services.user_service import UserService
import datetime


class TargetingService:
    """
    Centralized service for all mob targeting logic.
    
    This service determines which users can be targeted by mobs,
    and which users can perform combat actions (attack/defend).
    
    Responsibilities:
    - Determine valid targets for mobs (world and dungeon)
    - Check user eligibility (HP > 0, not resting, not fled)
    - Handle fatigue rules (fatigued users can be targeted but can't attack)
    """
    
    def __init__(self):
        self.db = Database()
        self.user_service = UserService()
    
    def get_valid_targets(self, mob, chat_id=None, recent_users=None, session=None):
        """
        Get list of valid target user IDs for a mob.
        
        Args:
            mob: Mob object to find targets for
            chat_id: Optional chat ID to filter users
            recent_users: Optional list of recent user IDs (if None, will fetch)
            session: Optional database session
            
        Returns:
            list: User IDs that can be targeted
        """
        local_session = False
        if not session:
            session = self.db.get_session()
            local_session = True
        
        try:
            # Get recent users if not provided
            if recent_users is None:
                recent_users = self.user_service.get_recent_users(chat_id=chat_id)
            
            # Filter users based on eligibility
            valid_targets = []
            
            for uid in recent_users:
                if self._is_valid_target(uid, mob, session):
                    valid_targets.append(uid)
            
            return valid_targets
            
        finally:
            if local_session:
                session.close()
    
    def _is_valid_target(self, user_id, mob, session):
        """Check if a user is a valid target for a mob."""
        # Use session to query user
        user = session.query(Utente).filter_by(id_telegram=user_id).first()
        if not user:
            return False
        
        # Check if resting
        is_resting = self.user_service.get_resting_status(user.id_telegram, session=session)
        if is_resting:
            return False
        
        # Check if alive (HP > 0)
        current_hp = user.current_hp if (hasattr(user, 'current_hp') and user.current_hp is not None) else (user.health or 0)
        if current_hp <= 0:
            return False
        
        # Check if fled from this mob
        participation = session.query(CombatParticipation).filter_by(
            mob_id=mob.id,
            user_id=user_id,
            has_fled=True
        ).first()
        if participation:
            return False
        
        # Dungeon-specific checks
        from services.dungeon_service import DungeonService
        ds = DungeonService()
        if mob.dungeon_id:
            # For dungeon mobs, user must be a participant
            participants = ds.get_dungeon_participants(mob.dungeon_id, session=session)
            participant_ids = [p.user_id for p in participants]
            
            if user_id not in participant_ids:
                return False
        else:
            # For world mobs, user must NOT be in any dungeon
            if ds.get_user_active_dungeon(user_id, session=session):
                return False
        
        return True
    
    def can_user_attack(self, user):
        """
        Check if a user can perform an attack action.
        
        Users cannot attack if:
        - They are fatigued (HP < 5% of max)
        - They are on cooldown
        
        Args:
            user: User object
            
        Returns:
            tuple: (bool, str) - (can_attack, error_message)
        """
        # Check fatigue
        if self.user_service.check_fatigue(user):
            return False, "Sei troppo affaticato per combattere! Riposa."
        
        # Check cooldown
        user_speed = getattr(user, 'speed', 0) or 0
        cooldown_seconds = 60 / (1 + user_speed * 0.01)
        
        last_attack = getattr(user, 'last_attack_time', None)
        if last_attack:
            elapsed = (datetime.datetime.now() - last_attack).total_seconds()
            if elapsed < cooldown_seconds:
                remaining = int(cooldown_seconds - elapsed)
                return False, f"⏳ Sei stanco! (CD: {int(cooldown_seconds)}s)\nDevi riposare ancora per {remaining}s."
        
        return True, ""
    
    def can_user_defend(self, user):
        """
        Check if a user can perform a defend action.
        
        Users can defend even when fatigued, but not when on cooldown.
        
        Args:
            user: User object
            
        Returns:
            tuple: (bool, str) - (can_defend, error_message)
        """
        # Check cooldown (shared with attack)
        user_speed = getattr(user, 'speed', 0) or 0
        cooldown_seconds = 60 / (1 + user_speed * 0.01)
        
        last_attack = getattr(user, 'last_attack_time', None)
        if last_attack:
            elapsed = (datetime.datetime.now() - last_attack).total_seconds()
            if elapsed < cooldown_seconds:
                remaining = int(cooldown_seconds - elapsed)
                return False, f"⏳ Sei stanco! (CD: {int(cooldown_seconds)}s)\nDevi riposare ancora per {remaining}s."
        
        return True, ""
