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
    # Local / dev default (docker-compose) unless we decide to jump straight to sqlite
    docker_default = "postgresql+psycopg2://kudwa:kudwa@db:5432/kudwadb"
    if os.getenv("RENDER") and not os.getenv("ALLOW_DB_FALLBACK"):
        # Instead of hard failing, we will fall back to SQLite as requested
        print("[DB WARN] DATABASE_URL missing on Render; falling back to SQLite (set REAL DB or ALLOW_DB_FALLBACK=1 to suppress).")
        DATABASE_URL = "sqlite:///./fallback.db"
    else:
        DATABASE_URL = docker_default
        print("DATABASE_URL not set. Using local docker-compose fallback (or will later fallback to SQLite if connection fails).")

print(f"Initial DATABASE_URL value: {DATABASE_URL}")

# Render's postgres service provides a URL that starts with postgresql://
# but psycopg2 (SQLAlchemy's default driver) requires postgresql+psycopg2://.
# We will adjust the URL scheme if it's a Render-provided URL.
if DATABASE_URL.startswith("postgresql://") and "+psycopg2" not in DATABASE_URL:
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg2://", 1)
    print(f"Adjusted scheme for psycopg2: {DATABASE_URL}")

FALLBACK_USED = False

def _try_create_engine(url: str):
    try:
        eng = create_engine(url, pool_pre_ping=True)
        # probe connection
        with eng.connect() as conn:
            conn.execute(text("SELECT 1"))
        print(f"Primary database connection OK: {url.split('@')[-1] if '://' in url else url}")
        return eng, False
    except Exception as e:
        print(f"[DB ERROR] Primary database connection failed: {e}")
        return None, True

engine, failed = _try_create_engine(DATABASE_URL)

if failed:
    # If already sqlite we don't double-fallback
    if DATABASE_URL.startswith("sqlite:"):
        print("SQLite fallback already in use; proceeding.")
        from sqlalchemy import create_engine as _ce
        engine = _ce(DATABASE_URL, connect_args={"check_same_thread": False})
        FALLBACK_USED = True
    else:
        # Switch to SQLite fallback
        fallback_path = os.getenv("SQLITE_FALLBACK_PATH", "./fallback.db")
        DATABASE_URL = f"sqlite:///{fallback_path.lstrip('./')}" if not fallback_path.startswith("sqlite:") else fallback_path
        print(f"[DB WARN] Switching to SQLite fallback at {DATABASE_URL}")
        from sqlalchemy import create_engine as _ce
        engine = _ce(DATABASE_URL, connect_args={"check_same_thread": False})
        FALLBACK_USED = True

if FALLBACK_USED:
    print("[DB INFO] Running in fallback (SQLite) mode. Some SQL features may be limited.")

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
