from services.user_service import UserService
from database import Database
import sys

user_id = 62716473 # Alan's ID based on logs

db = Database()
session = db.get_session()
from models.user import Utente

user = session.query(Utente).filter_by(id_telegram=user_id).first()

if user:
    print(f"User: {user.nome} ({user.username})")
    print(f"Speed: {user.speed}")
    print(f"Allocated Speed: {user.allocated_speed}")
    print(f"Stat Points: {user.stat_points}")
    print(f"Titles: {user.titles}")
    print(f"Current Title: {user.title}")
else:
    print("User not found")

session.close()
