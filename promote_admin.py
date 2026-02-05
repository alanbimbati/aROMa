from database import Database
from models.user import Admin

db = Database()
session = db.get_session()

# Target user IDs
admin_ids = [62716473, 5816821562, 6256663953]

for admin_id in admin_ids:
    # Check if already exists
    exist = session.query(Admin).filter_by(id_telegram=admin_id).first()
    if not exist:
        new_admin = Admin(id_telegram=admin_id)
        session.add(new_admin)
        print(f"User {admin_id} promoted to Admin.")
    else:
        print(f"User {admin_id} is already Admin.")

session.commit()

session.close()
