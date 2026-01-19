from database import Database
from models.user import Utente
from sqlalchemy import text

try:
    db = Database()
    session = db.get_session()
    print("Session created.")
    
    # Try simple query
    count = session.query(Utente).count()
    print(f"User count: {count}")
    
    # Try raw SQL
    result = session.execute(text("SELECT count(*) FROM utente")).scalar()
    print(f"Raw SQL count: {result}")
    
    session.close()
    print("Success!")
except Exception as e:
    print(f"Error: {e}")
