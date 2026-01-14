import csv
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from database import Database
from models.system import Livello
from sqlalchemy import text

# EXP Table provided by user
exp_table = {
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

def update_exp():
    db = Database()
    session = db.get_session()
    
    # Check if exp_required column exists, if not add it
    try:
        session.execute(text("SELECT exp_required FROM livello LIMIT 1"))
        print("Column 'exp_required' already exists.")
    except Exception:
        print("Adding exp_required column...")
        session.rollback()  # Clear any error state
        try:
            session.execute(text("ALTER TABLE livello ADD COLUMN exp_required INTEGER DEFAULT 100"))
            session.commit()
            print("Column 'exp_required' added successfully.")
        except Exception as e:
            print(f"Error adding column: {e}")
            session.rollback()
            session.close()
            return
    
    print("Updating exp levels...")
    for level, exp in exp_table.items():
        # Check if level exists
        livello = session.query(Livello).filter_by(livello=level).first()
        if livello:
            livello.exp_required = exp
            # Also update exp_to_lv for backward compatibility if needed
            livello.exp_to_lv = exp 
            print(f"Updated Level {level} -> {exp}")
        else:
            # Create new level entry if it doesn't exist (basic info)
            # We don't have character names for high levels, so just create placeholder
            print(f"Creating Level {level} -> {exp}")
            new_level = Livello(
                livello=level,
                nome=f"Livello {level}",
                exp_required=exp,
                price=0,
                lv_premium=0
            )
            session.add(new_level)
            
    session.commit()
    session.close()
    print("Done!")

if __name__ == "__main__":
    update_exp()
