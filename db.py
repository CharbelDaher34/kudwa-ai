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

# Resolve DATABASE_URL with environment-aware fallback
RAW_DATABASE_URL = os.getenv("DATABASE_URL")

if RAW_DATABASE_URL:
    DATABASE_URL = RAW_DATABASE_URL
else:
    # Only allow docker-compose fallback when clearly not on Render
    if os.getenv("RENDER"):
        raise RuntimeError(
            "DATABASE_URL is not set in environment. Render should inject it from the managed database. "
            "Verify render.yaml envVars for the backend service and that the deploy includes the database resource."
        )
    DATABASE_URL = "postgresql+psycopg2://kudwa:kudwa@db:5432/kudwadb"
    print("DATABASE_URL not set. Using local docker-compose fallback.")

print(f"Initial DATABASE_URL value: {DATABASE_URL}")

# Render's postgres service provides a URL that starts with postgresql://
# but psycopg2 (SQLAlchemy's default driver) requires postgresql+psycopg2://.
# We will adjust the URL scheme if it's a Render-provided URL.
if DATABASE_URL.startswith("postgresql://") and "+psycopg2" not in DATABASE_URL:
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg2://", 1)
    print(f"Adjusted scheme for psycopg2: {DATABASE_URL}")

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
