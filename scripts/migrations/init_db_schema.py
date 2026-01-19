from database import Database, Base
from models.user import Utente
from models.guild import Guild, GuildMember, GuildUpgrade, GuildItem
from models.items import Collezionabili
from models.combat import MobAbility, CombatParticipation
from models.achievements import Achievement, UserAchievement, GameEvent
from models.character_ownership import CharacterOwnership
from models.dungeon import Dungeon, DungeonParticipant
from models.game import GameInfo, Steam, GiocoUtente, NomiGiochi
from models.pve import Mob, Raid, RaidParticipation
from models.seasons import Season, SeasonProgress, SeasonReward, SeasonClaimedReward
from models.stats import UserStat
from models.system import Livello, CharacterAbility, CharacterTransformation, UserTransformation, Domenica, UserCharacter
from models.legacy_tables import Points, Gruppo, GiocoAroma

def init_schema():
    print("Initializing schema...")
    db = Database()
    # Accessing engine triggers creation because of __new__ logic in Database class
    # which calls Base.metadata.create_all(cls._instance.engine)
    print("Schema initialized.")

if __name__ == "__main__":
    init_schema()
