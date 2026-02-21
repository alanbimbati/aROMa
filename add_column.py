import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()
db_type = os.getenv('DB_TYPE', 'sqlite')
if db_type == 'postgresql':
    db_host = os.getenv('DB_HOST', 'localhost')
    db_port = os.getenv('DB_PORT', '5432')
    db_name = os.getenv('DB_NAME', 'aroma_bot')
    db_user = os.getenv('DB_USER', 'aroma_user')
    db_password = os.getenv('DB_PASSWORD', '')
    connection_string = f'postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}'
else:
    db_name = os.getenv('DB_NAME', 'points.db')
    connection_string = f'sqlite:///{db_name}'

print(f"Connecting to {connection_string}")
engine = create_engine(connection_string)

try:
    with engine.connect() as conn:
        conn.execute(text("ALTER TABLE utente ADD COLUMN IF NOT EXISTS notify_on_attack BOOLEAN DEFAULT TRUE"))
        conn.commit()
    print("Column added successfully or already exists")
except Exception as e:
    print(f"Error: {e}")
