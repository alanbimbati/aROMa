
from services.trap_service import TrapService
import time

def test_trap_protection():
    ts = TrapService()
    chat_id = 999
    placer_id = 123
    victim_id = 456
    
    print("Testing Trap Protection Logic...")
    
    # 1. Arm trap
    ts.arm_trap(chat_id, placer_id, duration=0.1)
    
    # Wait for volatile
    time.sleep(0.2)
    
    print(f"Is trap volatile? {ts.has_volatile_trap(chat_id)}")
    
    # 2. Check if placer triggers it (Simulate main.py lambda)
    is_volatile = ts.has_volatile_trap(chat_id)
    current_user = placer_id
    current_placer = ts.get_placer_id(chat_id)
    
    trigger_condition = is_volatile and current_user != current_placer
    print(f"Should Placer trigger? {trigger_condition} (Expected: False)")
    
    if trigger_condition:
        print("❌ FAILED: Placer triggered the trap!")
    else:
        print("✅ SUCCESS: Placer skipped the trap.")
        
    # 3. Check if victim triggers it
    current_user = victim_id
    trigger_condition = is_volatile and current_user != current_placer
    print(f"Should Victim trigger? {trigger_condition} (Expected: True)")
    
    if not trigger_condition:
        print("❌ FAILED: Victim did not trigger the trap!")
    else:
        print("✅ SUCCESS: Victim triggers the trap.")
        
    # Trigger and consume
    if trigger_condition:
        trap = ts.trigger_trap(chat_id, victim_id)
        print(f"Trap triggered by user {victim_id}. Placer was {trap['placer_id']}")

if __name__ == "__main__":
    test_trap_protection()
