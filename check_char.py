from database import Database
from models.system import Livello

db = Database()
session = db.get_session()
char = session.query(Livello).first()
print(f"Name: {char.nome}")
print(f"Group: {char.character_group}")
print(f"Saga: {getattr(char, 'saga', 'Not Present')}")
session.close()
