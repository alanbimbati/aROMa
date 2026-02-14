"""
Achievement Tracker Service - Tracks and awards achievements based on game events.
"""

from database import Database
from models.achievements import Achievement, UserAchievement
from models.stats import UserStat
from services.event_dispatcher import EventDispatcher
from services.stat_aggregator import StatAggregator
import json
import os
from datetime import datetime

# Dynamic path resolution
SERVICE_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(SERVICE_DIR)

class AchievementTracker:
    """
    Manages achievement checks and unlocks based on UserStats.
    """
    
    def __init__(self):
        self.db = Database()
        self.event_dispatcher = EventDispatcher()
        self.stat_aggregator = StatAggregator()
        
    def load_from_csv(self, csv_path=None):
        """Load achievements from a CSV file, updating the database."""
        import csv
        
        if csv_path is None:
            csv_path = os.path.join(BASE_DIR, "data", "achievements.csv")
        
        if not os.path.exists(csv_path):
            print(f"[AchievementTracker] CSV file not found: {csv_path}")
            return

        print(f"[AchievementTracker] Loading achievements from {csv_path}...")
        session = self.db.get_session()
        try:
            with open(csv_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                count = 0
                for row in reader:
                    key = row['key']
                    name = row['name']
                    description = row['description']
                    stat_key = row['stat_key']
                    category = row['category']
                    tiers_str = row['tiers']
                    
                    # Validate JSON
                    try:
                        json.loads(tiers_str)
                    except json.JSONDecodeError as e:
                        print(f"[AchievementTracker] Error parsing JSON for {key}: {e}")
                        continue

                    ach = session.query(Achievement).filter_by(achievement_key=key).first()
                    if not ach:
                        ach = Achievement(
                            achievement_key=key,
                            name=name,
                            description=description,
                            stat_key=stat_key,
                            category=category,
                            tiers=tiers_str
                        )
                        session.add(ach)
                    else:
                        ach.name = name
                        ach.description = description
                        ach.stat_key = stat_key
                        ach.category = category
                        ach.tiers = tiers_str
                    
                    count += 1
                
                session.commit()
                print(f"[AchievementTracker] Successfully processed {count} achievements.")
                
        except Exception as e:
            print(f"[AchievementTracker] Error loading CSV: {e}")
            session.rollback()
        finally:
            session.close()
        
    def load_from_json(self, json_path=None):
        """Load achievements from a JSON file, updating the database."""
        if json_path is None:
            json_path = os.path.join(BASE_DIR, "data", "achievements.json")
        
        if not os.path.exists(json_path):
            print(f"[AchievementTracker] JSON file not found: {json_path}")
            return

        print(f"[AchievementTracker] Loading achievements from {json_path}...")
        session = self.db.get_session()
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                count = 0
                for item in data:
                    key = item.get('achievement_key')
                    if not key: continue

                    ach = session.query(Achievement).filter_by(achievement_key=key).first()
                    
                    # Extract fields
                    name = item.get('name')
                    description = item.get('description')
                    stat_key = item.get('stat_key')
                    category = item.get('category')
                    tiers_str = item.get('tiers')
                    
                    if isinstance(tiers_str, dict):
                        tiers_str = json.dumps(tiers_str)
                    
                    if not ach:
                        ach = Achievement(
                            achievement_key=key,
                            name=name,
                            description=description,
                            stat_key=stat_key,
                            category=category,
                            tiers=tiers_str
                        )
                        session.add(ach)
                    else:
                        ach.name = name
                        ach.description = description
                        ach.stat_key = stat_key
                        ach.category = category
                        ach.tiers = tiers_str
                    
                    count += 1
                
                session.commit()
                print(f"[AchievementTracker] Successfully processed {count} achievements from JSON.")
                
        except Exception as e:
            print(f"[AchievementTracker] Error loading JSON: {e}")
            session.rollback()
        finally:
            session.close()

    def process_pending_events(self, limit=100, session=None):
        """
        Main loop:
        1. Fetch unprocessed events
        2. Aggregate them into UserStats
        3. Check for new achievement unlocks
        """
        while True:
            # 1. Fetch
            events = self.event_dispatcher.get_unprocessed_events(limit, session=session)
            if not events:
                break
                
            # 2. Aggregate
            self.stat_aggregator.process_events(events, session=session)
            
            # 3. Check Achievements for affected users
            affected_user_ids = set(e.user_id for e in events)
            for user_id in affected_user_ids:
                self.check_achievements(user_id, session=session)
            
            # If we fetched fewer than limit, we are done
            if len(events) < limit:
                break

    def sync_live_stats(self, user_id):
        """
        Synchronize 'live' stats from Utente table to UserStat table.
        This ensures achievements like 'level_master' are up to date even if events were missed.
        """
        from models.user import Utente
        session = self.db.get_session()
        try:
            user = session.query(Utente).filter_by(id_telegram=user_id).first()
            if user:
                # Sync Level
                level_stat = session.query(UserStat).filter_by(user_id=user_id, stat_key='level').first()
                if not level_stat or level_stat.value != user.livello:
                    if level_stat:
                        level_stat.value = user.livello
                    else:
                        level_stat = UserStat(user_id=user_id, stat_key='level', value=user.livello)
                        session.add(level_stat)
                    
                    session.commit()
                    # Re-check achievements since level changed
                    self.check_achievements(user_id)
                
                # Initialize one_shots stat if missing (can't retroactively calculate, but enable future tracking)
                one_shots_stat = session.query(UserStat).filter_by(user_id=user_id, stat_key='one_shots').first()
                if not one_shots_stat:
                    one_shots_stat = UserStat(user_id=user_id, stat_key='one_shots', value=0)
                    session.add(one_shots_stat)
                    session.commit()
        except Exception as e:
            print(f"[ERROR] Live stat sync failed for user {user_id}: {e}")
            session.rollback()
        finally:
            session.close()

    def check_achievements(self, user_id, session=None):
        """
        Check all achievements for a user against their current stats.
        """
        local_session = False
        if not session:
            session = self.db.get_session()
            local_session = True
            
        rewards_to_award = []
        try:
            # CHECK: Does user exist?
            from models.user import Utente
            user_exists = session.query(Utente).filter_by(id_telegram=user_id).first()
            if not user_exists:
                # If user doesn't exist, we shouldn't award achievements
                return
            
            # Get all achievements
            all_achievements = session.query(Achievement).all()
            
            # Get user stats (cache in dict for performance)
            user_stats = session.query(UserStat).filter_by(user_id=user_id).all()
            stats_map = {s.stat_key: s.value for s in user_stats}
            
            # Pre-fetch user achievements to avoid N+1 queries and reduce race conditions
            user_achievements = session.query(UserAchievement).filter_by(user_id=user_id).all()
            user_ach_map = {ua.achievement_key: ua for ua in user_achievements}
            
            for achievement in all_achievements:
                self._check_single_achievement(session, user_id, achievement, stats_map, rewards_to_award, user_ach_map)
            
            if local_session:
                session.commit()
            else:
                session.flush()
        except Exception as e:
            print(f"[ERROR] Achievement check failed for user {user_id}: {e}")
            if local_session:
                session.rollback()
        finally:
            if local_session:
                session.close()
            
        # Apply rewards AFTER session check (and potential flush/commit)
        # Note: If local_session was False, the session is still open but flushed.
        # We should pass it along if it's still alive.
        for reward_data in rewards_to_award:
            self._apply_reward(user_id, reward_data, session=session if not local_session else None)

    def _check_single_achievement(self, session, user_id, achievement, stats_map, rewards_to_award, user_ach_map=None):
        """
        Check if a specific achievement should be unlocked or upgraded.
        """
        if achievement.stat_key == 'botanist_unique_count':
            # Custom logic for unique herbs
            # Count keys in stats_map that start with 'discovery_' and have value > 0
            count = 0
            for k, v in stats_map.items():
                if k.startswith('discovery_') and v > 0:
                    count += 1
            current_val = count
        else:
            current_val = stats_map.get(achievement.stat_key, 0)
        
        # Get user's current progress
        user_ach = None
        if user_ach_map:
            user_ach = user_ach_map.get(achievement.achievement_key)
        else:
            # Fallback for legacy calls
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
            # Add to map if provided to avoid re-adding if called multiple times in same context (unlikely but safe)
            if user_ach_map is not None:
                user_ach_map[achievement.achievement_key] = user_ach
            
            session.add(user_ach)
        
        # Update progress snapshot
        user_ach.progress_value = current_val
        user_ach.last_progress_update = datetime.now()
        
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
            user_ach.unlocked_at = datetime.now()

    def _is_higher_tier(self, new_tier, current_tier, order):
        if current_tier is None:
            return True
        try:
            return order.index(new_tier) > order.index(current_tier)
        except ValueError:
            return False

    def _apply_reward(self, user_id, reward_data, session=None):
        """
        Grant rewards and notify user.
        """
        # Ensure user_service is initialized
        from services.user_service import UserService
        user_service = UserService()
        
        # CHECK: Does user exist in 'utente' table?
        user = user_service.get_user(user_id, session=session)
        if not user:
            print(f"[REWARD] Skipping reward for non-existent user {user_id}")
            return
            
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
                user_service.add_exp_by_id(user_id, exp_amount, session=session)
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
                user_service.add_title(user_id, title_text, session=session)
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
            err_msg = str(e).lower()
            if any(x in err_msg for x in ["chat not found", "bot was blocked", "user is deactivated", "bot can't initiate"]):
                # Intentionally silent for common inactive user cases
                pass
            else:
                print(f"[WARNING] Could not send notification to {user_id}: {e}")

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
                
                # Get current title if any
                current_title = None
                if current_tier and current_tier in tiers:
                    current_title = tiers[current_tier].get('rewards', {}).get('title')

                result.append({
                    'key': ach.achievement_key,
                    'name': ach.name,
                    'description': ach.description,
                    'current_tier': user_ach.current_tier,
                    'title': current_title, # The specific reward title
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
        self.sync_live_stats(user_id)
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
        self.sync_live_stats(user_id)
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
