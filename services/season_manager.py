import datetime
import json
from database import Database
from models.seasons import Season, SeasonProgress, SeasonReward, SeasonClaimedReward
from models.user import Utente
from services.user_service import UserService
from services.character_service import CharacterService

class SeasonManager:
    """Manages seasonal progression and rewards"""
    
    MAX_RANK = 30        # Maximum seasonal rank
    
    def __init__(self):
        self.db = Database()
        self.user_service = UserService()
        self.character_service = CharacterService()
        
    def get_active_season(self):
        """Get the currently active season"""
        session = self.db.get_session()
        try:
            now = datetime.datetime.now()
            return session.query(Season).filter(
                Season.is_active == True,
                Season.start_date <= now,
                Season.end_date >= now
            ).first()
        finally:
            session.close()
            
    def get_or_create_progress(self, user_id, season_id):
        """Get or create user progress for a season"""
        session = self.db.get_session()
        try:
            progress = session.query(SeasonProgress).filter_by(
                user_id=user_id,
                season_id=season_id
            ).first()
            
            if not progress:
                # Check if user is premium globally
                user = self.user_service.get_user(user_id)
                is_premium = user.premium == 1 if user else False
                
                progress = SeasonProgress(
                    user_id=user_id,
                    season_id=season_id,
                    current_exp=0,
                    current_level=1,
                    has_premium_pass=is_premium, # Auto-grant if premium
                    last_update=datetime.datetime.now()
                )
                session.add(progress)
                session.commit()
                # Refresh to get ID
                session.refresh(progress)
            else:
                # Sync premium status if not already set
                if not progress.has_premium_pass:
                    user = self.user_service.get_user(user_id)
                    if user and user.premium == 1:
                        progress.has_premium_pass = True
                        session.commit()
                
            return progress
        finally:
            session.close()
            
    def add_seasonal_exp(self, user_id, amount):
        """Add EXP to user's seasonal progress. Returns (rewards, season_end_msg)"""
        season = self.get_active_season()
        if not season:
            return [], None
            
        session = self.db.get_session()
        try:
            progress = session.query(SeasonProgress).filter_by(
                user_id=user_id,
                season_id=season.id
            ).first()
            
            if not progress:
                progress = SeasonProgress(
                    user_id=user_id,
                    season_id=season.id,
                    current_exp=0,
                    current_level=1,
                    last_update=datetime.datetime.now()
                )
                session.add(progress)
            
            # Apply season multiplier
            amount = int(amount * season.exp_multiplier)
            progress.current_exp += amount
            progress.last_update = datetime.datetime.now()
            
            # Check for level up
            leveled_up = False
            
            # Dynamic EXP Curve: 100 * (current_rank ** 2)
            def get_exp_required(rank):
                return 100 * (rank ** 2)
                
            next_rank_exp = get_exp_required(progress.current_level)
            
            while progress.current_level < self.MAX_RANK and progress.current_exp >= next_rank_exp:
                progress.current_exp -= next_rank_exp
                progress.current_level += 1
                leveled_up = True
                print(f"User {user_id} reached seasonal Grado {progress.current_level}")
                # Update requirement for next loop
                next_rank_exp = get_exp_required(progress.current_level)
            
            # If at max rank, cap EXP
            if progress.current_level >= self.MAX_RANK:
                progress.current_exp = 0
                
            # session.commit() # Moved to end
            
            rewards = []
            season_end_msg = None
            
            if leveled_up:
                rewards = self.check_and_award_rewards(user_id, season.id, progress.current_level, session)
                
                # Check if reached max rank (Season End Condition)
                if progress.current_level >= self.MAX_RANK:
                    season_end_msg = self.end_season(season.id, user_id, session)
            
            session.commit()
            return rewards, season_end_msg
        except Exception as e:
            session.rollback()
            print(f"Error adding seasonal exp: {e}")
            return [], None
        finally:
            session.close()

    def end_season(self, season_id, winner_user_id, session=None):
        """End the season, calculate stats, award top 3, and return summary message"""
        close_session = False
        if session is None:
            session = self.db.get_session()
            close_session = True
            
        try:
            season = session.query(Season).filter_by(id=season_id).first()
            if not season or not season.is_active:
                return None
                
            # 1. Close Season
            season.is_active = False
            season.end_date = datetime.datetime.now()
            
            # Calculate Duration
            duration = season.end_date - season.start_date
            days = duration.days
            
            # 2. Get Top 3
            # We need to join with Utente to get names
            top_users = session.query(SeasonProgress, Utente).join(Utente, SeasonProgress.user_id == Utente.id_telegram)\
                .filter(SeasonProgress.season_id == season_id)\
                .order_by(SeasonProgress.current_level.desc(), SeasonProgress.current_exp.desc())\
                .limit(3).all()
                
            # 3. Award Wumpa and Build Message
            winner_user = self.user_service.get_user(winner_user_id)
            winner_name = winner_user.game_name or winner_user.nome or "Eroe"
            
            msg = f"\n🏆 **LA STAGIONE È TERMINATA!** 🏆\n\n"
            msg += f"🥇 **{winner_name}** ha raggiunto il Grado {self.MAX_RANK} e ha concluso la stagione!\n"
            msg += f"⏱️ Durata: {days} giorni\n\n"
            msg += "🏅 **CLASSIFICA FINALE**\n"
            
            prizes = [1000, 500, 200]
            emojis = ["🥇", "🥈", "🥉"]
            
            for i, (progress, user) in enumerate(top_users):
                prize = prizes[i] if i < len(prizes) else 0
                emoji = emojis[i] if i < len(emojis) else "🔸"
                name = user.game_name or user.nome or f"User {user.id_telegram}"
                
                # Award Prize
                # Update directly to avoid nested session
                user.points = int(user.points) + prize
                
                msg += f"{emoji} **{name}** - Grado {progress.current_level} (+{prize} 🍑)\n"
                
            if close_session:
                session.commit()
            else:
                # If sharing session, we might want to flush or commit here to ensure it saves?
                # Or let caller handle it. But caller (add_seasonal_exp) commits BEFORE calling this currently.
                # We will fix caller next.
                pass
            return msg
            return msg
            
        except Exception as e:
            print(f"Error ending season: {e}")
            if close_session:
                session.rollback()
            return None
        finally:
            if close_session:
                session.close()
            
    def check_and_award_rewards(self, user_id, season_id, current_level, session=None):
        """Check and award rewards up to current Grado"""
        close_session = False
        if session is None:
            session = self.db.get_session()
            close_session = True
            
        try:
            progress = session.query(SeasonProgress).filter_by(
                user_id=user_id,
                season_id=season_id
            ).first()
            
            if not progress:
                return []
                
            # Get all rewards for this season up to current rank
            rewards = session.query(SeasonReward).filter(
                SeasonReward.season_id == season_id,
                SeasonReward.level_required <= current_level
            ).all()
            
            unlocked_rewards = []
            for reward in rewards:
                # Check if user can get this reward (Free or Premium)
                if not reward.is_premium or progress.has_premium_pass:
                    # Check if already claimed
                    claimed = session.query(SeasonClaimedReward).filter_by(
                        user_id=user_id,
                        season_id=season_id,
                        reward_id=reward.id
                    ).first()
                    
                    if not claimed:
                        unlocked_rewards.append(reward)
                        self.award_reward(user_id, reward, session)
                        
                        # Mark as claimed
                        new_claim = SeasonClaimedReward(
                            user_id=user_id,
                            season_id=season_id,
                            reward_id=reward.id
                        )
                        session.add(new_claim)
                        # Don't commit here if using shared session, let caller commit
                        if close_session:
                            session.commit()
                    
            return unlocked_rewards
        finally:
            if close_session:
                session.close()
            
    def award_reward(self, user_id, reward, session=None):
        """Actually give the reward to the user"""
        print(f"Awarding reward to {user_id}: {reward.reward_name} ({reward.reward_type})")
        
        close_session = False
        if session is None:
            session = self.db.get_session()
            close_session = True
            
        try:
            if reward.reward_type == 'points':
                # Update directly to avoid nested session in user_service.add_points
                user = session.query(Utente).filter_by(id_telegram=user_id).first()
                if user:
                    user.points = int(user.points) + int(reward.reward_value)
                    if close_session:
                        session.commit()
                        
            elif reward.reward_type == 'character':
                # Unlock character for user
                char_id = int(reward.reward_value)
                from models.system import UserCharacter
                # Check if already owned
                owned = session.query(UserCharacter).filter_by(
                    user_id=user_id,
                    character_id=char_id
                ).first()
                
                if not owned:
                    new_ownership = UserCharacter(
                        user_id=user_id,
                        character_id=char_id,
                        obtained_at=datetime.date.today()
                    )
                    session.add(new_ownership)
                    if close_session:
                        session.commit()
                    print(f"Character {char_id} unlocked for user {user_id}")
        except Exception as e:
            if close_session:
                session.rollback()
            print(f"Error unlocking reward in season: {e}")
        finally:
            if close_session:
                session.close()
            
    def purchase_season_pass(self, user_id):
        """Purchase the season pass for 1000 Wumpa"""
        season = self.get_active_season()
        if not season:
            return False, "Nessuna stagione attiva."
            
        session = self.db.get_session()
        try:
            progress = self.get_or_create_progress(user_id, season.id)
            if progress.has_premium_pass:
                return False, "Possiedi già il Season Pass per questa stagione!"
                
            user = self.user_service.get_user(user_id)
            if user.points < 1000:
                return False, "Non hai abbastanza Wumpa! Il Season Pass costa 1000 🍑."
                
            # Deduct points
            self.user_service.add_points(user, -1000)
            
            # Update progress
            db_progress = session.query(SeasonProgress).filter_by(id=progress.id).first()
            db_progress.has_premium_pass = True
            
            # Also set user as premium globally
            db_user = session.query(Utente).filter_by(id_telegram=user_id).first()
            if db_user:
                db_user.premium = 1
                
            session.commit()
            
            # Check if any previous rewards should be awarded now
            self.check_and_award_rewards(user_id, season.id, db_progress.current_level)
            
            return True, "🎉 **SEASON PASS ATTIVATO!**\n\nHai sbloccato il track Premium e sei diventato un utente Premium globale! 👑"
        except Exception as e:
            session.rollback()
            print(f"Error purchasing season pass: {e}")
            return False, f"Errore durante l'acquisto: {e}"
        finally:
            session.close()

    def get_season_status(self, user_id):
        """Get current status of user in the season"""
        season = self.get_active_season()
        if not season:
            return None
            
        session = self.db.get_session()
        try:
            progress = session.query(SeasonProgress).filter_by(
                user_id=user_id,
                season_id=season.id
            ).first()
            
            if not progress:
                progress_data = {
                    'level': 1,
                    'exp': 0,
                    'has_premium': False
                }
            else:
                progress_data = {
                    'level': progress.current_level,
                    'exp': progress.current_exp,
                    'has_premium': progress.has_premium_pass
                }
                
                # Double check sync (visual only here, DB update happens in get_or_create or purchase)
                if not progress_data['has_premium']:
                     user = self.user_service.get_user(user_id)
                     if user and user.premium == 1:
                         progress_data['has_premium'] = True
                
            # Get next rewards
            next_rewards = session.query(SeasonReward).filter(
                SeasonReward.season_id == season.id,
                SeasonReward.level_required > progress_data['level']
            ).order_by(SeasonReward.level_required).limit(5).all()
            
            return {
                'season_name': season.name,
                'end_date': season.end_date,
                'progress': progress_data,
                'next_rewards': next_rewards,
                'exp_per_level': 100 * (progress_data['level'] ** 2) # Dynamic requirement for current rank
            }
        finally:
            session.close()

    def get_all_season_rewards(self, season_id):
        """Get all rewards for a specific season"""
        session = self.db.get_session()
        try:
            return session.query(SeasonReward).filter_by(season_id=season_id).order_by(SeasonReward.level_required).all()
        finally:
            session.close()
