"""Database setup and session helpers.

Public objects (imported elsewhere):
  - DATABASE_URL
  - engine
  - SessionLocal
  - get_session (FastAPI dependency)
  - get_db_session (context manager)
  - execute_query (utility for ad‑hoc SQL)
"""

from contextlib import contextmanager
import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlmodel import SQLModel, Session
from contextlib import contextmanager
from dotenv import load_dotenv

# Load .env only when running locally (Render provides env vars directly)
if not os.getenv("RENDER"):
    load_dotenv()

# 1. Resolve DATABASE_URL or use docker-compose default
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://kudwa:kudwa@db:5432/kudwadb",
)

# # 2. Normalize Postgres scheme (Render sometimes omits +psycopg2)
# if DATABASE_URL.startswith("postgresql://") and "+psycopg2" not in DATABASE_URL:
#     DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg2://", 1)

# 3. Create engine (attempt primary; if it fails and not sqlite, fall back to local sqlite)
def _build_engine(url: str):
    kwargs = {"pool_pre_ping": True}
    if url.startswith("sqlite:"):
        kwargs["connect_args"] = {"check_same_thread": False}
    return create_engine(url, **kwargs)

try:
    engine = _build_engine(DATABASE_URL)
    # cheap connectivity probe
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
except Exception:
    if not DATABASE_URL.startswith("sqlite:"):
        fallback_path = os.getenv("SQLITE_FALLBACK_PATH", "./fallback.db")
        DATABASE_URL = (
            fallback_path
            if fallback_path.startswith("sqlite:")
            else f"sqlite:///{fallback_path.lstrip('./')}"
        )
        engine = _build_engine(DATABASE_URL)
    else:
        raise

# 4. Session factory
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

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

def execute_query(query: str, params: dict | None = None):
    """Execute raw SQL and return fetched rows where applicable."""
    with engine.connect() as connection:
        stmt = text(query) if isinstance(query, str) else query
        result = connection.execute(stmt, params or {})
        try:
            return result.fetchall()
        except Exception:
            return result

#%%
# query='''
# select count(names) from (SELECT distinct(account_name) as names from financialstatement )'''
# execute_query(query)
# %%
