from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, declarative_base, scoped_session

Base = declarative_base()

class Database:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Database, cls).__new__(cls)
            # Increase timeout to 30 seconds to handle concurrency better
            cls._instance.engine = create_engine('sqlite:///points.db', connect_args={'timeout': 30})
            
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
