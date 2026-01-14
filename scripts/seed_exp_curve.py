#!/usr/bin/env python3
"""
Seed Script: Update Livello table with Quadratic EXP Curve
Formula: EXP_Required = 100 * (Level ^ 2.2)
"""
import sqlite3
import os
import math

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'points.db')

def calculate_exp_required(level):
    if level <= 1:
        return 0
    
def calculate_exp_required(level):
    if level <= 1: return 0
    
    # User provided checkpoints (Shifted +1: User's Lvl 1 value is for DB Lvl 2)
    # User: 1->100, 2->235 ... 10->4575
    # DB: 2->100, 3->235 ... 11->4575
    
    raw_checkpoints = {
        1: 100, 2: 235, 3: 505, 4: 810, 5: 1250, 6: 1725, 7: 2335, 8: 2980, 9: 3760, 10: 4575,
        11: 5525, 12: 6510, 13: 7630, 14: 8785, 15: 10075, 16: 11400, 17: 12860, 18: 14355, 19: 15985, 20: 17650,
        21: 19450, 22: 21285, 23: 23255, 24: 25260, 25: 27400, 26: 29575, 27: 31885, 28: 34230, 29: 36710, 30: 39225,
        31: 41875, 32: 44560, 33: 47380, 34: 50235, 35: 53225, 36: 56250, 37: 59410, 38: 62605, 39: 65935, 40: 70000,
        41: 75000, 42: 80000, 43: 85000, 44: 90000, 45: 95000, 46: 100000, 47: 105000, 48: 110000, 49: 115000, 50: 120000,
        51: 125000, 52: 130000, 53: 135000, 54: 140000, 55: 145000, 56: 150000, 57: 155000, 58: 160000, 59: 165000, 60: 170000,
        61: 175000, 62: 180000, 63: 185000, 64: 190000, 65: 195000, 66: 200000, 67: 205000, 68: 210000, 69: 215000, 70: 220000,
        71: 225000, 72: 230000, 73: 235000, 74: 240000, 75: 245000, 76: 250000, 77: 255000, 78: 260000, 79: 265000, 80: 270000,
        81: 275000, 82: 280000, 83: 285000, 84: 290000, 85: 295000, 86: 300000, 87: 305000, 88: 310000, 89: 315000, 90: 320000,
        91: 325000, 92: 330000, 93: 335000, 94: 340000, 95: 345000, 96: 350000, 97: 355000, 98: 360000, 99: 365000, 100: 370000
    }
    
    # Shifted map
    checkpoints = {k + 1: v for k, v in raw_checkpoints.items()}
    
    if level in checkpoints:
        return checkpoints[level]
        
    # Fallback for levels > 101 (User provided up to 100, which maps to 101)
    if level > 101:
        return 370000 + ((level - 101) * 5000)
        
    return int(100 * (level ** 2))

def seed_exp_curve():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # Ensure exp_required column exists (it might be nullable from previous migration)
        # We don't need to add it if it exists, but we should check/add if missing
        try:
            cursor.execute("SELECT exp_required FROM livello LIMIT 1")
        except sqlite3.OperationalError:
            print("⚠️  Column exp_required missing, adding it...")
            cursor.execute("ALTER TABLE livello ADD COLUMN exp_required INTEGER")
            conn.commit()

        print("Updating EXP requirements for levels 1-100...")
        
        updated_count = 0
        for level in range(1, 101):
            exp_req = calculate_exp_required(level)
            
            # Check if level exists
            cursor.execute("SELECT id FROM livello WHERE livello = ?", (level,))
            result = cursor.fetchone()
            
            if result:
                # Update existing level
                cursor.execute(
                    "UPDATE livello SET exp_required = ? WHERE livello = ?",
                    (exp_req, level)
                )
                updated_count += 1
            else:
                # Create level if missing (basic template)
                cursor.execute(
                    """
                    INSERT INTO livello (livello, nome, exp_required, price, description)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (level, f"Livello {level}", exp_req, 0, "Livello generato automaticamente")
                )
                updated_count += 1
                
        conn.commit()
        print(f"✅ Updated {updated_count} levels with new EXP curve.")
        
        # Verify a few values
        print("\nVerification (Sample Levels):")
        for lvl in [2, 5, 10, 20, 50, 100]:
            cursor.execute("SELECT exp_required FROM livello WHERE livello = ?", (lvl,))
            res = cursor.fetchone()
            if res:
                print(f"Lvl {lvl}: {res[0]} EXP")
        
    except Exception as e:
        print(f"❌ Seeding failed: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    seed_exp_curve()
