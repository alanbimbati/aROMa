from database import Database
from models.user import Utente
from models.pve import Mob
from models.combat import CombatParticipation
from models.dungeon import DungeonParticipant
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
            # Get recent users from THIS chat (48h window)
            if recent_users is None:
                recent_users = self.user_service.get_recent_users(chat_id=chat_id, minutes=2880) # 48 hours
            
            # Candidates are ONLY those active in the current chat
            all_candidates = set(recent_users) if recent_users else set()
            print(f"[DEBUG] Targeting: chat_id={chat_id}, candidates_in_chat={len(all_candidates)}")
            
            # REMOVED: Dungeon participant injection. Mobs MUST only target people active in the chat.
            # Even if in a dungeon, we only care about who is present in the current chat "instance".
            
            print(f"[DEBUG] Targeting: Total candidates to check: {len(all_candidates)}")
            
            # FALLBACK: If it's a dungeon mob, also include all registered participants
            if mob.dungeon_id:
                try:
                    participants = session.query(DungeonParticipant).filter_by(dungeon_id=mob.dungeon_id).all()
                    for p in participants:
                        if p.user_id not in all_candidates:
                            all_candidates.add(p.user_id)
                    print(f"[DEBUG] Targeting: Added dungeon participants. Total candidates: {len(all_candidates)}")
                except Exception as e:
                    print(f"[DEBUG] Error fetching dungeon participants for targeting: {e}")
            
            # Filter users based on eligibility
            valid_targets = []
            
            for uid in list(all_candidates):
                is_valid = self._is_valid_target(uid, mob, session)
                if is_valid:
                    valid_targets.append(uid)
            print(f"[DEBUG] Targeting: Final valid targets: {valid_targets}")
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
        
        # Check if account is too old (inactive for 6+ months = auto-deleted)
        if hasattr(user, 'last_activity') and user.last_activity:
            import datetime
            six_months_ago = datetime.datetime.now() - datetime.timedelta(days=180)
            if user.last_activity < six_months_ago:
                print(f"[DEBUG] User {user_id} inactive for 6+ months, skipping")
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
        
        # No more dungeon-specific participant check for targeting.
        # If they are in recent_users for this chat, they are valid targets.
        
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
        
        # Check cooldown (1 point = 5% CD reduction)
        user_speed = getattr(user, 'speed', 0) or 0
        cooldown_seconds = 60 / (1 + user_speed * 0.05)
        
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
        # Check cooldown (shared with attack, 1 point = 5% CD reduction)
        user_speed = getattr(user, 'speed', 0) or 0
        cooldown_seconds = 60 / (1 + user_speed * 0.05)
        
        last_attack = getattr(user, 'last_attack_time', None)
        if last_attack:
            elapsed = (datetime.datetime.now() - last_attack).total_seconds()
            if elapsed < cooldown_seconds:
                remaining = int(cooldown_seconds - elapsed)
                return False, f"⏳ Sei stanco! (CD: {int(cooldown_seconds)}s)\nDevi riposare ancora per {remaining}s."
        
        return True, ""
