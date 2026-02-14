
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

def hunt():
    load_dotenv()
    db_user = os.getenv('DB_USER', 'alan')
    db_pass = os.getenv('DB_PASSWORD', 'asd1XD2LoL3')
    db_host = os.getenv('DB_HOST', 'localhost')
    db_port = os.getenv('DB_PORT', '5432')
    
    # Check all databases
    for db_name in ['aroma_bot', 'aroma_bot_test', 'postgres']:
        print(f"--- Checking Database: {db_name} ---")
        try:
            url = f'postgresql://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}'
            engine = create_engine(url)
            with engine.connect() as conn:
                # Find tables with likely user columns
                res = conn.execute(text("""
                    SELECT table_name, column_name 
                    FROM information_schema.columns 
                    WHERE column_name ILIKE '%id_Telegram%' 
                       OR column_name ILIKE '%username%'
                       OR column_name ILIKE '%nome%'
                    AND table_schema = 'public'
                """))
                tables = {}
                for row in res:
                    table, col = row
                    if table not in tables: tables[table] = []
                    tables[table].append(col)
                
                for table, cols in tables.items():
                    try:
                        col_str = ", ".join([f"\"{c}\"" for c in cols])
                        data = conn.execute(text(f"SELECT {col_str} FROM \"{table}\" LIMIT 20")).fetchall()
                        if data:
                            print(f"  Table '{table}': {len(data)} rows found (showing up to 20)")
                            for d in data:
                                print(f"    {d}")
                    except Exception as e:
                        print(f"  Error reading table {table}: {e}")
        except Exception as e:
            print(f"Error connecting to {db_name}: {e}")

if __name__ == "__main__":
    hunt()
