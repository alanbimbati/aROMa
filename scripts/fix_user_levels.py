import sys
import os
import time

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from services.user_service import UserService

def fix_levels():
    print("Starting level fix...")
    service = UserService()
    users = service.get_users()
    
    count = 0
    fixed = 0
    
    for user in users:
        print(f"Checking user {user.username or user.nome} (Lv. {user.livello}, Exp: {user.exp})...")
        
        # Add 0 EXP to trigger level up check
        result = service.add_exp_by_id(user.id_telegram, 0)
        
        if result['leveled_up']:
            print(f" -> LEVELED UP! New Level: {result['new_level']}")
            fixed += 1
        else:
            print(" -> OK")
            
        count += 1
        
    print(f"Finished. Checked {count} users. Fixed {fixed} users.")

if __name__ == "__main__":
    fix_levels()
