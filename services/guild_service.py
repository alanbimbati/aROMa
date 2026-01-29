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
            'map_x': guild.map_x,
            'map_y': guild.map_y,
            'role': member.role
        }
        session.close()
        return guild_data

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

    def get_potion_bonus(self, user_id):
        """Get potion effectiveness bonus based on inn level"""
        guild = self.get_user_guild(user_id)
        if not guild:
            return 1.0
        # 10% bonus per inn level above 1
        return 1.0 + (guild['inn_level'] - 1) * 0.1

    def buy_craft_beer(self, user_id):
        """Buy a craft beer for a fun bonus (and healing)"""
        session = self.db.get_session()
        user = session.query(Utente).filter_by(id_telegram=user_id).first()
        guild = self.get_user_guild(user_id)
        
        if not guild:
            session.close()
            return False, "Non fai parte di nessuna gilda!"
            
        if user.points < 50:
            session.close()
            return False, "Una birra artigianale costa 50 Wumpa!"
            
        user.points -= 50
        # Heal 10% HP
        heal_amount = int(user.max_health * 0.1)
        user.current_hp = min(user.current_hp + heal_amount, user.max_health)
        
        session.commit()
        session.close()
        return True, f"🍺 Hai bevuto una Birra Artigianale di {guild['name']}! Ti senti rinvigorito (+{heal_amount} HP). Le tue pozioni saranno più efficaci del {int((guild['inn_level']-1)*10)}%!"

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
        """Apply the Vigore bonus (50% mana cost) for 10 minutes"""
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
            
        cost = 200 # Fixed cost for now
        if user.points < cost:
            session.close()
            return False, f"Ti servono {cost} Wumpa per passare del tempo con le elfe!"
            
        user.points -= cost
        user.vigore_until = datetime.datetime.now() + datetime.timedelta(minutes=10)
        
        session.commit()
        session.close()
        return True, "✨ Hai passato del tempo con le Elfe del Piacere. Ti senti pieno di Vigore! Per i prossimi 10 minuti, il costo in Mana delle tue abilità sarà ridotto del 50%."

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
        """Deposit item into guild warehouse"""
        # Check if user has item
        from services.item_service import ItemService
        item_service = ItemService()
        
        count = item_service.get_item_by_user(user_id, item_name)
        if count < quantity:
            return False, "Non hai abbastanza oggetti!"
            
        # Remove from user (use_item marks it as used)
        for _ in range(quantity):
            item_service.use_item(user_id, item_name)
            
        # Add to guild
        session = self.db.get_session()
        member = session.query(GuildMember).filter_by(user_id=user_id).first()
        if not member:
            session.close()
            return False, "Non sei in una gilda!"
            
        guild_item = session.query(GuildItem).filter_by(guild_id=member.guild_id, item_name=item_name).first()
        if guild_item:
            guild_item.quantity += quantity
        else:
            guild_item = GuildItem(guild_id=member.guild_id, item_name=item_name, quantity=quantity)
            session.add(guild_item)
            
        session.commit()
        session.close()
        return True, f"Hai depositato {quantity}x {item_name} nel magazzino di gilda."

    def withdraw_item(self, user_id, item_name, quantity=1):
        """Withdraw item from guild warehouse"""
        session = self.db.get_session()
        member = session.query(GuildMember).filter_by(user_id=user_id).first()
        if not member:
            session.close()
            return False, "Non sei in una gilda!"
            
        guild_item = session.query(GuildItem).filter_by(guild_id=member.guild_id, item_name=item_name).first()
        if not guild_item or guild_item.quantity < quantity:
            session.close()
            return False, "Oggetto non disponibile nel magazzino!"
            
        # Remove from guild
        guild_item.quantity -= quantity
        if guild_item.quantity <= 0:
            session.delete(guild_item)
            
        session.commit()
        session.close()
        
        # Add to user
        from services.item_service import ItemService
        item_service = ItemService()
        for _ in range(quantity):
            item_service.add_item(user_id, item_name)
            
        return True, f"Hai prelevato {quantity}x {item_name} dal magazzino."

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
