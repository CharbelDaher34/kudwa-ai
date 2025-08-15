import os
import sys
import logging
from typing import Any, Dict, Optional, List, Tuple
import json
import re
from functools import lru_cache
from difflib import get_close_matches
from datetime import date
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

# Add parent directory to path to import local modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import our database and inspection utilities
from db import get_db_session, DATABASE_URL
from db_inspector import DatabaseInspector

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    filename="app.log",
    filemode="a",
)
logger = logging.getLogger(__name__)

# Constants
MAX_LONG_DATA = 1000

# Initialize database inspector
db_inspector = DatabaseInspector(DATABASE_URL)

# =====================================================================================
# Utility & Helper Functions
# =====================================================================================

def _to_markdown(rows: List[Dict[str, Any]]) -> str:
    """Convert list of dict rows into a Markdown table."""
    logger.info("_to_markdown called; rows_type=%s, rows_len=%d", type(rows), len(rows) if rows is not None else 0)
    if not rows:
        logger.info("_to_markdown: no rows -> returning placeholder")
        return "(no rows)"
    columns = list(rows[0].keys())
    md_table = "| " + " | ".join(columns) + " |\n"
    md_table += "| " + " | ".join(["---"] * len(columns)) + " |\n"
    for r in rows:
        md_table += "| " + " | ".join(str(r.get(c, "")) for c in columns) + " |\n"
    logger.info("_to_markdown: generated %d table rows", len(rows))
    return md_table


def _is_select_only(query: str) -> bool:
    """Basic safety check ensuring the query is a single SELECT statement."""
    logger.info("_is_select_only called with query: %s", query)
    q = query.strip().strip(";").lower()
    # Disallow common write / ddl operations
    forbidden = ["update", "delete", "insert", "alter", "drop", "create", "grant", "revoke", "truncate"]
    if not q.startswith("select"):
        logger.info("_is_select_only: does not start with select")
        return False
    if any(f in q for f in forbidden):
        logger.info("_is_select_only: contains forbidden keyword")
        return False
    # Disallow multiple statements by semicolon inside
    if ";" in query.strip()[:-1]:  # ignore trailing semicolon
        logger.info("_is_select_only: multiple statements detected")
        return False
    return True


def _ensure_limit(query: str, default_limit: int = 200) -> str:
    """Append a LIMIT clause if none present (case-insensitive) and not an aggregate only."""
    logger.info("_ensure_limit called; default_limit=%d", default_limit)
    q_lower = query.lower()
    if " limit " in q_lower or q_lower.rstrip().endswith(" limit"):
        logger.info("_ensure_limit: query already contains LIMIT")
        return query
    # If it's clearly an aggregate-only query returning few rows, leave it
    if re.search(r"count\s*\(|sum\s*\(|avg\s*\(|min\s*\(|max\s*\(", q_lower) and " group by " not in q_lower:
        logger.info("_ensure_limit: aggregate-only query detected; not adding LIMIT")
        return query
    return query.rstrip("; ") + f" LIMIT {default_limit}"


@lru_cache(maxsize=1)
def _distinct_account_names() -> List[str]:
    """Cached list of distinct account_name values."""
    try:
        from sqlalchemy import text
        logger.info("_distinct_account_names: querying database for distinct account_name")
        with get_db_session() as session:
            result = session.exec(text("SELECT DISTINCT account_name FROM financialstatement"))
            names = sorted([r[0] for r in result if r[0]])
            logger.info("_distinct_account_names: found %d distinct names", len(names))
            return names
    except Exception as e:
        logger.warning(f"Could not load distinct account names: {e}")
        return []


def _enable_trgm_if_possible():
    """Attempt to enable pg_trgm extension (Postgres only); ignore failures."""
    try:
        from sqlalchemy import text
        logger.info("_enable_trgm_if_possible: attempting to enable pg_trgm")
        with get_db_session() as session:
            session.exec(text("CREATE EXTENSION IF NOT EXISTS pg_trgm"))
            logger.info("_enable_trgm_if_possible: executed extension create (if needed)")
    except Exception:
        logger.info("_enable_trgm_if_possible: failed or not applicable; ignoring")
        pass


_enable_trgm_if_possible()


def get_connection():
    """
    Create a database session using our unified database setup.

    Returns:
        Database session context manager

    Raises:
        Exception: If session creation fails
    """
    logger.info("Creating database session for financial data")

    try:
        # Return the context manager from our db module
        logger.info("get_connection: acquiring session context manager from db.get_db_session")
        return get_db_session()
    except Exception as e:
        logger.exception(f"Failed to create database session: {e}")
        raise


# MCP Server initialization
mcp = FastMCP("financial-reports-server")


@mcp.tool(
    name="query_database",
    description=(
        "Primary tool for safely querying financial data. Use this for all data retrieval. "
        "Supports SELECT queries, account name searches, and fetching schema information. "
        "Specify one of `sql_query`, `search_account_term`, or `fetch_schema`."
    ),
)
def query_database(
    sql_query: Optional[str] = None,
    search_account_term: Optional[str] = None,
    fetch_schema: bool = False,
) -> str:
    """
    A unified and safe tool to query the financial database.

    Args:
        sql_query: A read-only SQL SELECT query to execute.
        search_account_term: A term to search for in account names.
        fetch_schema: If True, returns the database schema.

    Returns:
        Query results in Markdown format or an error message in JSON.
    """
    # Ensure exactly one action is requested
    actions = [sql_query, search_account_term, fetch_schema]
    if sum(1 for action in actions if action) != 1:
        return json.dumps({"error": "Specify exactly one of `sql_query`, `search_account_term`, or `fetch_schema`."})

    try:
        if fetch_schema:
            logger.info("query_database: fetching schema")
            return db_inspector.get_schema_text()

        if search_account_term:
            logger.info("query_database: searching account names for '%s'", search_account_term)
            # Use fuzzy search to find the best match
            all_names = _distinct_account_names()
            matches = get_close_matches(search_account_term, all_names, n=10, cutoff=0.6)
            if not matches:
                return f"No account names found matching '{search_account_term}'."
            return _to_markdown([{"matched_account_name": m} for m in matches])

        if sql_query:
            logger.info("query_database: executing SQL query: %s", sql_query)
            if not _is_select_only(sql_query):
                logger.warning("query_database: rejected non-select query")
                return json.dumps({"error": "Only read-only SELECT statements are allowed."})

            safe_query = _ensure_limit(sql_query)
            logger.info("query_database: safe_query=%s", safe_query)
            from sqlalchemy import text

            with get_connection() as session:
                result = session.exec(text(safe_query))
                if not result.returns_rows:
                    return "Query executed successfully, but returned no rows."
                
                columns = list(result.keys())
                rows = [dict(zip(columns, row)) for row in result]
                return _to_markdown(rows) + f"\n\n-- Query executed: {safe_query}"

        return json.dumps({"error": "An unexpected error occurred."})

    except Exception as e:
        logger.exception("query_database failed: %s", e)
        return json.dumps({"error": str(e)})


if __name__ == "__main__":
    logger.info("Starting Financial Reports MCP server...")
    mcp.run()
