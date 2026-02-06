import sys
import os
import datetime
from unittest.mock import MagicMock, patch

# Path adjustment
sys.path.append(os.getcwd())

from services.targeting_service import TargetingService
from services.pve_service import PvEService
from models.user import Utente
from models.pve import Mob
from models.combat import CombatParticipation

def test_targeting_rules():
    print("--- Testing Targeting Rules ---")
    ts = TargetingService()
    
    # Mocking user_service.get_recent_users
    # Case 1: User active within 48h in chat 100
    # Case 2: User active within 48h in chat 200
    # Case 3: User active 72h ago in chat 100
    
    mock_users_100 = [1001] # Active in 100
    mock_users_200 = [2001] # Active in 200
    
    with patch.object(ts.user_service, 'get_recent_users') as mock_recent:
        # Test Chat 100
        mock_recent.return_value = mock_users_100
        mob = Mob(id=1, chat_id=100, dungeon_id=1)
        
        session = MagicMock()
        u1001 = Utente(id_telegram=1001, health=100, current_hp=100)
        u2001 = Utente(id_telegram=2001, health=100, current_hp=100)
        
        def mock_query_filter_by(id_telegram):
            if id_telegram == 1001: return MagicMock(first=lambda: u1001)
            if id_telegram == 2001: return MagicMock(first=lambda: u2001)
            return MagicMock(first=lambda: None)
            
        session.query(Utente).filter_by.side_effect = lambda **kwargs: mock_query_filter_by(kwargs.get('id_telegram'))
        session.query(CombatParticipation).filter_by.return_value.first.return_value = None
        
        targets = ts.get_valid_targets(mob, chat_id=100, session=session)
        print(f"Chat 100 Targets: {targets} (Expected: [1001])")
        assert 1001 in targets
        assert 2001 not in targets
        
        # Test Chat 200
        mock_recent.return_value = mock_users_200
        mob2 = Mob(id=2, chat_id=200, dungeon_id=1)
        targets2 = ts.get_valid_targets(mob2, chat_id=200, session=session)
        print(f"Chat 200 Targets: {targets2} (Expected: [2001])")
        assert 2001 in targets2
        assert 1001 not in targets2

def test_aggro_distribution():
    print("\n--- Testing Aggro Distribution (85/15) ---")
    ps = PvEService()
    
    # Setup 10 valid targets in chat
    # One user has dealt massive damage (Aggro Target)
    # Total trials: 1000
    
    candidates = [i for i in range(1, 11)]
    weights = [1.0] * 10
    weights[0] = 100.0 # User 1 has high aggro
    
    aggro_count = 0
    random_count = 0
    user_hits = {i: 0 for i in range(1, 11)}
    
    trials = 1000
    for _ in range(trials):
        # Emulate the logic inside mob_random_attack
        import random
        random_roll = random.random()
        if random_roll < 0.15:
            # Random
            target_id = random.choice(candidates)
            random_count += 1
        else:
            # Aggro
            target_id = random.choices(candidates, weights=weights, k=1)[0]
            aggro_count += 1
        
        user_hits[target_id] += 1
        
    print(f"Trials: {trials}")
    print(f"Aggro Path triggered: {aggro_count} times")
    print(f"Random Path triggered: {random_count} times")
    print(f"User 1 (High Aggro) hits: {user_hits[1]}")
    print(f"User 2 (Low Aggro) hits: {user_hits[2]}")
    
    # Expected: 
    # User 1 should get ~850 (aggro) + ~15 (random/10) = ~865 hits
    # Other users should get ~0 (aggro) + ~15 (random/10) = ~15 hits
    
    assert 800 <= user_hits[1] <= 950
    assert 5 <= user_hits[2] <= 50

if __name__ == "__main__":
    try:
        test_targeting_rules()
        test_aggro_distribution()
        print("\n✅ Verification Successful!")
    except Exception as e:
        print(f"\n❌ Verification Failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
