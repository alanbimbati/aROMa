from sqlalchemy import create_engine, inspect, text
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def fix_sequences():
    print("🔧 Fixing PostgreSQL sequences...")
    
    # Get database configuration
    db_host = os.getenv('DB_HOST', 'localhost')
    db_port = os.getenv('DB_PORT', '5432')
    db_name = os.getenv('DB_NAME', 'aroma_bot')
    db_user = os.getenv('DB_USER', 'alan')
    db_password = os.getenv('DB_PASSWORD', '')
    
    connection_string = f'postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}'
    engine = create_engine(connection_string)
    
    with engine.connect() as conn:
        # Get all tables
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        
        for table in tables:
            try:
                # Check if table has 'id' column
                columns = [c['name'] for c in inspector.get_columns(table)]
                if 'id' in columns:
                    # Get max id
                    result = conn.execute(text(f"SELECT MAX(id) FROM {table}"))
                    max_id = result.scalar() or 0
                    
                    # Reset sequence
                    # PostgreSQL sequence naming convention is usually table_id_seq
                    seq_name = f"{table}_id_seq"
                    
                    # Check if sequence exists
                    seq_check = conn.execute(text(f"SELECT 1 FROM pg_class WHERE relname = '{seq_name}'"))
                    if seq_check.scalar():
                        next_val = max_id + 1
                        print(f"  🔄 Updating {seq_name} to {next_val}...")
                        conn.execute(text(f"ALTER SEQUENCE {seq_name} RESTART WITH {next_val}"))
                        conn.commit()
            except Exception as e:
                print(f"  ⚠️  Error processing {table}: {e}")
                
    print("✅ Sequences fixed!")

if __name__ == "__main__":
    fix_sequences()
