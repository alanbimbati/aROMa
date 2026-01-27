from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, declarative_base, scoped_session

Base = declarative_base()

class Database:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Database, cls).__new__(cls)
            # Increase timeout to 30 seconds to handle concurrency better
            import os
            from sqlalchemy.pool import NullPool
            
            import sys
            is_test = 'unittest' in sys.modules or 'pytest' in sys.modules or os.environ.get('TEST_DB')
            
            if is_test:
                db_path = os.path.abspath("test_points.db")
                print(f"[DEBUG] Using TEST database: {db_path}")
            else:
                db_path = os.path.abspath("points.db")
                
            cls._instance.engine = create_engine(f'sqlite:///{db_path}', poolclass=NullPool, connect_args={'timeout': 30})
            
            # Enable WAL mode for better concurrency
            @event.listens_for(cls._instance.engine, "connect")
            def set_sqlite_pragma(dbapi_connection, connection_record):
                cursor = dbapi_connection.cursor()
                cursor.execute("PRAGMA journal_mode=WAL")
                cursor.execute("PRAGMA synchronous=NORMAL")
                cursor.close()

            Base.metadata.create_all(cls._instance.engine)
            # Use standard sessionmaker but with WAL/timeout enabled
            cls._instance.Session = sessionmaker(bind=cls._instance.engine)
        return cls._instance

    def get_session(self):
        return self.Session()
