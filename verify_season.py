from services.season_manager import SeasonManager
import os
import sys

# Force test mode if argument provided
if len(sys.argv) > 1 and sys.argv[1] == 'test':
    os.environ['TEST'] = '1'
    print("🔧 Running in TEST mode")

try:
    sm = SeasonManager()
    season = sm.get_active_season()

    if season:
        print(f"✅ Active Season found: {season.name}")
        print(f"   ID: {season.id}")
        print(f"   Start: {season.start_date}")
        print(f"   End: {season.end_date}")
        print(f"   Theme: {season.theme}")
    else:
        print("❌ No active season found!")
        
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
