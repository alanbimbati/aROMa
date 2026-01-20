from database import Database
from models.achievements import Achievement
import sys

def fix_category():
    print("Updating 'Dormiglione' category to 'classici'...")
    db = Database()
    session = db.get_session()
    
    try:
        ach = session.query(Achievement).filter_by(achievement_key='dormiglione').first()
        if ach:
            print(f"Found achievement. Current category: {ach.category}")
            ach.category = 'classici'
            session.commit()
            print("Category updated to 'classici'.")
        else:
            print("Achievement not found.")
    except Exception as e:
        print(f"Error: {e}")
        session.rollback()
    finally:
        session.close()

if __name__ == "__main__":
    fix_category()
