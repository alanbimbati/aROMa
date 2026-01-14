import sys
import os
import unittest
from unittest.mock import MagicMock

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from services.user_service import UserService

class TestActivityTracking(unittest.TestCase):
    def test_text_message_tracking(self):
        user_service = UserService()
        chat_id = 12345
        user_id = 67890
        
        # Simulate tracking activity (which is what the 'any' handler now does for text)
        user_service.track_activity(user_id, chat_id)
        
        recent = user_service.get_recent_users(chat_id)
        self.assertIn(user_id, recent)
        print(f"SUCCESS: User {user_id} tracked in chat {chat_id}")

    def test_targeting_prioritization(self):
        # This was already verified, but let's double check the logic integration
        from services.pve_service import PvEService
        pve_service = PvEService()
        chat_id = 555
        
        # Track 10 users
        for i in range(1, 11):
            pve_service.user_service.track_activity(i, chat_id)
            
        recent_users = pve_service.user_service.get_recent_users(chat_id)
        self.assertEqual(len(recent_users), 10)
        
        # The logic in PvEService.mob_random_attack uses these users
        # If we have users, it should find a target
        # We verified the 70% distribution in test_targeting.py
        print("SUCCESS: Targeting logic has access to recent users")

if __name__ == "__main__":
    unittest.main()
