from database import Database
from sqlalchemy import inspect

db = Database()
inspector = inspect(db.engine)
columns = [col['name'] for col in inspector.get_columns('utente')]
print(f"Columns in utente: {columns}")
if 'admin' in columns:
    print("FOUND: admin column exists")
else:
    print("NOT FOUND: admin column does not exist")
