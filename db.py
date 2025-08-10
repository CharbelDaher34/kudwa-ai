import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlmodel import SQLModel, Session
from contextlib import contextmanager

# Use environment variable for database URL, with a fallback for local development
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+psycopg2://flow:flow@localhost:5437/flowdb")

engine = create_engine(DATABASE_URL)

# Create a configured "Session" class
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_session():
    """
    Returns a new session from the session factory.
    This is suitable for use in a FastAPI dependency.
    """
    db = SessionLocal()
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
