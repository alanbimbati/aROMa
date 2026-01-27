"""
PostgreSQL Database Configuration
Replace database.py with this file after migration
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.ext.declarative import declarative_base
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

Base = declarative_base()

class Database:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Database, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance
    
    def _initialize(self):
        """Initialize database connection"""
        # Get database configuration from environment
        db_type = os.getenv('DB_TYPE', 'sqlite')
        
        if db_type == 'postgresql':
            # PostgreSQL configuration
            db_host = os.getenv('DB_HOST', 'localhost')
            db_port = os.getenv('DB_PORT', '5432')
            
            # Check for TEST mode
            is_test = os.getenv('TEST') == '1' or os.getenv('TEST_DB') == '1'
            default_db_name = 'aroma_bot_test' if is_test else 'aroma_bot'
            
            db_name = os.getenv('DB_NAME', default_db_name)
            
            # If TEST mode is explicitly set, force test database name if DB_NAME wasn't manually overridden to something else
            # (Logic: if user sets TEST=1, we default to aroma_bot_test, unless they explicitly set DB_NAME to something else)
            if is_test and db_name == 'aroma_bot':
                db_name = 'aroma_bot_test'
                
            print(f"[DATABASE] Config: Host={db_host}, DB={db_name}, TestMode={is_test}")
            db_user = os.getenv('DB_USER', 'aroma_user')
            db_password = os.getenv('DB_PASSWORD', '')
            
            connection_string = f'postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}'
            
            # PostgreSQL engine with optimized settings
            self.engine = create_engine(
                connection_string,
                pool_size=20,           # Increased pool size for concurrency
                max_overflow=40,        # Allow more connections during peaks
                pool_pre_ping=True,     # Verify connections before use
                pool_recycle=3600,      # Recycle connections every hour
                echo=False              # Set to True for SQL debugging
            )
        else:
            # SQLite fallback (for testing)
            test_mode = os.getenv('TEST_DB') == '1'
            db_name = 'test_points.db' if test_mode else 'points.db'
            
            connection_string = f'sqlite:///{db_name}'
            
            self.engine = create_engine(
                connection_string,
                connect_args={'check_same_thread': False, 'timeout': 30},
                echo=False
            )
        
        # Create session factory
        self.SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=self.engine
        )
        
        # Thread-safe session
        self.ScopedSession = scoped_session(self.SessionLocal)
        
        print(f"[DATABASE] Connected to {db_type.upper()} database")
    
    def get_session(self):
        """Get a new database session"""
        return self.SessionLocal()
    
    def get_scoped_session(self):
        """Get a thread-safe scoped session"""
        return self.ScopedSession()
    
    def create_all_tables(self):
        """Create all tables"""
        Base.metadata.create_all(bind=self.engine)
    
    def drop_all_tables(self):
        """Drop all tables (use with caution!)"""
        Base.metadata.drop_all(bind=self.engine)
