from database import Database, Base
from sqlalchemy import inspect
import os

if __name__ == "__main__":
    if not os.path.exists('aroma.db'):
        print("aroma.db not found!")
    else:
        db = Database()
        inspector = inspect(db.engine)
        tables = inspector.get_table_names()
        print(f"Tables: {tables}")
        
        if 'mob' in tables:
            columns = [c['name'] for c in inspector.get_columns('mob')]
            print(f"Mob columns: {columns}")
