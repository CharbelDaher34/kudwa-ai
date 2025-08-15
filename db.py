#%%
import os
import time
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlmodel import SQLModel, Session
from contextlib import contextmanager
from dotenv import load_dotenv
load_dotenv()

# Use environment variable for database URL, with a fallback for local development
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+psycopg2://kudwa:kudwa@db:5432/kudwadb")
print(f"dbbbb: {DATABASE_URL}")

def create_engine_with_retry(database_url: str, max_retries: int = 5, retry_delay: int = 2):
    """Create database engine with retry logic for deployment environments"""
    for attempt in range(max_retries):
        try:
            engine = create_engine(database_url)
            # Test the connection
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            print(f"Database connection successful on attempt {attempt + 1}")
            return engine
        except Exception as e:
            if attempt < max_retries - 1:
                print(f"Database connection attempt {attempt + 1} failed: {e}")
                print(f"Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
            else:
                print(f"All database connection attempts failed. Last error: {e}")
                # For deployment, we still return the engine - let the app handle the error
                # This prevents import-time failures
                return create_engine(database_url)

engine = create_engine_with_retry(DATABASE_URL)

# Create a configured "Session" class
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_session():
    """
    Returns a new session from the session factory.
    This is suitable for use in a FastAPI dependency.
    """
    db = Session(engine)
    try:
        yield db
    finally:
        db.close()

@contextmanager
def get_db_session():
    """
    Provides a session for use in scripts and other non-request contexts.
    This ensures the session is always closed and handles transactions.
    """
    session = Session(engine)
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

def execute_query(query: str, params: dict = None):
    """
    Executes a raw SQL query using the engine.
    Returns the result as a list of rows.
    """
    with engine.connect() as connection:
        # If a raw SQL string is provided, convert it to a SQLAlchemy TextClause
        stmt = text(query) if isinstance(query, str) else query
        result = connection.execute(stmt, params or {})
        # Fetch all rows where possible
        try:
            return result.fetchall()
        except Exception:
            # Some executions may not return rows (e.g., DDL); return the raw result
            return result

#%%
# query='''
# select count(names) from (SELECT distinct(account_name) as names from financialstatement )'''
# execute_query(query)
# %%
