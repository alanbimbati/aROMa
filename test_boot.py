from database import Database
from models.user import Utente
from services.boot_service import BootService

db = Database()
session = db.get_session()
boot = BootService()

print("Applying Boot Service startup_and_clean...")
boot.startup_and_clean()

users = session.query(Utente).all()
for u in users:
    print(f"User {u.id_telegram}: Lvl {u.livello} ({u.exp} EXP) - Character: {u.livello_selezionato}")
session.close()
