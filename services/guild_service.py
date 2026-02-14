import datetime
import random
from database import Database
from models.guild import Guild, GuildMember, GuildUpgrade, GuildItem
from models.user import Utente
from sqlalchemy import func

class GuildService:
    def __init__(self):
        self.db = Database()

    def create_guild(self, leader_id, name, x=None, y=None):
        """Create a new guild if user meets requirements (lv10+, 1000 wumpa)"""
        session = self.db.get_session()
        user = session.query(Utente).filter_by(id_telegram=leader_id).first()
        
        if not user:
            session.close()
            return False, "Utente non trovato."
            
        if user.livello < 10:
            session.close()
            return False, "Devi essere almeno al livello 10 per fondare una gilda!", None
            
        if user.points < 1000:
            session.close()
            return False, "Ti servono 1000 Wumpa per fondare una gilda!", None
            
        # Check if name exists
        existing = session.query(Guild).filter(func.lower(Guild.name) == name.lower()).first()
        if existing:
            session.close()
            return False, f"Il nome '{name}' è già occupato!", None
            
        # Check if user is already in a guild
        in_guild = session.query(GuildMember).filter_by(user_id=leader_id).first()
        if in_guild:
            session.close()
            return False, "Fai già parte di una gilda!", None
            
        # Deduct cost
        user.points -= 1000
        
        # Create guild
        new_guild = Guild(
            name=name,
            leader_id=leader_id,
            map_x=x if x is not None else random.randint(0, 100),
            map_y=y if y is not None else random.randint(0, 100)
        )
        session.add(new_guild)
        session.flush() # Get guild ID
        
        # Add leader as member
        leader_member = GuildMember(
            guild_id=new_guild.id,
            user_id=leader_id,
            role="Leader"
        )
        session.add(leader_member)
        
        session.commit()
        guild_id = new_guild.id
        session.close()
        return True, f"Gilda '{name}' fondata con successo!", guild_id

    def get_user_guild(self, user_id):
        """Get the guild a user belongs to"""
        session = self.db.get_session()
        member = session.query(GuildMember).filter_by(user_id=user_id).first()
        if not member:
            session.close()
            return None
        guild = session.query(Guild).filter_by(id=member.guild_id).first()
        # We need to detach or keep session open. Detaching is better for simple apps.
        # But for now, let's just return a dict with data to avoid DetachedInstanceError.
        guild_data = {
            'id': guild.id,
            'name': guild.name,
            'leader_id': guild.leader_id,
            'wumpa_bank': guild.wumpa_bank,
            'member_limit': guild.member_limit,
            'inn_level': guild.inn_level,
            'armory_level': guild.armory_level,
            'village_level': guild.village_level,
            'map_y': guild.map_y,
            'role': member.role,
            'bordello_level': guild.bordello_level,
            'brewery_level': guild.brewery_level,
            'emblem': guild.emblem,
            'skin_id': guild.skin_id,
            'description': guild.description,
            'laboratory_level': guild.laboratory_level,
            'garden_level': guild.garden_level,
            'dragon_stables_level': guild.dragon_stables_level,
            'ancient_temple_level': guild.ancient_temple_level,
            'magic_library_level': guild.magic_library_level,
            'inn_image': guild.inn_image,
            'bordello_image': guild.bordello_image,
            'laboratory_image': guild.laboratory_image,
            'garden_image': guild.garden_image
        }
        session.close()
        return guild_data




    # --- Customization Methods ---
    def set_guild_emblem(self, leader_id, emblem):
        """Set guild emblem (Leader only)"""
        session = self.db.get_session()
        member = session.query(GuildMember).filter_by(user_id=leader_id, role="Leader").first()
        if not member:
            session.close()
            return False, "Solo il capogilda può impostare lo stemma!"
        
        guild = session.query(Guild).filter_by(id=member.guild_id).first()
        guild.emblem = emblem
        session.commit()
        session.close()
        return True, f"Stemma della gilda aggiornato: {emblem}"

    def set_guild_skin(self, leader_id, skin_id):
        """Set guild UI skin (Leader only)"""
        session = self.db.get_session()
        member = session.query(GuildMember).filter_by(user_id=leader_id, role="Leader").first()
        if not member:
            session.close()
            return False, "Solo il capogilda può impostare la skin!"
            
        guild = session.query(Guild).filter_by(id=member.guild_id).first()
        guild.skin_id = skin_id
        session.commit()
        session.close()
        return True, f"Skin della gilda aggiornata: {skin_id}"

    def set_guild_description(self, leader_id, description):
        """Set guild description (Leader only)"""
        session = self.db.get_session()
        member = session.query(GuildMember).filter_by(user_id=leader_id, role="Leader").first()
        if not member:
            session.close()
            return False, "Solo il capogilda può impostare la descrizione!"
            
        if len(description) > 500:
             session.close()
             return False, "Descrizione troppo lunga (max 500 caratteri)!"

        guild = session.query(Guild).filter_by(id=member.guild_id).first()
        guild.description = description
        session.commit()
        session.close()
        return True, "Descrizione della gilda aggiornata!"

    def get_dungeon_ranking(self, dungeon_id=None, limit=10):
        """Get guild damage ranking"""
        session = self.db.get_session()
        from models.guild_dungeon_stats import GuildDungeonStats
        
        query = session.query(Guild.name, func.sum(GuildDungeonStats.total_damage).label('total_damage'))\
            .join(GuildDungeonStats, Guild.id == GuildDungeonStats.guild_id)
            
        if dungeon_id:
            query = query.filter(GuildDungeonStats.dungeon_id == dungeon_id)
            
        ranking = query.group_by(Guild.id, Guild.name).order_by(func.sum(GuildDungeonStats.total_damage).desc()).limit(limit).all()
        
        result = [{'name': r[0], 'total_damage': r[1]} for r in ranking]
        session.close()
        return result

    def process_weekly_rewards(self):
        """Distribute rewards to top 3 guilds"""
        ranking = self.get_dungeon_ranking(limit=3)
        if not ranking:
            return "Nessuna attività di gilda rilevata questa settimana."
            
        session = self.db.get_session()
        rewards_log = []
        
        # 1st Place
        if len(ranking) >= 1:
            top_guild_name = ranking[0]['name']
            g1 = session.query(Guild).filter_by(name=top_guild_name).first()
            if g1:
                g1.wumpa_bank += 5000
                rewards_log.append(f"🥇 **{top_guild_name}**: 5000 Wumpa")
                
        # 2nd Place
        if len(ranking) >= 2:
            g2_name = ranking[1]['name']
            g2 = session.query(Guild).filter_by(name=g2_name).first()
            if g2:
                g2.wumpa_bank += 3000
                rewards_log.append(f"🥈 **{g2_name}**: 3000 Wumpa")
                
        # 3rd Place
        if len(ranking) >= 3:
            g3_name = ranking[2]['name']
            g3 = session.query(Guild).filter_by(name=g3_name).first()
            if g3:
                g3.wumpa_bank += 1500
                rewards_log.append(f"🥉 **{g3_name}**: 1500 Wumpa")

        session.commit()
        session.close()
        
        if not rewards_log:
            return None
            
        return "🏆 **Ricompense Settimanali Gilda (Dungeon)**\n\n" + "\n".join(rewards_log)


    def deposit_wumpa(self, user_id, amount):
        """Deposit wumpa into guild bank"""
        if amount <= 0:
            return False, "Importo non valido."
            
        session = self.db.get_session()
        user = session.query(Utente).filter_by(id_telegram=user_id).first()
        member = session.query(GuildMember).filter_by(user_id=user_id).first()
        
        if not member:
            session.close()
            return False, "Non fai parte di nessuna gilda!"
            
        if user.points < amount:
            session.close()
            return False, "Non hai abbastanza Wumpa!"
            
        guild = session.query(Guild).filter_by(id=member.guild_id).first()
        user.points -= amount
        guild.wumpa_bank += amount
        
        session.commit()
        session.close()
        return True, f"Hai depositato {amount} Wumpa nella banca della gilda!"

    def withdraw_wumpa(self, leader_id, amount):
        """Leader only: withdraw wumpa from guild bank"""
        if amount <= 0:
            return False, "Importo non valido."
            
        session = self.db.get_session()
        member = session.query(GuildMember).filter_by(user_id=leader_id, role="Leader").first()
        
        if not member:
            session.close()
            return False, "Solo il capogilda può prelevare fondi!"
            
        guild = session.query(Guild).filter_by(id=member.guild_id).first()
        if guild.wumpa_bank < amount:
            session.close()
            return False, "La banca della gilda non ha abbastanza fondi!"
            
        user = session.query(Utente).filter_by(id_telegram=leader_id).first()
        guild.wumpa_bank -= amount
        user.points += amount
        
        session.commit()
        session.close()
        return True, f"Hai prelevato {amount} Wumpa dalla banca della gilda!"

    def upgrade_inn(self, leader_id):
        """Upgrade the guild inn"""
        session = self.db.get_session()
        member = session.query(GuildMember).filter_by(user_id=leader_id, role="Leader").first()
        if not member:
            session.close()
            return False, "Solo il capogilda può gestire gli upgrade!"
            
        guild = session.query(Guild).filter_by(id=member.guild_id).first()
        cost = guild.inn_level * 500
        
        if guild.wumpa_bank < cost:
            session.close()
            return False, f"Servono {cost} Wumpa nella banca della gilda per questo upgrade!"
            
        guild.wumpa_bank -= cost
        guild.inn_level += 1
        new_level = guild.inn_level
        
        session.commit()
        session.close()
        return True, f"Locanda potenziata al livello {new_level}!"

    def expand_village(self, leader_id):
        """Expand the village to accept more members"""
        session = self.db.get_session()
        member = session.query(GuildMember).filter_by(user_id=leader_id, role="Leader").first()
        if not member:
            session.close()
            return False, "Solo il capogilda può gestire gli upgrade!"
            
        guild = session.query(Guild).filter_by(id=member.guild_id).first()
        
        if guild.village_level >= 5:
            session.close()
            return False, "Il Villaggio è già al livello massimo (Lv. 5)!"
            
        cost = guild.village_level * 1000
        
        if guild.wumpa_bank < cost:
            session.close()
            return False, f"Servono {cost} Wumpa nella banca della gilda per questo upgrade!"
            
        guild.wumpa_bank -= cost
        guild.village_level += 1
        guild.member_limit += 5
        new_limit = guild.member_limit
        
        session.commit()
        session.close()
        return True, f"Villaggio ampliato! Nuovo limite membri: {new_limit}."

    def upgrade_armory(self, leader_id):
        """Upgrade or build the armory"""
        session = self.db.get_session()
        member = session.query(GuildMember).filter_by(user_id=leader_id, role="Leader").first()
        if not member:
            session.close()
            return False, "Solo il capogilda può gestire gli upgrade!"
            
        guild = session.query(Guild).filter_by(id=member.guild_id).first()
        
        if guild.armory_level >= 5:
            session.close()
            return False, "L'Armeria è già al livello massimo (Lv. 5)!"
            
        cost = (guild.armory_level + 1) * 750
        
        if guild.wumpa_bank < cost:
            session.close()
            return False, f"Servono {cost} Wumpa nella banca della gilda per questo upgrade!"
            
        guild.wumpa_bank -= cost
        guild.armory_level += 1
        new_level = guild.armory_level
        
        session.commit()
        session.close()
        return True, f"Armeria potenziata al livello {new_level}!"

    def upgrade_brewery(self, leader_id):
        """Upgrade the brewery"""
        session = self.db.get_session()
        member = session.query(GuildMember).filter_by(user_id=leader_id, role="Leader").first()
        if not member:
            session.close()
            return False, "Solo il capogilda può gestire gli upgrade!"
            
        guild = session.query(Guild).filter_by(id=member.guild_id).first()
        
        # Initialize default if null (from new column)
        if guild.brewery_level is None: guild.brewery_level = 1
        
        if guild.brewery_level >= 5:
            session.close()
            return False, "Il Birrificio è già al livello massimo (Lv. 5)!"
            
        cost = (guild.brewery_level + 1) * 600
        
        if guild.wumpa_bank < cost:
            session.close()
            return False, f"Servono {cost} Wumpa nella banca della gilda per questo upgrade!"
            
        guild.wumpa_bank -= cost
        guild.brewery_level += 1
        new_level = guild.brewery_level
        
        session.commit()
        session.close()
        return True, f"Birrificio potenziato al livello {new_level}!"

    def upgrade_brothel(self, leader_id):
        """Build or Upgrade the brothel"""
        session = self.db.get_session()
        member = session.query(GuildMember).filter_by(user_id=leader_id, role="Leader").first()
        if not member:
            session.close()
            return False, "Solo il capogilda può gestire gli upgrade!"
            
        guild = session.query(Guild).filter_by(id=member.guild_id).first()
        
        if guild.bordello_level >= 5:
            session.close()
            return False, "Il Bordello delle Elfe è già al livello massimo (Lv. 5)!"
            
        # Cost: 2000 to build (Lv 0->1), then scaling
        if guild.bordello_level == 0:
            cost = 2000
        else:
            cost = (guild.bordello_level + 1) * 1000
        
        if guild.wumpa_bank < cost:
            session.close()
            return False, f"Servono {cost} Wumpa nella banca della gilda per questo upgrade!"
            
        guild.wumpa_bank -= cost
        guild.bordello_level += 1
        new_level = guild.bordello_level
        
        session.commit()
        session.close()
        if new_level == 1:
            return True, "👙 Hai costruito il **Bordello delle Elfe**! I tuoi membri ora possono ottenere il buff Vigore!"
        return True, f"Bordello potenziato al livello {new_level}!"

    def get_potion_bonus(self, user_id):
        """Get potion effectiveness bonus based on inn level (Active for 30 mins after beer)"""
        session = self.db.get_session()
        user = session.query(Utente).filter_by(id_telegram=user_id).first()
        if not user or not user.last_beer_usage:
            session.close()
            return 1.0
            
        # Check if 30 minutes have passed
        now = datetime.datetime.now()
        if (now - user.last_beer_usage).total_seconds() > 1800: # 30 mins
            session.close()
            return 1.0
            
        guild = self.get_user_guild(user_id)
        if not guild:
            session.close()
            return 1.0
            
        # Brewery bonus logic
        brew_level = guild.get('brewery_level', 1) or 1
        bonus_pct = 15 + (brew_level * 5)
        session.close()
        return 1.0 + (bonus_pct / 100.0)

    def buy_craft_beer(self, user_id):
        """Buy a craft beer for a fun bonus (and healing)"""
        session = self.db.get_session()
        user = session.query(Utente).filter_by(id_telegram=user_id).first()
        guild = self.get_user_guild(user_id)
        
        if not guild:
            session.close()
            return False, "Non fai parte di nessuna gilda!"
            
        # Daily limit check (reset at midnight)
        now = datetime.datetime.now()
        if user.last_beer_usage and user.last_beer_usage.date() == now.date():
             session.close()
             return False, "🍺 Hai già bevuto la tua birra giornaliera! Torna domani."

        # No cost
        # user.points -= 50
        user.last_beer_usage = now
        
        # Heal 10% HP
        heal_amount = int(user.max_health * 0.1)
        user.current_hp = min((user.current_hp or 0) + heal_amount, user.max_health)
        
        # Brewery bonus logic
        # Lv 1: 20%
        # Lv 5: 40%
        # Formula: 15 + (brewery_level * 5)
        brew_level = guild['brewery_level'] if guild['brewery_level'] else 1
        potion_bonus_pct = 15 + (brew_level * 5)
        
        session.commit()
        session.close()
        return True, f"🍺 Hai bevuto una Birra Artigianale di {guild['name']}! Ti senti rinvigorito (+{heal_amount} HP).\n\n✨ Le tue pozioni saranno più efficaci del **{potion_bonus_pct}%** per 30 minuti!"

    def get_inn_image(self, inn_level):
        """Get the image path for the inn based on its level"""
        # We found images/locanda.png in the project!
        return "images/locanda.png"

    def get_guilds_list(self):
        """Get all guilds sorted by level and member ratio"""
        session = self.db.get_session()
        guilds = session.query(Guild).all()
        
        guild_list = []
        for g in guilds:
            member_count = session.query(GuildMember).filter_by(guild_id=g.id).count()
            # Calculate a score for sorting: level * 100 + (member_count / member_limit)
            # Higher level first, then higher member ratio
            score = g.village_level * 100 + (member_count / g.member_limit)
            
            guild_list.append({
                'id': g.id,
                'name': g.name,
                'level': g.village_level,
                'members': member_count,
                'limit': g.member_limit,
                'score': score
            })
            
        session.close()
        # Sort by score descending
        guild_list.sort(key=lambda x: x['score'], reverse=True)
        return guild_list

    def get_guild_members(self, guild_id):
        """Get all members of a guild"""
        session = self.db.get_session()
        members = session.query(GuildMember, Utente).join(Utente, GuildMember.user_id == Utente.id_telegram).filter(GuildMember.guild_id == guild_id).all()
        
        member_list = []
        for m, u in members:
            member_list.append({
                'user_id': u.id_telegram,
                'name': u.game_name or u.nome or u.username or "Sconosciuto",
                'role': m.role,
                'level': u.livello
            })
            
        session.close()
        return member_list

    def upgrade_bordello(self, leader_id):
        """Upgrade or build the bordello"""
        session = self.db.get_session()
        member = session.query(GuildMember).filter_by(user_id=leader_id, role="Leader").first()
        if not member:
            session.close()
            return False, "Solo il capogilda può gestire gli upgrade!"
            
        guild = session.query(Guild).filter_by(id=member.guild_id).first()
        cost = (guild.bordello_level + 1) * 1500
        
        if guild.wumpa_bank < cost:
            session.close()
            return False, f"Servono {cost} Wumpa nella banca della gilda per questo upgrade!"
            
        guild.wumpa_bank -= cost
        guild.bordello_level += 1
        new_level = guild.bordello_level
        
        session.commit()
        session.close()
        return True, f"Bordello delle Elfe potenziato al livello {new_level}!"

    def apply_vigore_bonus(self, user_id):
        """Apply the Vigore bonus (50% mana cost) for 30 minutes"""
        session = self.db.get_session()
        user = session.query(Utente).filter_by(id_telegram=user_id).first()
        member = session.query(GuildMember).filter_by(user_id=user_id).first()
        
        if not member:
            session.close()
            return False, "Devi far parte di una gilda per accedere al Bordello delle Elfe!"
            
        guild = session.query(Guild).filter_by(id=member.guild_id).first()
        if guild.bordello_level == 0:
            session.close()
            return False, "La tua gilda non ha ancora un Bordello delle Elfe!"
            
        # Daily limit
        now = datetime.datetime.now()
        if user.last_brothel_usage and user.last_brothel_usage.date() == now.date():
             session.close()
             return False, "🔞 Hai già visitato il Bordello oggi! Torna domani."
            
        # Limit 1 per day
        user.last_brothel_usage = now
        
        # FIXED Duration: 30 minutes
        duration_minutes = 30
        user.vigore_until = datetime.datetime.now() + datetime.timedelta(minutes=duration_minutes)
        
        session.commit()
        session.close()
        return True, f"✨ Hai passato del tempo con le Elfe del Piacere. Ti senti pieno di Vigore! Per {duration_minutes} minuti, il costo in Mana delle tue abilità sarà ridotto del 50%."

    def get_mana_cost_multiplier(self, user_id):
        """Get mana cost multiplier (0.5 if Vigore is active)"""
        session = self.db.get_session()
        user = session.query(Utente).filter_by(id_telegram=user_id).first()
        if not user or not user.vigore_until:
            session.close()
            return 1.0
            
        if user.vigore_until > datetime.datetime.now():
            session.close()
            return 0.5
            
        session.close()
        return 1.0

    def rename_guild(self, leader_id, new_name):
        """Rename the guild (Leader only)"""
        session = self.db.get_session()
        member = session.query(GuildMember).filter_by(user_id=leader_id, role="Leader").first()
        if not member:
            session.close()
            return False, "Solo il capogilda può rinominare la gilda!"
            
        guild = session.query(Guild).filter_by(id=member.guild_id).first()
        
        # Check if name exists
        existing = session.query(Guild).filter(func.lower(Guild.name) == new_name.lower()).first()
        if existing:
            session.close()
            return False, f"Il nome '{new_name}' è già occupato!"
            
        old_name = guild.name
        guild.name = new_name
        session.commit()
        session.close()
        return True, f"Gilda rinominata da '{old_name}' a '{new_name}'!"

    def upgrade_laboratory(self, leader_id):
        """Upgrade the guild laboratory"""
        session = self.db.get_session()
        member = session.query(GuildMember).filter_by(user_id=leader_id, role="Leader").first()
        if not member:
            session.close()
            return False, "Solo il capogilda può gestire gli upgrade!"
            
        guild = session.query(Guild).filter_by(id=member.guild_id).first()
        
        # Default if null
        if guild.laboratory_level is None: guild.laboratory_level = 1
        
        if guild.laboratory_level >= 10:
            session.close()
            return False, "Il Laboratorio è già al livello massimo (Lv. 10)!"
            
        # Cost Logic: 
        # Lv 1->2: 2,500
        # ...
        # Lv 9->10: 100,000
        # Curve: Base * (Multiplier ^ (Level - 1))?
        # Let's use specific values similar to user request
        COSTS = {
            1: 2500,
            2: 5000,
            3: 10000,
            4: 20000,
            5: 35000,
            6: 50000,
            7: 65000,
            8: 80000,
            9: 100000
        }
        cost = COSTS.get(guild.laboratory_level, 100000)
        
        if guild.wumpa_bank < cost:
            session.close()
            return False, f"Servono {cost} Wumpa nella banca della gilda per questo upgrade!"
            
        guild.wumpa_bank -= cost
        guild.laboratory_level += 1
        new_level = guild.laboratory_level
        
        session.commit()
        session.close()
        return True, f"Laboratorio Alchemico potenziato al livello {new_level}!"

    def upgrade_garden(self, leader_id):
        """Upgrade the guild garden"""
        session = self.db.get_session()
        member = session.query(GuildMember).filter_by(user_id=leader_id, role="Leader").first()
        if not member:
            session.close()
            return False, "Solo il capogilda può gestire gli upgrade!"
            
        guild = session.query(Guild).filter_by(id=member.guild_id).first()
        
        # Default if null
        if guild.garden_level is None: guild.garden_level = 1
        
        if guild.garden_level >= 10:
            session.close()
            return False, "Il Giardino è già al livello massimo (Lv. 10)!"
            
        # Same cost structure as Lab
        COSTS = {
            1: 2500,
            2: 5000,
            3: 10000,
            4: 20000,
            5: 35000,
            6: 50000,
            7: 65000,
            8: 80000,
            9: 100000
        }
        cost = COSTS.get(guild.garden_level, 100000)
        
        if guild.wumpa_bank < cost:
            session.close()
            return False, f"Servono {cost} Wumpa nella banca della gilda per questo upgrade!"
            
        guild.wumpa_bank -= cost
        guild.garden_level += 1
        new_level = guild.garden_level
        
        session.commit()
        session.close()
        return True, f"Giardino Botanico potenziato al livello {new_level}!"

    def upgrade_dragon_stables(self, leader_id):
        """Upgrade the dragon stables (Reduced CD)"""
        session = self.db.get_session()
        member = session.query(GuildMember).filter_by(user_id=leader_id, role="Leader").first()
        if not member:
            session.close()
            return False, "Solo il capogilda può gestire gli upgrade!"
        guild = session.query(Guild).filter_by(id=member.guild_id).first()
        
        if guild.dragon_stables_level >= 5:
            session.close()
            return False, "Le Scuderie dei Draghi sono già al livello massimo (Lv. 5)!"
            
        cost = (guild.dragon_stables_level + 1) * 2000
        if guild.wumpa_bank < cost:
            session.close()
            return False, f"Servono {cost} Wumpa in banca per questo upgrade!"
            
        guild.wumpa_bank -= cost
        guild.dragon_stables_level += 1
        new_level = guild.dragon_stables_level
        session.commit()
        session.close()
        return True, f"🐉 Scuderie dei Draghi potenziate al livello {new_level}! Il tempo di ricarica dei tuoi membri è ridotto."

    def upgrade_ancient_temple(self, leader_id):
        """Upgrade the ancient temple (Crit bonus)"""
        session = self.db.get_session()
        member = session.query(GuildMember).filter_by(user_id=leader_id, role="Leader").first()
        if not member:
            session.close()
            return False, "Solo il capogilda può gestire gli upgrade!"
        guild = session.query(Guild).filter_by(id=member.guild_id).first()
        
        if guild.ancient_temple_level >= 5:
            session.close()
            return False, "L'Antico Tempio è già al livello massimo (Lv. 5)!"
            
        cost = (guild.ancient_temple_level + 1) * 2500
        if guild.wumpa_bank < cost:
            session.close()
            return False, f"Servono {cost} Wumpa in banca per questo upgrade!"
            
        guild.wumpa_bank -= cost
        guild.ancient_temple_level += 1
        new_level = guild.ancient_temple_level
        session.commit()
        session.close()
        return True, f"⛩️ Antico Tempio potenziato al livello {new_level}! Il colpo critico dei tuoi membri è aumentato."

    def upgrade_magic_library(self, leader_id):
        """Upgrade the magic library (Mana bonus)"""
        session = self.db.get_session()
        member = session.query(GuildMember).filter_by(user_id=leader_id, role="Leader").first()
        if not member:
            session.close()
            return False, "Solo il capogilda può gestire gli upgrade!"
        guild = session.query(Guild).filter_by(id=member.guild_id).first()
        
        if guild.magic_library_level >= 5:
            session.close()
            return False, "La Biblioteca Magica è già al livello massimo (Lv. 5)!"
            
        cost = (guild.magic_library_level + 1) * 3000
        if guild.wumpa_bank < cost:
            session.close()
            return False, f"Servono {cost} Wumpa in banca per questo upgrade!"
            
        guild.wumpa_bank -= cost
        guild.magic_library_level += 1
        new_level = guild.magic_library_level
        session.commit()
        session.close()
        return True, f"📚 Biblioteca Magica potenziata al livello {new_level}! Il Mana massimo dei tuoi membri è aumentato."

    def set_custom_menu_image(self, leader_id, menu_type, image_url):
        """Set a custom image for a guild menu (Costs 5000 Wumpa)"""
        session = self.db.get_session()
        member = session.query(GuildMember).filter_by(user_id=leader_id, role="Leader").first()
        if not member:
            session.close()
            return False, "Solo il capogilda può personalizzare i menu!"
        
        guild = session.query(Guild).filter_by(id=member.guild_id).first()
        cost = 5000
        if guild.wumpa_bank < cost:
            session.close()
            return False, f"Servono {cost} Wumpa in banca per acquistare una personalizzazione!"
            
        field_map = {
            'inn': 'inn_image',
            'bordello': 'bordello_image',
            'laboratory': 'laboratory_image',
            'garden': 'garden_image'
        }
        
        if menu_type not in field_map:
            session.close()
            return False, "Tipo di menu non valido."
            
        setattr(guild, field_map[menu_type], image_url)
        guild.wumpa_bank -= cost
        session.commit()
        session.close()
        return True, f"✨ Menu '{menu_type}' personalizzato con successo! (Costo: {cost} Wumpa)"

    def get_laboratory_bonus(self, user_id):
        """Get Alchemy bonus based on guild lab level"""
        guild = self.get_user_guild(user_id)
        if not guild:
            return 1.0
            
        # Bonus: Speed up crafting?
        # Lv 1: 1.0
        # Lv 10: 2.0 (Double speed / Half time)
        # Formula: 1.0 + (Level - 1) * 0.11
        lab_level = guild.get('laboratory_level', 1) or 1
        
        # multiplier: e.g. 1.0 to 2.0
        multiplier = 1.0 + ((lab_level - 1) * 0.1)
        return multiplier

    def delete_guild(self, leader_id):
        """Delete the guild (Leader only)"""
        session = self.db.get_session()
        member = session.query(GuildMember).filter_by(user_id=leader_id, role="Leader").first()
        if not member:
            session.close()
            return False, "Solo il capogilda può eliminare la gilda!"
            
        guild = session.query(Guild).filter_by(id=member.guild_id).first()
        guild_name = guild.name
        
        # Delete all members
        session.query(GuildMember).filter_by(guild_id=guild.id).delete()
        
        # Delete guild
        session.delete(guild)
        
        session.commit()
        session.close()
        return True, f"Gilda '{guild_name}' eliminata definitivamente."
        return True, f"Gilda '{guild_name}' eliminata definitivamente."

    def get_guild_inventory(self, guild_id):
        """Get list of items in guild warehouse"""
        session = self.db.get_session()
        items = session.query(GuildItem).filter_by(guild_id=guild_id).all()
        result = [(i.item_name, i.quantity) for i in items]
        session.close()
        return result

    def deposit_item(self, user_id, item_name, quantity=1):
        """Deposit item or resource into guild warehouse"""
        from services.item_service import ItemService
        from sqlalchemy import text
        item_service = ItemService()
        
        session = self.db.get_session()
        try:
            # Check if it's a regular item
            item_count = item_service.get_item_by_user(user_id, item_name)
            
            # Check if it's a resource
            resource_id = session.execute(text("SELECT id FROM resources WHERE name = :name"), {"name": item_name}).scalar()
            resource_qty = 0
            if resource_id:
                resource_qty = session.execute(text("""
                    SELECT quantity FROM user_resources 
                    WHERE user_id = :uid AND resource_id = :rid
                """), {"uid": user_id, "rid": resource_id}).scalar() or 0
                
            if item_count < quantity and resource_qty < quantity:
                return False, "Non hai abbastanza oggetti o risorse!"
                
            # Remove from user
            if item_count >= quantity:
                for _ in range(quantity):
                    item_service.use_item(user_id, item_name, session=session)
            else:
                session.execute(text("""
                    UPDATE user_resources SET quantity = quantity - :qty
                    WHERE user_id = :uid AND resource_id = :rid
                """), {"qty": quantity, "uid": user_id, "rid": resource_id})
                
            # Add to guild
            member = session.query(GuildMember).filter_by(user_id=user_id).first()
            if not member:
                return False, "Non sei in una gilda!"
                
            guild_item = session.query(GuildItem).filter_by(guild_id=member.guild_id, item_name=item_name).first()
            if guild_item:
                guild_item.quantity += quantity
            else:
                guild_item = GuildItem(guild_id=member.guild_id, item_name=item_name, quantity=quantity)
                session.add(guild_item)
                
            session.commit()
            return True, f"Hai depositato {quantity}x {item_name} nel magazzino di gilda."
        except Exception as e:
            session.rollback()
            return False, f"Errore nel deposito: {e}"
        finally:
            session.close()

    def withdraw_item(self, user_id, item_name, quantity=1):
        """Withdraw item or resource from guild warehouse"""
        from sqlalchemy import text
        session = self.db.get_session()
        try:
            member = session.query(GuildMember).filter_by(user_id=user_id).first()
            if not member:
                return False, "Non sei in una gilda!"
                
            guild_item = session.query(GuildItem).filter_by(guild_id=member.guild_id, item_name=item_name).first()
            if not guild_item or guild_item.quantity < quantity:
                return False, "Oggetto non disponibile nel magazzino!"
                
            # Check if it's a resource
            resource_id = session.execute(text("SELECT id FROM resources WHERE name = :name"), {"name": item_name}).scalar()
            
            # Remove from guild
            guild_item.quantity -= quantity
            if guild_item.quantity <= 0:
                session.delete(guild_item)
                
            # Add to user
            if resource_id:
                from services.crafting_service import CraftingService
                crafting_serv = CraftingService()
                # We need to manually add to avoid creating a new session if possible, 
                # but add_resource_drop creates its own.
                crafting_serv.add_resource_drop(user_id, resource_id, quantity, source="guild")
            else:
                from services.item_service import ItemService
                item_service = ItemService()
                for _ in range(quantity):
                    item_service.add_item(user_id, item_name, session=session)
                    
            session.commit()
            return True, f"Hai prelevato {quantity}x {item_name} dal magazzino."
        except Exception as e:
            session.rollback()
            return False, f"Errore nel prelievo: {e}"
        finally:
            session.close()

    def join_guild(self, user_id, guild_id):
        """Join a guild if there is space"""
        session = self.db.get_session()
        
        # Check if user is already in a guild
        existing_member = session.query(GuildMember).filter_by(user_id=user_id).first()
        if existing_member:
            session.close()
            return False, "Fai già parte di una gilda!"
            
        # Get guild
        guild = session.query(Guild).filter_by(id=guild_id).first()
        if not guild:
            session.close()
            return False, "Gilda non trovata."
            
        # Check member limit
        member_count = session.query(GuildMember).filter_by(guild_id=guild_id).count()
        if member_count >= guild.member_limit:
            session.close()
            return False, "La gilda è al completo!"
            
        # Add member
        new_member = GuildMember(
            guild_id=guild_id,
            user_id=user_id,
            role="Member"
        )
        session.add(new_member)
        session.commit()
        
        guild_name = guild.name
        session.close()
        return True, f"Benvenuto nella gilda {guild_name}!"

    def leave_guild(self, user_id):
        """Leave the current guild"""
        session = self.db.get_session()
        member = session.query(GuildMember).filter_by(user_id=user_id).first()
        
        if not member:
            session.close()
            return False, "Non fai parte di nessuna gilda!"
            
        if member.role == "Leader":
            session.close()
            return False, "Il capogilda non può abbandonare la gilda! Devi prima cedere il ruolo o sciogliere la gilda."
            
        guild = session.query(Guild).filter_by(id=member.guild_id).first()
        guild_name = guild.name
        
        session.delete(member)
        session.commit()
        session.close()
        return True, f"Hai lasciato la gilda {guild_name}."

    def is_guild_leader(self, user_id):
        """Check if user is a guild leader"""
        session = self.db.get_session()
        try:
            guild = session.query(Guild).filter_by(leader_id=user_id).first()
            return guild is not None
        finally:
            session.close()
