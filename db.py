#%%
import os
from sqlalchemy import create_engine, text
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
query='''
SELECT
    CASE
        WHEN account_name LIKE '%labor_expense%' THEN 'Labor Expense'
        WHEN account_name LIKE '%shipping_expense%' THEN 'Shipping Expense'
        WHEN account_name LIKE '%technology_expense%' THEN 'Technology Expense'
        WHEN account_name LIKE '%facility_cost%' THEN 'Facility Cost'
        WHEN account_name LIKE '%marketing_expense%' THEN 'Marketing Expense'
        WHEN account_name LIKE '%communication_expense%' THEN 'Communication Expense'
        WHEN account_name LIKE '%material_cost%' THEN 'Material Cost'
        WHEN account_name LIKE '%travel_expense%' THEN 'Travel Expense'
        WHEN account_name LIKE '%utility_expense%' THEN 'Utility Expense'
        WHEN account_name LIKE '%office_expense%' THEN 'Office Expense'
        WHEN account_name LIKE '%equipment_expense%' THEN 'Equipment Expense'
        WHEN account_name LIKE '%insurance_expense%' THEN 'Insurance Expense'
        WHEN account_name LIKE '%rd_expense%' THEN 'R&D Expense'
        WHEN account_name LIKE '%rd_cost%' THEN 'R&D Cost'
        WHEN account_name LIKE '%expense_category%' THEN 'Expense Category'
        WHEN account_name LIKE '%depreciation_expense%' THEN 'Depreciation Expense'
        WHEN account_name LIKE '%tax_expense%' THEN 'Tax Expense'
        WHEN account_name LIKE '%banking_expense%' THEN 'Banking Expense'
        WHEN account_name LIKE '%operations_expense%' THEN 'Operations Expense'
        WHEN account_name LIKE '%meal_expense%' THEN 'Meal Expense'
        ELSE 'Other Expenses'
    END AS expense_category,
    SUM(amount) AS total_amount
FROM
    financialstatement
WHERE account_name LIKE '%expense%' OR account_name LIKE '%cost%'
GROUP BY
    expense_category
ORDER BY
    total_amount DESC;'''
execute_query(query)
# %%
