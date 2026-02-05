from database import Database
from models.user import Utente
from sqlalchemy import or_

db = Database()
session = db.get_session()
users = session.query(Utente).filter(
    or_(
        Utente.nome.ilike('%alan%'),
        Utente.username.ilike('%alan%')
    )
).all()

print("--- Users found ---")
for u in users:
    print(f"ID: {u.id_telegram} | Nome: {u.nome} | Username: {u.username}")
session.close()
