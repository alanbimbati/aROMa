#!/usr/bin/env python3
"""
Migration: Add transformation temporal fields
Adds transformation_expires_at and current_transformation to utente table
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from database import Database
from sqlalchemy import text

def upgrade():
    """Add transformation temporal tracking columns"""
    db = Database()
    session = db.get_session()
    
    print("🔄 Starting migration: add_transformation_fields")
    
    try:
        # Check and add transformation_expires_at
        try:
            session.execute(text(
                "ALTER TABLE utente ADD COLUMN transformation_expires_at TIMESTAMP WITHOUT TIME ZONE"
            ))
            session.commit()
            print("✅ Added transformation_expires_at column")
        except Exception as e:
            if "already exists" in str(e).lower() or "duplicate column" in str(e).lower():
                print("ℹ️  transformation_expires_at already exists")
            else:
                raise
        
        # Check and add current_transformation
        try:
            session.execute(text(
                "ALTER TABLE utente ADD COLUMN current_transformation VARCHAR(100)"
            ))
            session.commit()
            print("✅ Added current_transformation column")
        except Exception as e:
            if "already exists" in str(e).lower() or "duplicate column" in str(e).lower():
                print("ℹ️  current_transformation already exists")
            else:
                raise
        
        print("✅ Migration completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        session.rollback()
        return False
    finally:
        session.close()

def downgrade():
    """Remove transformation temporal tracking columns"""
    db = Database()
    session = db.get_session()
    
    print("🔄 Starting rollback: remove transformation fields")
    
    try:
        session.execute(text("ALTER TABLE utente DROP COLUMN IF EXISTS transformation_expires_at"))
        session.execute(text("ALTER TABLE utente DROP COLUMN IF EXISTS current_transformation"))
        session.commit()
        print("✅ Rollback completed successfully!")
        return True
    except Exception as e:
        print(f"❌ Rollback failed: {e}")
        session.rollback()
        return False
    finally:
        session.close()

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--downgrade", action="store_true", help="Rollback migration")
    args = parser.parse_args()
    
    if args.downgrade:
        success = downgrade()
    else:
        success = upgrade()
    
    sys.exit(0 if success else 1)
