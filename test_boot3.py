from database import Database
from models.user import Utente
from db_setup import init_database
from services.boot_service import BootService

print("Connecting to DB...")
try:
    init_database()
    db = Database()
    session = db.get_session()
    print("DB Session gathered.")
    
    # Pre-test data prep
    u = session.query(Utente).filter_by(id_telegram=1234567890).first()
    if u:
        u.exp = 2000000 # Massive EXP to trigger high level check (level ~70+)
        u.livello_selezionato = 6 # E.g., Vegeta (max level might be 50)
        u.livello = 1
        session.commit()
    
    boot = BootService()
    print("Applying Boot Service startup_and_clean...")
    boot.startup_and_clean()

    users = session.query(Utente).all()
    for user in users:
        print(f"User {user.id_telegram}: Lvl {user.livello} ({user.exp} EXP) - Character: {user.livello_selezionato}")
    session.close()
    print("Test complete.")
except Exception as e:
    print(f"Error: {e}")
