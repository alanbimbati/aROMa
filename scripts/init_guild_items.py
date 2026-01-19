from database import Database, Base
from models.guild import GuildItem
from models.user import Utente
from sqlalchemy import create_engine

db = Database()
engine = db.engine

# Create table
GuildItem.__table__.create(bind=engine, checkfirst=True)
print("Table guild_items created successfully!")
