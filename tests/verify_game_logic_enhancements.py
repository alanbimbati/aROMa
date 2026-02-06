import sys
import os
from unittest.mock import MagicMock, patch, PropertyMock
import datetime

# Add project root to path
sys.path.append('/home/alan/Documenti/Coding/aroma')

from services.user_service import UserService
from services.market_service import MarketService
from services.guild_service import GuildService
from models.user import Utente
from models.resources import Resource, UserResource
from models.items import Collezionabili
from models.guild import Guild, GuildMember, GuildItem
from models.market import MarketListing

def test_fatigue_logic():
    print("Testing Fatigue Logic...")
    user_service = UserService()
    
    # Mock user
    user = MagicMock(spec=Utente)
    user.max_health = 100
    
    # Case 1: Healthy
    user.current_hp = 50
    user.health = 50
    assert user_service.check_fatigue(user) is False
    
    # Case 2: Fatigued (4 HP)
    user.current_hp = 4
    user.health = 4
    assert user_service.check_fatigue(user) is True
    
    # Case 3: Dead (0 HP)
    user.current_hp = 0
    user.health = 0
    assert user_service.check_fatigue(user) is False
    
    print("✅ Fatigue Logic Verified")

def test_resource_market_guild():
    print("Testing Resource Market & Guild Storage...")
    
    # We'll use patches to avoid DB calls
    with patch('database.Database.get_session') as mock_session_factory:
        session = MagicMock()
        mock_session_factory.return_value = session
        
        market_service = MarketService()
        guild_service = GuildService()
        
        user_id = 123456
        resource_name = "Rottami Metallici"
        resource_id = 1
        
        # --- Market Listing Test ---
        # Mock user
        # Note: We don't use spec=Utente here to avoid PropertyMock complexity if not needed, 
        # but for points we need it to be an int.
        user = MagicMock()
        user.id_telegram = user_id
        user.points = 1000
        
        # Configure session.query chain
        query_mock = MagicMock()
        session.query.return_value = query_mock
        filter_mock = MagicMock()
        query_mock.filter_by.return_value = filter_mock
        
        # First call to filter_by().first() should return user
        # Second call to filter_by().count() should return 0 (no regular items)
        filter_mock.first.return_value = user
        filter_mock.count.return_value = 0
        
        # Mock resource ID fetch and quantity check
        execute_mock = MagicMock()
        session.execute.return_value = execute_mock
        # 1. resource_id = ...scalar()
        # 2. resource_qty = ...scalar()
        execute_mock.scalar.side_effect = [resource_id, 10]
        
        success, msg = market_service.list_item(user_id, resource_name, 5, 100)
        print(f"Market List Result: {msg}")
        assert success is True
        assert "Annuncio creato" in msg
        
        # --- Market Buy Test ---
        # Reset mocks
        listing = MagicMock()
        listing.item_name = resource_name
        listing.quantity = 5
        listing.status = 'active'
        listing.seller_id = 999
        listing.price_per_unit = 100
        listing.expires_at = datetime.datetime.now() + datetime.timedelta(days=1)
        listing.created_at = datetime.datetime.now()
        
        # buy_item calls:
        # 1. buyer = query(Utente).filter_by(id_telegram=buyer_id).first()
        # 2. listing = query(MarketListing).filter_by(id=listing_id).first()
        # 3. seller = query(Utente).filter_by(id_telegram=listing.seller_id).first()
        filter_mock.first.side_effect = [user, listing, MagicMock()]
        
        # Inside buy_item, text check for resource_id
        execute_mock.scalar.side_effect = [resource_id]
        
        with patch('services.crafting_service.CraftingService.add_resource_drop', return_value=True) as mock_add_res:
            success, msg = market_service.buy_item(user_id, 1)
            print(f"Market Buy Result: {msg}")
            if not success:
                 print(f"DEBUG: buy_item failed with: {msg}")
            assert success is True
            assert "Acquistato" in msg
            mock_add_res.assert_called_once()
        
        # --- Guild Deposit Test ---
        # Reset mocks
        # deposit_item calls:
        # 1. resource_id = execute().scalar()
        # 2. resource_qty = execute().scalar()
        execute_mock.scalar.side_effect = [resource_id, 10]
        
        # 3. member = query(GuildMember).filter_by(user_id=user_id).first()
        # 4. guild_item = query(GuildItem).filter_by(...).first()
        filter_mock.first.side_effect = [MagicMock(), None] 
        
        with patch('services.item_service.ItemService.get_item_by_user', return_value=0):
            success, msg = guild_service.deposit_item(user_id, resource_name, 5)
            print(f"Guild Deposit Result: {msg}")
            assert success is True
            assert "depositato" in msg
            
        # --- Guild Withdraw Test ---
        # Reset mocks
        # withdraw_item calls:
        # 1. member = query(GuildMember).filter_by(user_id=user_id).first()
        # 2. guild_item = query(GuildItem).filter_by(...).first()
        filter_mock.first.side_effect = [MagicMock(), MagicMock(quantity=10)]
        
        # 3. resource_id = execute().scalar()
        execute_mock.scalar.side_effect = [resource_id]
        
        with patch('services.crafting_service.CraftingService.add_resource_drop', return_value=True) as mock_add_res_guild:
            success, msg = guild_service.withdraw_item(user_id, resource_name, 5)
            print(f"Guild Withdraw Result: {msg}")
            assert success is True
            assert "prelevato" in msg
            mock_add_res_guild.assert_called_once()

    print("✅ Resource Market & Guild Storage Verified")

if __name__ == "__main__":
    try:
        test_fatigue_logic()
        test_resource_market_guild()
        print("\n✨ ALL TESTS PASSED! ✨")
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
