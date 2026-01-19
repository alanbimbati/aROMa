from sqlalchemy import create_engine
from database import Base
# Import all models to ensure they are registered with Base
from models.user import Utente
from models.guild import Guild, GuildMember, GuildUpgrade
from models.system import Livello

DB_PATH = 'sqlite:///points_dietpi.db'

def init_db():
    print(f"Initializing tables in {DB_PATH}...")
    engine = create_engine(DB_PATH)
    Base.metadata.create_all(engine)
    print("Tables initialized.")

if __name__ == "__main__":
    init_db()
