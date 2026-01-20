from services.stats_service import StatsService
from services.user_service import UserService
from database import Database
from models.user import Utente
import sys

user_id = 62716473 # Alan

print("Testing allocation logic...")
stats_service = StatsService()
user_service = UserService()
db = Database()

# Get user
user = user_service.get_user(user_id)
print(f"Initial: Speed={user.speed}, Allocated={user.allocated_speed}")

# Allocate Speed
print("Allocating Speed...")
success, msg = stats_service.allocate_stat_point(user, 'speed')
print(f"Result: {success}, {msg}")

# Verify
session = db.get_session()
user = session.query(Utente).filter_by(id_telegram=user_id).first()
print(f"After: Speed={user.speed}, Allocated={user.allocated_speed}")
session.close()
