#%%
import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlmodel import SQLModel, Session
from contextlib import contextmanager
from dotenv import load_dotenv

# Only load .env file in local development. Render will set the env vars directly.
if os.getenv("RENDER") is None:
    load_dotenv()

# Use environment variable for database URL, with a fallback for local development
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+psycopg2://kudwa:kudwa@db:5432/kudwadb")
print(f"DATABASE_URL used: {DATABASE_URL}")

# Render's postgres service provides a URL that starts with postgresql://
# but psycopg2 (SQLAlchemy's default driver) requires postgresql+psycopg2://.
# We will adjust the URL scheme if it's a Render-provided URL.
if DATABASE_URL and DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg2://", 1)
    print(f"Adjusted DATABASE_URL for psycopg2: {DATABASE_URL}")

engine = create_engine(DATABASE_URL)

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
