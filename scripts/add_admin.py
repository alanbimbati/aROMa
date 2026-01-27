from database import Database
from models.user import Admin, Utente
from services.user_service import UserService

db = Database()
session = db.get_session()

user_id = 62716473

# Check if user exists in Utente
user = session.query(Utente).filter_by(id_telegram=user_id).first()
if not user:
    print(f"User {user_id} not found in Utente table.")
else:
    print(f"User {user_id} found: {user.username}")

# Check if user is in Admin
admin = session.query(Admin).filter_by(id_telegram=user_id).first()
if admin:
    print(f"User {user_id} is ALREADY in Admin table.")
else:
    print(f"User {user_id} is NOT in Admin table. Adding...")
    new_admin = Admin(id_telegram=user_id)
    session.add(new_admin)
    session.commit()
    print(f"User {user_id} added to Admin table.")

# Verify
admin_check = session.query(Admin).filter_by(id_telegram=user_id).first()
print(f"Verification: Is Admin? {admin_check is not None}")

session.close()
