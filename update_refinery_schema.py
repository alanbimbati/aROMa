from database import Database
from models.resources import Resource, UserResource, RefinedMaterial, UserRefinedMaterial, RefineryDaily, RefineryQueue
from models.user import Utente
from models.guild import Guild

def update_schema():
    db = Database()
    print(f"Updating schema for {db.engine.url}...")
    db.create_all_tables()
    print("Done.")

if __name__ == "__main__":
    update_schema()
