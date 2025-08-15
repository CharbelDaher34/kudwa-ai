import time
import logging
from sqlalchemy.exc import OperationalError
from sqlalchemy import create_engine, text
from typing import Optional

logger = logging.getLogger(__name__)

def wait_for_database(database_url: str, max_retries: int = 30, retry_delay: float = 2.0) -> bool:
    """
    Wait for database to become available with exponential backoff.
    
    Args:
        database_url: Database connection string
        max_retries: Maximum number of retry attempts
        retry_delay: Initial delay between retries in seconds
    
    Returns:
        True if database is available, False if max retries exceeded
    """
    for attempt in range(1, max_retries + 1):
        try:
            # Create a temporary engine for testing connection
            test_engine = create_engine(database_url, pool_timeout=5, pool_recycle=300)
            
            # Test the connection
            with test_engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            
            test_engine.dispose()
            print(f"Database connection successful on attempt {attempt}")
            return True
            
        except OperationalError as e:
            if attempt == max_retries:
                print(f"Database connection failed after {max_retries} attempts. Last error: {e}")
                return False
            
            print(f"Database connection attempt {attempt} failed: {e}")
            print(f"Retrying in {retry_delay} seconds...")
            time.sleep(retry_delay)
            
            # Exponential backoff with jitter
            retry_delay = min(retry_delay * 1.5, 30.0)
            
        except Exception as e:
            print(f"Unexpected error during database connection attempt {attempt}: {e}")
            if attempt == max_retries:
                return False
            time.sleep(retry_delay)
    
    return False

def create_tables_with_retry(engine, metadata, max_retries: int = 5) -> bool:
    """
    Create database tables with retry logic.
    
    Args:
        engine: SQLAlchemy engine
        metadata: SQLModel metadata
        max_retries: Maximum number of retry attempts
    
    Returns:
        True if tables created successfully, False otherwise
    """
    for attempt in range(1, max_retries + 1):
        try:
            metadata.create_all(engine)
            print("Database tables created successfully")
            return True
            
        except OperationalError as e:
            if attempt == max_retries:
                print(f"Failed to create tables after {max_retries} attempts. Last error: {e}")
                return False
            
            print(f"Table creation attempt {attempt} failed: {e}")
            print(f"Retrying in {attempt * 2} seconds...")
            time.sleep(attempt * 2)
            
        except Exception as e:
            print(f"Unexpected error during table creation attempt {attempt}: {e}")
            if attempt == max_retries:
                return False
            time.sleep(attempt * 2)
    
    return False
