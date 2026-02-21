from datetime import datetime, timedelta
import random
from database import Database
from models.guild import Guild, GuildMember, GuildUpgrade, GuildItem
from models.user import Utente
from sqlalchemy import func
from settings import PointsName

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
            'garden_image': guild.garden_image,
            'temple_image': guild.temple_image,
            'library_image': guild.library_image,
            'stables_image': guild.stables_image,
            'brewery_image': guild.brewery_image,
            'armory_image': guild.armory_image,
            'main_image': guild.main_image
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
        return True, f"Locanda potenziata al livello {new_level}! Recupero: +{int((new_level-1)*50)}% -> +{int(new_level*50)}%"

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
        """Build or Upgrade the brothel (Alias for consistency)"""
        return self.upgrade_bordello(leader_id)

    def get_potion_bonus(self, user_id):
        """Get potion effectiveness bonus based on inn level (Active for 30 mins after beer)"""
        session = self.db.get_session()
        user = session.query(Utente).filter_by(id_telegram=user_id).first()
        if not user or not user.last_beer_usage:
            session.close()
            return 1.0
            
        # Check if 30 minutes have passed
        now = datetime.now()
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

    def buy_guild_drink(self, user_id, drink_type='beer'):
        """Buy a drink from the guild brewery"""
        session = self.db.get_session()
        user = session.query(Utente).filter_by(id_telegram=user_id).first()
        member = session.query(GuildMember).filter_by(user_id=user_id).first()
        
        if not member:
            session.close()
            return False, "Non fai parte di nessuna gilda!"
            
        guild = session.query(Guild).filter_by(id=member.guild_id).first()
        
        # Daily limit check (reset at midnight)
        now = datetime.now()
        if user.last_beer_usage and user.last_beer_usage.date() == now.date():
             session.close()
             return False, "🍺 Hai già bevuto la tua dose giornaliera! Torna domani."

        # Costs and Level Requirements
        DRINK_CONFIG = {
            'beer': {'cost': 0, 'lvl': 1, 'heal': 0.1, 'name': "Birra Chiara"},
            'whiskey': {'cost': 50, 'lvl': 3, 'heal': 0.2, 'name': "Whiskey Nanico"},
            'ambrosia': {'cost': 500, 'lvl': 5, 'heal': 0.4, 'name': "Ambrosia di Wumpa"},
            'mead': {'cost': 1000, 'lvl': 7, 'heal': 0.6, 'name': "Idromele dei Titani"},
            'dragon_blood': {'cost': 5000, 'lvl': 9, 'heal': 0.8, 'name': "Sangue di Drago"},
            'yggdrasil': {'cost': 10000, 'lvl': 10, 'heal': 1.0, 'name': "Lacrima di Yggdrasil"}
        }
        
        drink = DRINK_CONFIG.get(drink_type)
        if not drink:
            session.close()
            return False, "Bevanda non valida."
            
        if (guild.brewery_level or 0) < drink['lvl']:
            session.close()
            return False, f"Il Birrificio deve essere al livello {drink['lvl']} per servire questa bevanda!"
        
        if user.points < drink['cost']:
            session.close()
            return False, f"Non hai abbastanza Wumpa! Serve {drink['cost']} Wumpa."

        user.points -= drink['cost']
        user.last_beer_usage = now
        
        # Heal Logic
        heal_amount = int(user.max_health * drink['heal'])
        user.current_hp = min((user.current_hp or 0) + heal_amount, user.max_health)
        
        # Potion Bonus Logic
        brew_level = guild.brewery_level if guild.brewery_level else 1
        base_bonus = 15 + (brew_level * 5)
        
        # Multiplier based on drink
        drink_mults = {
            'beer': 1.0, 'whiskey': 1.1, 'ambrosia': 1.25, 
            'mead': 1.5, 'dragon_blood': 2.0, 'yggdrasil': 3.0
        }
        drink_mult = drink_mults.get(drink_type, 1.0)
        final_bonus = int(base_bonus * drink_mult)
        
        session.commit()
        session.close()
        
        return True, f"🍺 Hai bevuto **{drink['name']}**! Ti senti rinvigorito (+{heal_amount} HP).\n\n✨ Le tue pozioni saranno più efficaci del **{final_bonus}%** per 30 minuti!"

    def get_inn_image(self, inn_level):
        """Get the image path for the inn based on its level"""
        return "assets/guild/inn.png"

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

    def apply_vigore_bonus(self, user_id, tier='fairy'):
        """Apply the Vigore bonus (Man cost reduction) for varying duration"""
        session = self.db.get_session()
        
        try:
            member = session.query(GuildMember).filter_by(user_id=user_id).first()
            if not member:
                return False, "Devi far parte di una gilda!"
                
            guild = session.query(Guild).filter_by(id=member.guild_id).first()
            if guild.bordello_level < 1:
                return False, "Il Bordello non è ancora stato costruito!"
                
            # Tier Configuration (Consolidated)
            TIERS = {
                'fairy':    {'lvl': 1, 'cost': 100,  'dur': 30,  'dmg': 5,  'crit': 2,  'mana': 20,  'flavor': "🧚 La Fatina delle Luci ha danzato intorno a te... ti senti protetto!"},
                'elf':      {'lvl': 3, 'cost': 500,  'dur': 60,  'dmg': 10, 'crit': 5,  'mana': 50,  'flavor': "🧝‍♀️ L'Elfa dei Boschi ti ha stretto in un abbraccio fatato."},
                'nymph':    {'lvl': 5, 'cost': 1500, 'dur': 120, 'dmg': 25, 'crit': 10, 'mana': 100, 'flavor': "💧 La Ninfa delle Acque ti ha sussurrato segreti di giovinezza."},
                'succubus': {'lvl': 7, 'cost': 5000, 'dur': 240, 'dmg': 60, 'crit': 20, 'mana': 250, 'flavor': "😈 La Succube Reale ti ha prosciugato... ma ora il tuo potere è immenso!"}
            }
            
            config = TIERS.get(tier)
            if not config:
                return False, "Tipo di compagnia non valido!"

            if guild.bordello_level < config['lvl']:
                return False, f"Questa compagnia richiede un Bordello di Livello {config['lvl']}!"

            user = session.query(Utente).filter_by(id_telegram=user_id).first()
            now = datetime.now()
            
            # Use 'last_brothel_free_usage' if we want to separate it?
            # User said "first time free", let's check if they used it today.
            # If last_brothel_usage is NOT today, it's FREE.
            is_free = False
            if not user.last_brothel_usage or user.last_brothel_usage.date() < now.date():
                is_free = True
            
            cost = 0 if is_free else config['cost']
                 
            current_points = user.points or 0
            if current_points < cost:
                return False, f"Non hai abbastanza {PointsName}! Servono {cost} {PointsName}."
    
            user.points = current_points - cost
            user.last_brothel_usage = now
            user.vigore_until = datetime.now() + timedelta(minutes=config['dur'])
            
            # Apply Persistent Status Effects (Dmg, Crit, etc.)
            import json
            effects = json.loads(user.active_status_effects or '[]')
            
            # Remove old bordello effects
            effects = [e for e in effects if not e.get('effect', '').startswith('bordello_')]
            
            expires_at = (datetime.now() + timedelta(minutes=config['dur'])).timestamp()
            
            if config.get('dmg'):
                effects.append({'effect': 'bordello_dmg', 'value': config['dmg'], 'expires_at': expires_at})
            if config.get('crit'):
                effects.append({'effect': 'bordello_crit', 'value': config['crit'], 'expires_at': expires_at})
            if config.get('mana'):
                effects.append({'effect': 'bordello_mana', 'value': config['mana'], 'expires_at': expires_at})
                
            user.active_status_effects = json.dumps(effects)
            
            session.commit()
            free_msg = "🎁 **PRIMA VISITA GRATUITA!**\n" if is_free else ""
            stats_msg = f"\n✨ +{config['dmg']} Danno, +{config['crit']}% Critico, +{config['mana']} Mana"
            return True, f"{free_msg}{config['flavor']}\n\n💪 **Vigore Attivo**: Costo Mana dimezzato per {config['dur']} minuti!{stats_msg}"
        except Exception as e:
            session.rollback()
            return False, f"Errore: {e}"
        finally:
            session.close()

    def buy_drink(self, user_id, drink_key):
        """Buy a drink at the brewery"""
        # drink_key: 'beer', 'whiskey', 'ambrosia', 'mead', 'dragon_blood', 'yggdrasil'
        session = self.db.get_session()
        try:
            member = session.query(GuildMember).filter_by(user_id=user_id).first()
            if not member:
                return False, "Non fai parte di nessuna gilda!"
            
            guild = session.query(Guild).filter_by(id=member.guild_id).first()
            if guild.brewery_level < 1:
                return False, "Il Birrificio non è ancora stato costruito o è di livello troppo basso!"
                
            # Configuration
            DRINKS = {
                'beer': {'name': 'Birra Chiara', 'lvl': 1, 'cost': 10, 'hp': 20, 'mana': 10, 'flavor': "Una birra fresca e leggera."},
                'whiskey': {'name': 'Whiskey Nanico', 'lvl': 3, 'cost': 50, 'hp': 50, 'mana': 30, 'flavor': "Brucia la gola, ma scalda il cuore."},
                'mead': {'name': 'Idromele dei Titani', 'lvl': 5, 'cost': 150, 'hp': 150, 'mana': 100, 'flavor': "Il nettare degli antichi guerrieri."},
                'ambrosia': {'name': 'Ambrosia di Wumpa', 'lvl': 7, 'cost': 500, 'hp': 500, 'mana': 300, 'flavor': "Un gusto divino che ripristina le forze."},
                'dragon_blood': {'name': 'Sangue di Drago', 'lvl': 9, 'cost': 1000, 'hp': 1000, 'mana': 500, 'flavor': "PICCANTE! Ti senti invincibile."},
                'yggdrasil': {'name': 'Lacrima di Yggdrasil', 'lvl': 10, 'cost': 2500, 'hp': 9999, 'mana': 9999, 'flavor': "Una goccia di pura energia vitale."}
            }
            
            drink = DRINKS.get(drink_key)
            if not drink:
                return False, "Bevanda non trovata!"
                
            if guild.brewery_level < drink['lvl']:
                return False, f"Il Birrificio deve essere al livello {drink['lvl']} per servire questa bevanda!"
                
            user = session.query(Utente).filter_by(id_telegram=user_id).first()
            if user.points < drink['cost']:
                return False, f"Non hai abbastanza Wumpa! Costa {drink['cost']}."
                
            user.points -= drink['cost']
            
            # Helper to execute restore logic reuse?
            # Just do it manually here
            old_hp = user.current_hp if user.current_hp is not None else user.max_health
            old_mana = user.current_mana if user.current_mana is not None else user.max_mana
            
            user.current_hp = min(user.max_health, old_hp + drink['hp'])
            user.current_mana = min(user.max_mana, old_mana + drink['mana'])
            
            restored_hp = user.current_hp - old_hp
            restored_mana = user.current_mana - old_mana
            
            session.commit()
            return True, f"🍺 Hai bevuto **{drink['name']}**!\n\n_{drink['flavor']}_\n\n❤️ +{restored_hp} HP\n💙 +{restored_mana} Mana"
        except Exception as e:
            session.rollback()
            return False, f"Errore: {e}"
        finally:
             session.close()

    def get_mana_cost_multiplier(self, user_id):
        """Get mana cost multiplier (0.5 if Vigore is active)"""
        session = self.db.get_session()
        user = session.query(Utente).filter_by(id_telegram=user_id).first()
        if not user or not user.vigore_until:
            session.close()
            return 1.0
            
        if user.vigore_until > datetime.now():
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
            'garden': 'garden_image',
            'temple': 'temple_image',
            'library': 'library_image',
            'stables': 'stables_image',
            'brewery': 'brewery_image',
            'armory': 'armory_image',
            'village': 'main_image',
            'main': 'main_image'
        }
        
        if menu_type not in field_map:
            session.close()
            return False, f"Tipo di menu '{menu_type}' non valido."
            
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

    # ---------------- EGG SYSTEM ----------------
    def get_active_egg(self, guild_id):
        """Get the current active egg for the guild"""
        session = self.db.get_session()
        from models.guild import GuildEgg
        egg = session.query(GuildEgg).filter_by(guild_id=guild_id, hatched=0).first()
        result = None
        if egg:
            result = {
                'id': egg.id,
                'guild_id': egg.guild_id,
                'egg_type': egg.egg_type,
                'progress': egg.progress,
                'required_progress': egg.required_progress,
                'created_at': egg.created_at
            }
        session.close()
        return result

    def buy_egg(self, user_id, egg_type):
        """Buy a new egg for the guild"""
        COSTS = {
            'common': 5000,
            'rare': 15000,
            'epic': 50000
        }
        cost = COSTS.get(egg_type)
        if not cost: return False, "Tipo di uovo non valido!"

        session = self.db.get_session()
        member = session.query(GuildMember).filter_by(user_id=user_id, role="Leader").first()
        if not member:
            session.close()
            return False, "Solo il capogilda può acquistare le uova!"

        guild = session.query(Guild).filter_by(id=member.guild_id).first()
        from models.guild import GuildEgg
        active_egg = session.query(GuildEgg).filter_by(guild_id=guild.id, hatched=0).first()
        if active_egg:
            session.close()
            return False, "Avete già un uovo da accudire!"

        if guild.wumpa_bank < cost:
            session.close()
            return False, f"Servono {cost} Wumpa in banca per questo uovo!"

        guild.wumpa_bank -= cost
        
        # Required progress based on type
        # Common: 50, Rare: 200, Epic: 500
        REQS = {'common': 50, 'rare': 200, 'epic': 500}
        
        new_egg = GuildEgg(
            guild_id=guild.id,
            egg_type=egg_type,
            required_progress=REQS.get(egg_type, 100)
        )
        session.add(new_egg)
        session.commit()
        session.close()
        return True, f"🥚 Hai acquistato un **Uovo {egg_type.capitalize()}**! Ora tutti i membri devono accudirlo per farlo schiudere!"

    def nurture_egg(self, user_id):
        """Nurture the active egg"""
        session = self.db.get_session()
        member = session.query(GuildMember).filter_by(user_id=user_id).first()
        if not member:
            session.close()
            return False, "Non fai parte di nessuna gilda!"
        
        from models.guild import GuildEgg
        egg = session.query(GuildEgg).filter_by(guild_id=member.guild_id, hatched=0).first()
        if not egg:
            session.close()
            return False, "Non c'è nessun uovo da accudire al momento!"
            
        user = session.query(Utente).filter_by(id_telegram=user_id).first()
        now = datetime.now()
        
        if user.last_egg_nurture and (now - user.last_egg_nurture).total_seconds() < 3600:
             session.close()
             mins = int((3600 - (now - user.last_egg_nurture).total_seconds()) / 60)
             if mins == 0: mins = 1
             return False, f"Hai già accudito l'uovo di recente! Riprova tra {mins} minuti."

        user.last_egg_nurture = now
        egg.progress += 1
        
        hatched = False
        msg = "Hai accarezzato l'uovo! Sembra felice. 💓"
        
        if egg.progress >= egg.required_progress:
            egg.hatched = 1
            hatched = True
            # Award logic
            reward_msg = self._hatch_egg_logic(egg)
            msg = f"🎉 **L'UOVO SI È SCHIUSO!** 🎉\n\n{reward_msg}"
            
        session.commit()
        session.close()
        return True, msg

    def _hatch_egg_logic(self, egg):
        # Determine reward
        return f"È nato un magnifico **Drago {egg.egg_type.capitalize()}**! (Presto disponibile nelle Scuderie)"

    def pray_at_temple(self, user_id):
        """Pray at the temple for a temporary Crit Buff"""
        session = self.db.get_session()
        try:
            member = session.query(GuildMember).filter_by(user_id=user_id).first()
            if not member:
                return False, "Non fai parte di nessuna gilda!"
                
            guild = session.query(Guild).filter_by(id=member.guild_id).first()
            if guild.ancient_temple_level < 1:
                return False, "Il tempio non è ancora stato costruito!"
                
            user = session.query(Utente).filter_by(id_telegram=user_id).first()
            now = datetime.now()
            
            # Cooldown: 1 hour
            # We use a custom field stored in json? No, let's use a simpler way.
            # We can check active_status_effects for the buff. If present, deny?
            # Or use last_prayer field if we add it?
            # User doesn't have last_prayer.
            # Use JSON to track cooldown? "last_temple_usage": timestamp
            
            import json
            effects = json.loads(user.active_status_effects or '[]')
            
            # Check for existing buff
            existing = next((e for e in effects if e.get('effect') == 'temple_buff_crit'), None)
            if existing:
                # Check if expired
                if existing.get('expires_at', 0) > now.timestamp():
                    remaining = int((existing['expires_at'] - now.timestamp()) / 60)
                    return False, f"Sei già benedetto dal Tempio! La benedizione dura ancora {remaining} minuti."
            
            # Apply Buff
            duration = 30 # minutes
            expires_at = (now + timedelta(minutes=duration)).timestamp()
            
            # Remove old
            effects = [e for e in effects if e.get('effect') != 'temple_buff_crit']
            
            effects.append({
                'effect': 'temple_buff_crit',
                'expires_at': expires_at,
                'value': 15, # 15% Crit
                'source': 'temple'
            })
            
            user.active_status_effects = json.dumps(effects)
            session.commit()
            
            return True, f"🙏 Hai pregato al Tempio.\n\n✨ **Benedizione Ricevuta**: +15% Critico per {duration} minuti!"
        except Exception as e:
            session.rollback()
            return False, f"Errore: {e}"
        finally:
            session.close()

    def study_at_library(self, user_id):
        """Study at the library for Mana Restore + Max Mana Buff"""
        session = self.db.get_session()
        try:
            member = session.query(GuildMember).filter_by(user_id=user_id).first()
            if not member:
                return False, "Non fai parte di nessuna gilda!"
                
            guild = session.query(Guild).filter_by(id=member.guild_id).first()
            if guild.magic_library_level < 1:
                return False, "La biblioteca non è ancora stata costruita!"
                
            user = session.query(Utente).filter_by(id_telegram=user_id).first()
            now = datetime.now()
            
            import json
            effects = json.loads(user.active_status_effects or '[]')
            
            # Check for existing buff
            existing = next((e for e in effects if e.get('effect') == 'library_buff_mana'), None)
            if existing and existing.get('expires_at', 0) > now.timestamp():
                remaining = int((existing['expires_at'] - now.timestamp()) / 60)
                return False, f"Hai già studiato di recente! Il buff dura ancora {remaining} minuti."
            
            # Restore Mana
            # Amount based on Library Level?
            # Lv 1: 50, Lv 5: 250?
            restore = guild.magic_library_level * 50
            user.current_mana = min(user.max_mana, user.current_mana + restore)
            
            # Apply Buff
            duration = 60 # minutes
            expires_at = (now + timedelta(minutes=duration)).timestamp()
            
            # Remove old
            effects = [e for e in effects if e.get('effect') != 'library_buff_mana']
            
            buff_amount = guild.magic_library_level * 20 # +20 Max Mana per level
            
            effects.append({
                'effect': 'library_buff_mana',
                'expires_at': expires_at,
                'value': buff_amount,
                'source': 'library'
            })
            
            user.active_status_effects = json.dumps(effects)
            session.commit()
            
            return True, f"📖 Hai studiato antichi tomi.\n\n💧 **Mana Recuperato**: {restore}\n✨ **Buff Conoscenza**: +{buff_amount} Mana Max per {duration} minuti!"
        except Exception as e:
            session.rollback()
            return False, f"Errore: {e}"
        finally:
            session.close()

    def use_relax_corner(self, user_id, gadget_type):
        """Use the Relax Corner (Smoking gadgets)"""
        session = self.db.get_session()
        try:
            member = session.query(GuildMember).filter_by(user_id=user_id).first()
            if not member:
                return False, "Non fai parte di nessuna gilda!"
                
            guild = session.query(Guild).filter_by(id=member.guild_id).first()
            garden_lvl = getattr(guild, 'garden_level', 1) or 1
            
            # Gadget Config
            GADGETS = {
                'papers': {'lvl': 1, 'name': 'Cartine', 'res': 5, 'speed': -5, 'cost_erba': 1},
                'chilum': {'lvl': 3, 'name': 'Chilum', 'res': 10, 'speed': -10, 'cost_erba': 2},
                'bong': {'lvl': 5, 'name': 'Bong', 'res': 15, 'speed': -15, 'cost_erba': 3},
                'hookah': {'lvl': 7, 'name': 'Narghilè', 'res': 20, 'speed': -20, 'cost_erba': 5}
            }
            
            gadget = GADGETS.get(gadget_type)
            if not gadget:
                return False, "Gadget non valido!"
                
            if garden_lvl < gadget['lvl']:
                 return False, f"Serve il Giardino al livello {gadget['lvl']}!"
            
            user = session.query(Utente).filter_by(id_telegram=user_id).first()
            
            # Check Daily Limit (Reset at midnight)
            import json
            effects = json.loads(user.active_status_effects or '[]')
            
            limit_id = f"relax_limit_{gadget_type}"
            for effect in effects:
                if effect.get('id') == limit_id:
                    # Check expiry
                    expires = datetime.fromisoformat(effect.get('expires'))
                    if datetime.now() < expires:
                        return False, f"Hai già usato {gadget['name']} oggi! Torna domani."
            
            # Check Usage Cost (Erba Verde - now as Resource)
            from services.crafting_service import CraftingService
            crafting_service = CraftingService()
            erba_count = crafting_service.get_resource_quantity(user_id, "Erba Verde")
            
            if erba_count < gadget['cost_erba']:
                return False, f"Non hai abbastanza Erba Verde! Te ne servono {gadget['cost_erba']}."
            
            # Consume Resources
            if not crafting_service.remove_resource(user_id, "Erba Verde", gadget['cost_erba'], session=session):
                 return False, "Errore nel consumo dell'erba."
            
            # Apply Buffs
            # Duration: Until end of day? Or fixed time? 
            # Prompt implies "Daily Limit" for usage, but effect duration usually temporary. 
            # Let's say 2 hours for now, as usually buffs are temporary.
            # "Ogni cosa si può usare 1 volta al giorno" -> Limit usage frequency.
            # Effect duration: Let's stick to 60-120 mins like others.
            duration_minutes = 30
            
            now = datetime.now()
            expires_at = (now + timedelta(minutes=duration_minutes)).timestamp()
            limit_expires = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
            
            # Remove old buffs of same type to prevent stacking of SAME gadget? 
            # Or allow multiple DIFFERENT gadgets? "1 use per gadget type".
            # Assume different gadgets stack.
            
            # Add Limit Tracker
            effects.append({
                'id': limit_id,
                'expires': limit_expires,
                'type': 'limit'
            })
            
            # Add Stat Buff
            effects.append({
                'effect': f"relax_{gadget_type}",
                'expires_at': expires_at,
                'value_res': gadget['res'],
                'value_speed': gadget['speed'],
                'source': 'relax_corner',
                'name': gadget['name']
            })
            
            user.active_status_effects = json.dumps(effects)
            session.commit()
            
            return True, f"🌿 Hai usato: **{gadget['name']}**.\n\n💨 Ti senti molto rilassato...\n🛡️ Resistenza +{gadget['res']}%\n🐌 Velocità {gadget['speed']}"
            
        except Exception as e:
            print(f"Error use_relax_corner: {e}")
            import traceback
            traceback.print_exc()
            return False, f"Errore: {e}"
        finally:
            session.close()

        
