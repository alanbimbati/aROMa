import random
from settings import PointsName
from services.status_effects import StatusEffect
from models.user import Utente

class RewardService:
    def __init__(self, db, user_service, item_service, season_manager):
        self.db = db
        self.user_service = user_service
        self.item_service = item_service
        self.season_manager = season_manager

    def calculate_rewards(self, mob, participants):
        """
        Calculate rewards for a mob kill.
        
        Args:
            mob: The Mob object
            participants: List of CombatParticipation objects (or similar objects with .user_id, .damage_dealt)
            
        Returns:
            List of dictionaries containing reward info for each participant
        """
        total_damage = sum(p.damage_dealt for p in participants)
        if total_damage <= 0:
            return []

        rewards = []
        difficulty = mob.difficulty_tier if mob.difficulty_tier else 1
        
        # Difficulty Multiplier (can be adjusted if needed, currently linear based on PveService logic)
        # Old logic: wumpa = damage * 0.05 * difficulty
        # Old logic: xp = random(100, 300) * difficulty * share
        
        base_xp_pool = random.randint(100, 300) * difficulty

        for p in participants:
            share = p.damage_dealt / total_damage
            
            # Wumpa (Points) calculation
            wumpa = int(p.damage_dealt * 0.05 * difficulty)
            if wumpa < 1: wumpa = 1

            # XP calculation
            xp = int(base_xp_pool * share)
            if xp < 1: xp = 1
            
            # Turbo Bonus check (needs User object or flag passed, let's assume we handle it in distribution or here if we fetch user)
            # For simplicity, we calculate base here. Modifiers can be applied in distribute or if we fetch users here.
            # Let's keep it simple: return base values, fetch user in distribute to apply multipliers/status checks?
            # Or better: fetch user here to check for 'stun' or 'dead' status which affects rewards (0 rewards).
            
            rewards.append({
                'user_id': p.user_id,
                'base_xp': xp,
                'base_wumpa': wumpa,
                'damage_dealt': p.damage_dealt,
                'share': share
            })
            
        return rewards

    def distribute_rewards(self, rewards_data, mob, session):
        """
        Apply rewards to users and generate a summary report.
        """
        summary_lines = []
        total_wumpa_distributed = 0
        
        for reward in rewards_data:
            user_id = reward['user_id']
            xp = reward['base_xp']
            wumpa = reward['base_wumpa']
            damage = reward['damage_dealt']
            
            # Use session to query user
            user = session.query(Utente).filter_by(id_telegram=user_id).first()
            if not user:
                continue

            # Check status (e.g. Dead users get nothing? Or just reduced?)
            # PveService logic: if dead (HP<=0) -> 0 rewards.
            # If stunned -> 0 rewards (unless we want to change this policy, but sticking to existing logic for now)
            
            is_dead = (user.health <= 0)
            is_stunned = StatusEffect.has_effect(user, 'stun')
            
            if is_dead or is_stunned:
                xp = 0
                wumpa = 0
            
            # Turbo Bonus
            if getattr(user, 'has_turbo', False):
                 xp = int(xp * 1.2)
                 
            # Apply XP
            level_up_info = self.user_service.add_exp_by_id(user_id, xp, session=session)
            
            # Apply Points
            self.user_service.add_points_by_id(user_id, wumpa, is_drop=True, session=session)
            total_wumpa_distributed += wumpa
            
            # Seasonal XP
            self.season_manager.add_seasonal_exp(user_id, xp, session=session)
            
            # Item Drops
            item_msg = self._handle_item_drop(user_id, mob.is_boss, session=session)
            
            # Format Message
            user_name = user.game_name or user.nome or f"User {user_id}"
            line = f"👤 **{user_name}**: {damage} dmg -> {xp} Exp, {wumpa} {PointsName}"
            
            if is_dead:
                line += " 💀 (Morto)"
            elif is_stunned:
                line += " 💫 (Stordito)"
                
            if level_up_info['leveled_up']:
                line += f"\n   🎉 **LEVEL UP!** {level_up_info['new_level']}!"
            
            if item_msg:
                line += f"\n   {item_msg}"
                
            summary_lines.append(line)
            
            # Recalculate stats if needed
            if user.health > user.max_health:
                 self.user_service.recalculate_stats(user_id, session=session)

        header = f"💰 **Ricompense Distribuite!** ({total_wumpa_distributed} {PointsName} totali)"
        return header + "\n" + "\n".join(summary_lines)

    def _handle_item_drop(self, user_id, is_boss, session=None):
        chance = 0.30 if is_boss else 0.10
        if random.random() < chance:
            items_data = self.item_service.load_items_from_csv()
            if items_data:
                weights = [1/float(item['rarita']) for item in items_data]
                reward_item = random.choices(items_data, weights=weights, k=1)[0]
                self.item_service.add_item(user_id, reward_item['nome'], session=session)
                return f"✨ Oggetto: **{reward_item['nome']}**"
        return None

    def distribute_aggregated_rewards(self, mobs_rewards_map, session):
        """
        Distribute rewards for multiple mobs (AoE).
        mobs_rewards_map: dict of mob -> rewards_data list
        """
        aggregated_users = {} # user_id -> {'xp': 0, 'wumpa': 0, 'items': []}
        
        total_xp_global = 0
        total_wumpa_global = 0
        
        for mob, rewards_data in mobs_rewards_map.items():
            for reward in rewards_data:
                user_id = reward['user_id']
                xp = reward['base_xp']
                wumpa = reward['base_wumpa']
                
                if user_id not in aggregated_users:
                    aggregated_users[user_id] = {'xp': 0, 'wumpa': 0, 'items': [], 'name': ""}
                
                aggregated_users[user_id]['xp'] += xp
                aggregated_users[user_id]['wumpa'] += wumpa
                
                # Items
                item_msg = self._handle_item_drop(user_id, mob.is_boss, session=session)
                if item_msg:
                    aggregated_users[user_id]['items'].append(item_msg)

        summary_lines = []
        
        for user_id, data in aggregated_users.items():
            amount_xp = data['xp']
            amount_wumpa = data['wumpa']
            
            # Use session to query user if provided
            user = session.query(Utente).filter_by(id_telegram=user_id).first()
            if not user: continue
            
            is_dead = (user.health <= 0)
            is_stunned = StatusEffect.has_effect(user, 'stun')
            
            if is_dead or is_stunned:
                amount_xp = 0
                amount_wumpa = 0
            
            if getattr(user, 'has_turbo', False):
                 amount_xp = int(amount_xp * 1.2)
            
            # Application
            level_up_info = self.user_service.add_exp_by_id(user_id, amount_xp, session=session)
            self.user_service.add_points_by_id(user_id, amount_wumpa, is_drop=True, session=session)
            self.season_manager.add_seasonal_exp(user_id, amount_xp, session=session)
            
            total_xp_global += amount_xp
            total_wumpa_global += amount_wumpa
            
            # Format
            p_name = user.game_name or user.nome or f"User {user_id}"
            line = f"👤 **{p_name}**: +{amount_xp} Exp, +{amount_wumpa} {PointsName}"
            
            if is_dead: line += " 💀"
            elif is_stunned: line += " 💫"
            
            if level_up_info['leveled_up']:
                line += f"\n   🎉 **LEVEL UP!** {level_up_info['new_level']}!"
                
            for item in data['items']:
                line += f"\n   {item}"
                
            summary_lines.append(line)
            
            if user.health > user.max_health:
                 self.user_service.recalculate_stats(user_id, session=session)
                 
        header = f"💰 **Ricompense Totali per {len(mobs_rewards_map)} nemici!**"
        return header + "\n" + "\n".join(summary_lines)
