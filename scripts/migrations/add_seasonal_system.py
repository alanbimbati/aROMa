"""
Migration script to add seasonal path tables (season, season_progress, season_reward)
"""

from sqlalchemy import create_engine, text
import datetime

def migrate():
    engine = create_engine('sqlite:///points.db')
    
    with engine.connect() as conn:
        print("🔧 Resetting and creating seasonal tables...")
        
        # Drop existing tables to reset progress
        conn.execute(text("DROP TABLE IF EXISTS season_reward"))
        conn.execute(text("DROP TABLE IF EXISTS season_progress"))
        conn.execute(text("DROP TABLE IF EXISTS season"))
        
        # Season table
        conn.execute(text("""
            CREATE TABLE season (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                start_date DATETIME NOT NULL,
                end_date DATETIME NOT NULL,
                is_active BOOLEAN DEFAULT 1,
                exp_multiplier FLOAT DEFAULT 1.0,
                description TEXT,
                final_reward_name TEXT
            )
        """))
        
        # Season Progress table
        conn.execute(text("""
            CREATE TABLE season_progress (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                season_id INTEGER,
                current_exp INTEGER DEFAULT 0,
                current_level INTEGER DEFAULT 1,
                has_premium_pass BOOLEAN DEFAULT 0,
                last_update DATETIME,
                FOREIGN KEY(season_id) REFERENCES season(id)
            )
        """))
        
        # Season Reward table
        conn.execute(text("""
            CREATE TABLE season_reward (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                season_id INTEGER,
                level_required INTEGER NOT NULL,
                reward_type TEXT NOT NULL,
                reward_value TEXT NOT NULL,
                reward_name TEXT NOT NULL,
                is_premium BOOLEAN DEFAULT 0,
                icon TEXT,
                FOREIGN KEY(season_id) REFERENCES season(id)
            )
        """))
        
        now = datetime.datetime.now()
        
        # Helper to generate 30 rewards
        def gen_rewards(char_ids, names, base_wumpa=50):
            rewards = []
            for lv in range(1, 31):
                is_premium = 1 if lv % 2 == 0 else 0
                if lv % 3 == 0 and char_ids:
                    cid = char_ids.pop(0)
                    name = names.pop(0)
                    rewards.append((lv, 'character', str(cid), name, is_premium, '👤'))
                else:
                    val = base_wumpa * lv
                    rewards.append((lv, 'points', str(val), f"{val} Wumpa", is_premium, '💰'))
            return rewards

        seasons_data = [
            {
                "name": "Stagione 1: Dragonball Saga",
                "desc": "Rivivi le avventure di Goku e compagni!",
                "final_reward": "Shenron",
                "rewards": [
                    (1, 'character', '60', 'Goku', 0, '👤'),
                    (2, 'character', '61', 'Vegeta', 0, '👤'),
                    (3, 'character', '62', 'Piccolo', 0, '👤'),
                    (4, 'character', '151', 'Jiren', 1, '👤'), # Premium
                    (5, 'character', '78', 'Goku SSJ', 0, '👤'),
                    (6, 'character', '79', 'Vegeta SSJ', 0, '👤'),
                    (7, 'character', '80', 'Gohan SSJ', 0, '👤'),
                    (8, 'points', '500', '500 Wumpa', 1, '💰'),
                    (9, 'character', '260', 'C16', 0, '👤'),
                    (10, 'character', '261', 'C17', 0, '👤'),
                    (11, 'character', '262', 'C18', 0, '👤'),
                    (12, 'points', '800', '800 Wumpa', 1, '💰'),
                    (13, 'character', '263', 'Freezer (Prima Forma)', 0, '👤'),
                    (14, 'character', '264', 'Freezer (Seconda Forma)', 0, '👤'),
                    (15, 'character', '265', 'Freezer (Terza Forma)', 0, '👤'),
                    (16, 'character', '266', 'Freezer (Corpo Perfetto)', 0, '👤'),
                    (17, 'character', '267', 'Golden Freezer', 1, '👤'), # Premium
                    (18, 'points', '1200', '1200 Wumpa', 0, '💰'),
                    (19, 'character', '268', 'Cell (Imperfetto)', 0, '👤'),
                    (20, 'character', '269', 'Cell (Semi-Perfetto)', 0, '👤'),
                    (21, 'character', '270', 'Cell (Perfetto)', 0, '👤'),
                    (22, 'character', '271', 'Cell (Super Perfetto)', 0, '👤'),
                    (23, 'points', '1500', '1500 Wumpa', 1, '💰'),
                    (24, 'character', '272', 'Majin Buu (Grasso)', 0, '👤'),
                    (25, 'character', '273', 'Super Buu', 0, '👤'),
                    (26, 'character', '274', 'Kid Buu', 1, '👤'), # Premium
                    (27, 'points', '2000', '2000 Wumpa', 0, '💰'),
                    (28, 'points', '2500', '2500 Wumpa', 1, '💰'),
                    (29, 'character', '226', 'Porunga', 1, '👤'), # Premium
                    (30, 'character', '225', 'Shenron', 0, '👤') # Final Reward (Free)
                ]
            },
            {
                "name": "Stagione 2: Final Fantasy Journey",
                "desc": "Un viaggio attraverso i mondi di Final Fantasy.",
                "final_reward": "Bahamut",
                "rewards": gen_rewards(
                    [1, 30, 31, 32, 33, 34, 36, 37, 195, 210],
                    ["Chocobo", "Cloud", "Tifa", "Sephiroth", "Squall", "Rinoa", "Tidus", "Yuna", "Bahamut", "Zodiark"]
                )
            },
            {
                "name": "Stagione 3: JRPG Legends",
                "desc": "I grandi classici del gioco di ruolo giapponese.",
                "final_reward": "Sora",
                "rewards": gen_rewards(
                    [3, 39, 40, 41, 72, 73, 100, 101, 129, 132],
                    ["Slime", "Dante", "Vergil", "Nero", "Geralt", "Ciri", "Sora", "Riku", "Shulk", "Isaac"]
                )
            },
            {
                "name": "Stagione 4: Nintendo & Crossover",
                "desc": "Il meglio di Nintendo e oltre!",
                "final_reward": "Arceus",
                "rewards": gen_rewards(
                    [4, 5, 6, 7, 15, 16, 24, 25, 213, 221],
                    ["Pikachu", "Bulbasaur", "Squirtle", "Charmander", "Mario", "Luigi", "Link", "Zelda", "Arceus", "Mewtwo"]
                )
            }
        ]

        for i, s_data in enumerate(seasons_data):
            is_active = 1 if i == 0 else 0
            start_date = now + datetime.timedelta(days=30*i)
            end_date = start_date + datetime.timedelta(days=30)
            
            conn.execute(text("""
                INSERT INTO season (name, start_date, end_date, is_active, exp_multiplier, description, final_reward_name)
                VALUES (:name, :start, :end, :active, 1.0, :desc, :reward)
            """), {
                "name": s_data["name"],
                "start": start_date,
                "end": end_date,
                "active": is_active,
                "desc": s_data["desc"],
                "reward": s_data["final_reward"]
            })
            
            # Get season ID
            season_id = conn.execute(text("SELECT id FROM season WHERE name = :name"), {"name": s_data["name"]}).fetchone()[0]
            
            for r in s_data["rewards"]:
                conn.execute(text("""
                    INSERT INTO season_reward (season_id, level_required, reward_type, reward_value, reward_name, is_premium, icon)
                    VALUES (:sid, :lv, :type, :val, :name, :prem, :icon)
                """), {
                    "sid": season_id,
                    "lv": r[0],
                    "type": r[1],
                    "val": r[2],
                    "name": r[3],
                    "prem": r[4],
                    "icon": r[5]
                })
            
        conn.commit()
        print(f"✅ Seasonal system refactored and seeded with {len(seasons_data)} themed seasons (30 rewards each)!")

if __name__ == "__main__":
    migrate()
