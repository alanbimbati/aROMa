
import unittest
import time
from services.trap_service import TrapService

class TestTrapService(unittest.TestCase):
    def setUp(self):
        self.trap_service = TrapService()
        self.chat_id = 12345
        self.user_id = 999
        self.placer_id = 888

    def test_arm_trap(self):
        """Test arming a trap"""
        self.trap_service.arm_trap(self.chat_id, self.placer_id, duration=1.0)
        self.assertTrue(self.trap_service.is_trap_active(self.chat_id))
        
        trap = self.trap_service._active_traps[self.chat_id]
        self.assertEqual(trap['state'], 'armed')
        self.assertEqual(trap['placer_id'], self.placer_id)
        
        # Cleanup
        self.trap_service.cancel_trap(self.chat_id)

    def test_timeout_callback(self):
        """Test that timeout fires and sets state to volatile"""
        callback_fired = {'fired': False}
        
        def my_callback(cid):
            if cid == self.chat_id:
                callback_fired['fired'] = True
                
        self.trap_service.arm_trap(self.chat_id, self.placer_id, duration=0.2, on_timeout=my_callback)
        
        # Wait for timeout
        time.sleep(0.3)
        
        self.assertTrue(callback_fired['fired'], "Callback should have fired")
        
        trap = self.trap_service._active_traps.get(self.chat_id)
        self.assertIsNotNone(trap)
        self.assertEqual(trap['state'], 'volatile')

    def test_defuse_success(self):
        """Test successful defuse"""
        self.trap_service.arm_trap(self.chat_id, self.placer_id, duration=1.0)
        
        success, code = self.trap_service.defuse_trap(self.chat_id, self.user_id)
        self.assertTrue(success)
        self.assertEqual(code, 'defused')
        self.assertFalse(self.trap_service.is_trap_active(self.chat_id))

    def test_defuse_fail_volatile(self):
        """Test defuse failing when volatile"""
        self.trap_service.arm_trap(self.chat_id, self.placer_id, duration=0.1)
        time.sleep(0.2) # Wait for volatile
        
        success, code = self.trap_service.defuse_trap(self.chat_id, self.user_id)
        self.assertFalse(success)
        self.assertEqual(code, 'volatile')
        
    def test_trigger(self):
        """Test mechanism triggering on user"""
        self.trap_service.arm_trap(self.chat_id, self.placer_id, duration=0.1)
        time.sleep(0.2)
        
        # Should trigger
        trap_data = self.trap_service.trigger_trap(self.chat_id, self.user_id)
        self.assertIsNotNone(trap_data)
        self.assertEqual(trap_data['placer_id'], self.placer_id)
        
        # Should be gone
        self.assertFalse(self.trap_service.is_trap_active(self.chat_id))
        
    def test_no_trigger_when_armed(self):
        """Test that it does NOT trigger when still armed (timer running)"""
        self.trap_service.arm_trap(self.chat_id, self.placer_id, duration=1.0)
        
        result = self.trap_service.trigger_trap(self.chat_id, self.user_id)
        self.assertIsNone(result)
        self.assertTrue(self.trap_service.is_trap_active(self.chat_id))
        self.trap_service.cancel_trap(self.chat_id)

    def test_nitro_type(self):
        """Test arming check with nitro type"""
        self.trap_service.arm_trap(self.chat_id, self.placer_id, duration=0.1, trap_type='NITRO')
        time.sleep(0.2)
        
        trap_data = self.trap_service.trigger_trap(self.chat_id, self.user_id)
        self.assertIsNotNone(trap_data)
        self.assertEqual(trap_data['trap_type'], 'NITRO')

if __name__ == '__main__':
    unittest.main()
