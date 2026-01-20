from services.user_service import UserService
from database import Database
from models.user import Utente
import sys

user_id = 62716473

print("Testing manual speed update...")
us = UserService()
db = Database()
session = db.get_session()

user = session.query(Utente).filter_by(id_telegram=user_id).first()
print(f"Before: Speed={user.speed}, Allocated={user.allocated_speed}")

# Try updating via UserService
print("Updating speed to 10 via update_user...")
us.update_user(user_id, {'speed': 10, 'allocated_speed': 5})

# Verify
session.expire_all()
user = session.query(Utente).filter_by(id_telegram=user_id).first()
print(f"After: Speed={user.speed}, Allocated={user.allocated_speed}")

session.close()
