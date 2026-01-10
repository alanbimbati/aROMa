"""
Achievement Tracker Service - Tracks and awards achievements based on game events.
"""

from database import Database
from models.achievements import Achievement, UserAchievement, GameEvent
from services.event_dispatcher import EventDispatcher
from services.user_service import UserService
import datetime
import json

class AchievementTracker:
    """Tracks and awards achievements based on game events"""
    
    def __init__(self):
        self.db = Database()
        self.event_dispatcher = EventDispatcher()
        self.user_service = UserService()
    
    def process_pending_events(self, limit=50):
        """
        Process unprocessed events and check for achievement triggers
        
        Args:
            limit: Maximum number of events to process
        """
        events = self.event_dispatcher.get_unprocessed_events(limit=limit)
        
        for event in events:
            self.process_event(event)
            self.event_dispatcher.mark_processed(event.id)
    
    def process_event(self, event):
        """
        Process a single game event and check for achievement triggers
        
        Args:
            event: GameEvent object
        """
        if not event.user_id:
            return  # Skip system events
        
        event_type = event.event_type
        user_id = event.user_id
        event_data = json.loads(event.event_data) if event.event_data else {}
        
        session = self.db.get_session()
        try:
            # Get all achievements that match this event type
            matching_achievements = session.query(Achievement).filter(
                Achievement.trigger_event == event_type
            ).all()
            
            for achievement in matching_achievements:
                # Check if user already has this achievement
                user_achievement = session.query(UserAchievement).filter(
                    UserAchievement.user_id == user_id,
                    UserAchievement.achievement_id == achievement.id
                ).first()
                
                # Skip if completed and not progressive
                if user_achievement and user_achievement.is_completed and not achievement.is_progressive:
                    continue
                
                # Check trigger conditions
                if self.check_conditions(achievement, event_data):
                    self.award_achievement(user_id, achievement, event_data, session)
        
        finally:
            session.close()
    
    def check_conditions(self, achievement, event_data):
        """
        Check if event data matches achievement conditions
        
        Args:
            achievement: Achievement object
            event_data: Dictionary with event data
            
        Returns:
            Boolean indicating if conditions are met
        """
        if not achievement.trigger_condition:
            return True
        
        try:
            conditions = json.loads(achievement.trigger_condition)
        except:
            return True
        
        for key, value in conditions.items():
            if key.startswith('min_'):
                # Minimum value check
                data_key = key[4:]  # Remove 'min_' prefix
                if event_data.get(data_key, 0) < value:
                    return False
            
            elif key.startswith('max_'):
                # Maximum value check
                data_key = key[4:]  # Remove 'max_' prefix
                if event_data.get(data_key, float('inf')) > value:
                    return False
            
            elif key == 'count':
                # Special case for first achievement
                # This is handled by checking if user_achievement exists
                continue
            
            else:
                # Exact match
                if event_data.get(key) != value:
                    return False
        
        return True
    
    def award_achievement(self, user_id, achievement, event_data, session=None):
        """
        Award achievement to user
        
        Args:
            user_id: Telegram ID of user
            achievement: Achievement object
            event_data: Dictionary with event data
            session: Database session (optional)
        """
        close_session = False
        if not session:
            session = self.db.get_session()
            close_session = True
        
        try:
            user_achievement = session.query(UserAchievement).filter(
                UserAchievement.user_id == user_id,
                UserAchievement.achievement_id == achievement.id
            ).first()
            
            if not user_achievement:
                user_achievement = UserAchievement(
                    user_id=user_id,
                    achievement_id=achievement.id,
                    current_progress=0
                )
                session.add(user_achievement)
            
            # Update progress
            if achievement.is_progressive:
                increment = event_data.get('progress_increment', 1)
                user_achievement.current_progress += increment
                user_achievement.last_progress_update = datetime.datetime.now()
                
                if user_achievement.current_progress >= achievement.max_progress:
                    if not user_achievement.is_completed:
                        user_achievement.is_completed = True
                        user_achievement.completion_date = datetime.datetime.now()
                        user_achievement.times_earned += 1
                        
                        # Award rewards
                        self.give_rewards(user_id, achievement)
                        
                        # Notify user
                        self.notify_achievement_unlocked(user_id, achievement)
            else:
                if not user_achievement.is_completed:
                    user_achievement.is_completed = True
                    user_achievement.completion_date = datetime.datetime.now()
                    user_achievement.times_earned = 1
                    user_achievement.current_progress = achievement.max_progress
                    
                    # Award rewards
                    self.give_rewards(user_id, achievement)
                    
                    # Notify user
                    self.notify_achievement_unlocked(user_id, achievement)
            
            session.commit()
            
        except Exception as e:
            session.rollback()
            print(f"Error awarding achievement: {e}")
        finally:
            if close_session:
                session.close()
    
    def give_rewards(self, user_id, achievement):
        """
        Give achievement rewards to user
        
        Args:
            user_id: Telegram ID of user
            achievement: Achievement object
        """
        user = self.user_service.get_user(user_id)
        if not user:
            return
        
        # Award points
        if achievement.reward_points:
            self.user_service.add_points(user, achievement.reward_points)
        
        # Award title
        if achievement.reward_title:
            session = self.db.get_session()
            try:
                from models.user import Utente
                db_user = session.query(Utente).filter_by(id_telegram=user_id).first()
                if db_user:
                    # Update titles list
                    current_titles = []
                    if db_user.titles:
                        try:
                            current_titles = json.loads(db_user.titles)
                        except:
                            current_titles = []
                    
                    if achievement.reward_title not in current_titles:
                        current_titles.append(achievement.reward_title)
                        db_user.titles = json.dumps(current_titles)
                    
                    # Set as active title if user doesn't have one, or this is a higher tier
                    if not db_user.title or achievement.tier in ['platinum', 'gold']:
                        db_user.title = achievement.reward_title
                    
                    session.commit()
            except Exception as e:
                session.rollback()
                print(f"Error setting title: {e}")
            finally:
                session.close()
    
    def notify_achievement_unlocked(self, user_id, achievement):
        """
        Send notification to user about unlocked achievement
        
        Args:
            user_id: Telegram ID of user
            achievement: Achievement object
        """
        tier_emoji = {
            'bronze': '🥉',
            'silver': '🥈',
            'gold': '🥇',
            'platinum': '💎'
        }
        
        message = f"""
🎉 **ACHIEVEMENT SBLOCCATO!** 🎉

{tier_emoji.get(achievement.tier, '🏆')} **{achievement.name}**
_{achievement.description}_

{achievement.flavor_text or ''}

**Ricompense:**
"""
        
        if achievement.reward_points:
            message += f"\n💰 +{achievement.reward_points} Wumpa Coins"
        
        if achievement.reward_title:
            message += f"\n👑 Titolo: {achievement.reward_title}"
        
        if achievement.cosmetic_reward:
            message += f"\n✨ {achievement.cosmetic_reward}"
        
        # Send via Telegram bot
        try:
            # Import bot instance from main
            import main
            if hasattr(main, 'bot'):
                main.bot.send_message(user_id, message, parse_mode='markdown')
            else:
                print(f"Achievement notification for user {user_id}:")
                print(message)
        except Exception as e:
            print(f"Error sending achievement notification: {e}")
            print(f"Achievement notification for user {user_id}:")
            print(message)
    
    def get_user_achievements(self, user_id):
        """
        Get all achievements for a user
        
        Args:
            user_id: Telegram ID of user
            
        Returns:
            List of dictionaries with achievement data
        """
        session = self.db.get_session()
        try:
            user_achievements = session.query(UserAchievement, Achievement).join(
                Achievement, UserAchievement.achievement_id == Achievement.id
            ).filter(
                UserAchievement.user_id == user_id
            ).all()
            
            result = []
            for user_ach, ach in user_achievements:
                result.append({
                    'achievement': ach,
                    'progress': user_ach.current_progress,
                    'max_progress': ach.max_progress,
                    'is_completed': user_ach.is_completed,
                    'completion_date': user_ach.completion_date,
                    'times_earned': user_ach.times_earned
                })
            
            return result
        finally:
            session.close()

    def get_all_achievements_with_progress(self, user_id):
        """
        Get all available achievements with user progress if any
        """
        session = self.db.get_session()
        try:
            all_ach = session.query(Achievement).all()
            user_ach = {ua.achievement_id: ua for ua in session.query(UserAchievement).filter_by(user_id=user_id).all()}
            
            result = []
            for ach in all_ach:
                ua = user_ach.get(ach.id)
                result.append({
                    'achievement': ach,
                    'progress': ua.current_progress if ua else 0,
                    'max_progress': ach.max_progress,
                    'is_completed': ua.is_completed if ua else False,
                    'completion_date': ua.completion_date if ua else None,
                    'times_earned': ua.times_earned if ua else 0
                })
            return result
        finally:
            session.close()
    
    def get_achievement_stats(self, user_id):
        """
        Get achievement statistics for a user
        
        Args:
            user_id: Telegram ID of user
            
        Returns:
            Dictionary with stats
        """
        session = self.db.get_session()
        try:
            total_achievements = session.query(Achievement).count()
            user_completed = session.query(UserAchievement).filter(
                UserAchievement.user_id == user_id,
                UserAchievement.is_completed == True
            ).count()
            
            total_points = session.query(Achievement).join(
                UserAchievement, Achievement.id == UserAchievement.achievement_id
            ).filter(
                UserAchievement.user_id == user_id,
                UserAchievement.is_completed == True
            ).with_entities(Achievement.reward_points).all()
            
            points_earned = sum(p[0] or 0 for p in total_points)
            
            return {
                'total_achievements': total_achievements,
                'completed': user_completed,
                'completion_rate': (user_completed / total_achievements * 100) if total_achievements > 0 else 0,
                'points_earned': points_earned
            }
        finally:
            session.close()
