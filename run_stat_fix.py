from services.user_service import UserService
from database import Database

db = Database()
# Force a recalculation for all users by iterating and calling recalculate_stats directly
# or using the existing validate method if it triggers recalculate.
# validate_and_fix_user_stats only fixes points, but recalculate_stats updates max values.
# We need to force recalculate_stats for everyone.

print("Starting global stat recalculation...")
us = UserService()
session = db.get_session()
users = us.get_users()

count = 0
for user in users:
    try:
        # print(f"Recalculating for {user.username} ({user.id_telegram})...")
        us.recalculate_stats(user.id_telegram)
        count += 1
    except Exception as e:
        print(f"Error recalculating for {user.id_telegram}: {e}")

print(f"Recalculation complete for {count} users.")
