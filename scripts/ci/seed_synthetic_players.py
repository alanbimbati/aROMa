import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database import Database
from models.user import Utente

db = Database()
session = db.get_session()
try:
    for i in range(10):
        # We need to make sure we don't violate unique constraints, although it's an empty DB normally
        user = session.query(Utente).filter_by(id_telegram=1000+i).first()
        if not user:
            session.add(Utente(id_telegram=1000+i, nome=f"FakeUser{i}", exp=100))
    session.commit()
finally:
    session.close()
