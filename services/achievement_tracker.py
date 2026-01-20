"""
Achievement Tracker Service - Tracks and awards achievements based on game events.
"""

from database import Database
from models.achievements import Achievement, UserAchievement
from models.stats import UserStat
from services.event_dispatcher import EventDispatcher
from services.stat_aggregator import StatAggregator
import json
import datetime

class AchievementTracker:
    """
    Manages achievement checks and unlocks based on UserStats.
    """
    
    def __init__(self):
        self.db = Database()
        self.event_dispatcher = EventDispatcher()
        self.stat_aggregator = StatAggregator()
        
    def process_pending_events(self, limit=100):
        """
        Main loop:
        1. Fetch unprocessed events
        2. Aggregate them into UserStats
        3. Check for new achievement unlocks
        """
        while True:
            # 1. Fetch
            events = self.event_dispatcher.get_unprocessed_events(limit)
            if not events:
                break
                
            # 2. Aggregate
            self.stat_aggregator.process_events(events)
            
            # 3. Check Achievements for affected users
            affected_user_ids = set(e.user_id for e in events)
            for user_id in affected_user_ids:
                self.check_achievements(user_id)
            
            # If we fetched fewer than limit, we are done
            if len(events) < limit:
                break

    def check_achievements(self, user_id):
        """
        Check all achievements for a user against their current stats.
        """
        session = self.db.get_session()
        rewards_to_award = []
        try:
            # Get all achievements
            all_achievements = session.query(Achievement).all()
            
            # Get user stats (cache in dict for performance)
            user_stats = session.query(UserStat).filter_by(user_id=user_id).all()
            stats_map = {s.stat_key: s.value for s in user_stats}
            
            for achievement in all_achievements:
                self._check_single_achievement(session, user_id, achievement, stats_map, rewards_to_award)
            
            session.commit()
        except Exception as e:
            print(f"[ERROR] Achievement check failed for user {user_id}: {e}")
            session.rollback()
        finally:
            session.close()
            
        # Apply rewards AFTER session is closed to avoid locks
        for reward_data in rewards_to_award:
            self._apply_reward(user_id, reward_data)

    def _check_single_achievement(self, session, user_id, achievement, stats_map, rewards_to_award):
        """
        Check if a specific achievement should be unlocked or upgraded.
        """
        current_val = stats_map.get(achievement.stat_key, 0)
        
        # Get user's current progress
        user_ach = session.query(UserAchievement).filter_by(
            user_id=user_id, 
            achievement_key=achievement.achievement_key
        ).first()
        
        if not user_ach:
            user_ach = UserAchievement(
                user_id=user_id,
                achievement_key=achievement.achievement_key,
                current_tier=None,
                progress_value=current_val
            )
            session.add(user_ach)
        
        # Update progress snapshot
        user_ach.progress_value = current_val
        user_ach.last_progress_update = datetime.datetime.now()
        
        # Check Tiers
        try:
            tiers = json.loads(achievement.tiers)
        except:
            tiers = {}
            
        unlocked_tier = user_ach.current_tier
        
        # Define tier order for comparison
        tier_order = ['bronze', 'silver', 'gold', 'platinum', 'diamond', 'legendary']
        
        for tier_name in tier_order:
            if tier_name not in tiers:
                continue
                
            tier_data = tiers[tier_name]
            threshold = tier_data.get('threshold', 0)
            
            # Check condition
            is_met = False
            if achievement.condition_type == '>=':
                is_met = current_val >= threshold
            elif achievement.condition_type == '<=':
                is_met = current_val <= threshold
            elif achievement.condition_type == '==':
                is_met = current_val == threshold
                
            if is_met:
                # If this tier is higher than current, unlock it
                if self._is_higher_tier(tier_name, unlocked_tier, tier_order):
                    unlocked_tier = tier_name
                    # Collect reward data
                    rewards_to_award.append({
                        'achievement_name': achievement.name,
                        'achievement_description': achievement.description,
                        'tier_name': tier_name,
                        'tier_data': tier_data
                    })
        
        if unlocked_tier != user_ach.current_tier:
            user_ach.current_tier = unlocked_tier
            user_ach.unlocked_at = datetime.datetime.now()

    def _is_higher_tier(self, new_tier, current_tier, order):
        if current_tier is None:
            return True
        try:
            return order.index(new_tier) > order.index(current_tier)
        except ValueError:
            return False

    def _apply_reward(self, user_id, reward_data):
        """
        Grant rewards and notify user.
        """
        achievement_name = reward_data['achievement_name']
        achievement_description = reward_data['achievement_description']
        tier_name = reward_data['tier_name']
        tier_data = reward_data['tier_data']
        rewards = tier_data.get('rewards', {})
        
        # Notification message
        msg = f"🏆 **Achievement Sbloccato!**\n\n"
        msg += f"**{achievement_name}** ({tier_name.capitalize()})\n"
        msg += f"_{achievement_description}_\n\n"
        
        if 'exp' in rewards:
            exp_amount = rewards['exp']
            msg += f"➕ {exp_amount} EXP\n"
            try:
                from services.user_service import UserService
                user_service = UserService()
                user_service.add_exp_by_id(user_id, exp_amount)
            except Exception as e:
                print(f"[ERROR] Failed to award achievement EXP: {e}")
            
        if 'title' in rewards:
            title_text = rewards['title']
            msg += f"🏷️ Titolo: **{title_text}**\n"
            try:
                # Ensure user_service is initialized (might be already if exp was awarded)
                if 'user_service' not in locals():
                    from services.user_service import UserService
                    user_service = UserService()
                user_service.add_title(user_id, title_text)
            except Exception as e:
                print(f"[ERROR] Failed to add title: {e}")
            
        # Send notification (using main.bot via import inside function to avoid circular dep)
        try:
            import main
            if hasattr(main, 'bot'):
                # Private notification
                main.bot.send_message(user_id, msg, parse_mode='markdown')
                
                # Public announcement in official group
                # Get user name
                from services.user_service import UserService
                user_service = UserService()
                user = user_service.get_user(user_id)
                username = user.username if user and user.username else (user.nome if user else "Un utente")
                
                public_msg = f"🏆 **ACHIEVEMENT SBLOCCATO!** 🏆\n\n"
                public_msg += f"👤 **{username}** ha sbloccato:\n"
                public_msg += f"✨ **{achievement_name}** ({tier_name.capitalize()})\n"
                public_msg += f"_{achievement_description}_"
                
                from settings import GRUPPO_AROMA
                main.bot.send_message(GRUPPO_AROMA, public_msg, parse_mode='markdown')
        except Exception as e:
            print(f"[WARNING] Could not send notification: {e}")

    def on_chat_exp(self, user_id: int, total_chat_exp: int, increment: int = 0):
        value = increment if increment > 0 else total_chat_exp
        context = {"total_chat_exp": total_chat_exp}
        
        self.event_dispatcher.log_event(
            event_type="chat_exp",
            user_id=user_id,
            value=value,
            context=context
        )

    def get_user_achievements(self, user_id):
        """
        Get all achievements for a user (Adapted for new schema)
        """
        session = self.db.get_session()
        try:
            # Join on achievement_key
            user_achievements = session.query(UserAchievement, Achievement).join(
                Achievement, UserAchievement.achievement_key == Achievement.achievement_key
            ).filter(
                UserAchievement.user_id == user_id
            ).all()
            
            result = []
            for user_ach, ach in user_achievements:
                try:
                    tiers = json.loads(ach.tiers)
                except:
                    tiers = {}
                
                # Determine next tier threshold
                current_tier = user_ach.current_tier
                next_tier = 'bronze'
                if current_tier == 'bronze': next_tier = 'silver'
                elif current_tier == 'silver': next_tier = 'gold'
                elif current_tier == 'gold': next_tier = None
                
                max_prog = 0
                if next_tier and next_tier in tiers:
                    max_prog = tiers[next_tier].get('threshold', 0)
                
                result.append({
                    'key': ach.achievement_key,
                    'name': ach.name,
                    'description': ach.description,
                    'current_tier': user_ach.current_tier,
                    'progress': user_ach.progress_value,
                    'next_threshold': max_prog,
                    'unlocked_at': user_ach.unlocked_at
                })
            return result
        finally:
            session.close()

    def get_achievement_stats(self, user_id):
        """
        Get achievement statistics for a user
        """
        session = self.db.get_session()
        try:
            total_achievements = session.query(Achievement).count()
            
            # Count unlocked achievements (at least bronze)
            user_achievements = session.query(UserAchievement, Achievement).join(
                Achievement, UserAchievement.achievement_key == Achievement.achievement_key
            ).filter(
                UserAchievement.user_id == user_id,
                UserAchievement.current_tier != None
            ).all()
            
            user_unlocked = len(user_achievements)
            
            # Calculate points earned
            # Bronze: 10, Silver: 25, Gold: 50, Platinum: 100, Diamond: 250, Legendary: 500
            tier_points = {
                'bronze': 10, 'silver': 25, 'gold': 50, 
                'platinum': 100, 'diamond': 250, 'legendary': 500
            }
            
            points_earned = 0
            tier_order = ['bronze', 'silver', 'gold', 'platinum', 'diamond', 'legendary']
            
            for ua, ach in user_achievements:
                if ua.current_tier in tier_points:
                    # Sum points for all tiers up to the current one
                    try:
                        idx = tier_order.index(ua.current_tier)
                        for i in range(idx + 1):
                            points_earned += tier_points[tier_order[i]]
                    except ValueError:
                        points_earned += tier_points.get(ua.current_tier, 0)

            return {
                'total_achievements': total_achievements,
                'completed': user_unlocked,
                'points_earned': points_earned,
                'completion_rate': (user_unlocked / total_achievements * 100) if total_achievements > 0 else 0
            }
        finally:
            session.close()

    def get_all_achievements_with_progress(self, user_id, category=None):
        """
        Get all available achievements with user progress, adapted for main.py UI.
        """
        session = self.db.get_session()
        try:
            query = session.query(Achievement)
            if category:
                query = query.filter_by(category=category)
            all_ach = query.all()
            user_ach_map = {ua.achievement_key: ua for ua in session.query(UserAchievement).filter_by(user_id=user_id).all()}
            
            result = []
            tier_order = ['bronze', 'silver', 'gold', 'platinum', 'diamond', 'legendary']
            
            for ach in all_ach:
                ua = user_ach_map.get(ach.achievement_key)
                
                # Parse tiers
                try:
                    tiers = json.loads(ach.tiers)
                except:
                    tiers = {}
                
                current_tier = ua.current_tier if ua else None
                current_progress = ua.progress_value if ua else 0
                
                # Determine target tier (the next one to unlock)
                target_tier = 'bronze'
                if current_tier:
                    try:
                        curr_idx = tier_order.index(current_tier)
                        # Find the first tier in tier_order that is AFTER current_tier AND exists in tiers
                        found_next = False
                        for i in range(curr_idx + 1, len(tier_order)):
                            t_name = tier_order[i]
                            if t_name in tiers:
                                target_tier = t_name
                                found_next = True
                                break
                        
                        if not found_next:
                            target_tier = current_tier # Truly maxed
                    except ValueError:
                        target_tier = 'bronze'
                else:
                    # If no tier unlocked, find the first available tier in tier_order
                    for t_name in tier_order:
                        if t_name in tiers:
                            target_tier = t_name
                            break
                
                # Check if fully completed (Max tier unlocked)
                is_maxed = False
                if current_tier == target_tier and current_tier in tiers:
                    # We are at the target, check if there is a next one
                    # Actually logic above sets target=current if maxed
                    # So if target == current, we are likely maxed, UNLESS we are at None (start)
                    if current_tier is not None:
                        is_maxed = True
                
                # Set attributes for main.py compatibility
                # We modify the object instance - this is safe as long as we don't commit
                ach.tier = target_tier
                ach.max_progress = tiers.get(target_tier, {}).get('threshold', 1)
                
                # If maxed, we want to show as completed
                is_completed = is_maxed
                
                # If not maxed, we are working towards target_tier
                # main.py uses is_completed to decide whether to show progress bar
                
                result.append({
                    'achievement': ach,
                    'is_completed': is_completed,
                    'progress': current_progress
                })
                
            return result
        finally:
            session.close()
