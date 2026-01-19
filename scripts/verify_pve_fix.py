import sys
import os
sys.path.append(os.getcwd())

from services.pve_service import PvEService
from services.user_service import UserService
from models.user import Utente
from database import Database

# Mock setup
db = Database()
session = db.get_session()

# Create or get a test user
user = session.query(Utente).filter_by(id_telegram=123456789).first()
if not user:
    user = Utente(id_telegram=123456789, nome="TestUser", mana=100, max_mana=100, livello_selezionato=1)
    session.add(user)
    session.commit()
else:
    user.mana = 100 # Refill mana
    session.commit()

pve_service = PvEService()

# Ensure there is a mob
pve_service.spawn_specific_mob()

print("Testing use_special_attack...")
try:
    success, msg = pve_service.use_special_attack(user)
    print(f"Success: {success}")
    print(f"Message: {msg}")
except Exception as e:
    print(f"CRASH: {e}")
    import traceback
    traceback.print_exc()

session.close()
