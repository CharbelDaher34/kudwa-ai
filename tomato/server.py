import os
import sys
import logging
from typing import Any, Dict, Optional
import json
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP
from rapidfuzz import fuzz

# Add parent directory to path to import local modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import our database and inspection utilities
from db import get_db_session, DATABASE_URL
from db_inspector import DatabaseInspector
from data.models import UnifiedReport, Account, FinancialEntry

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
DEFAULT_MAX_ROWS = 100

# Initialize database inspector
db_inspector = DatabaseInspector(DATABASE_URL)


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
        return get_db_session()
    except Exception as e:
        logger.error(f"Failed to create database session: {e}")
        raise


# MCP Server initialization
mcp = FastMCP("financial-reports-server")


@mcp.tool(
    name="get_tables",
    description="""🔍 DISCOVERY TOOL: Explore Financial Database Schema

PURPOSE: Get a complete overview of all available tables in the financial reporting database.
This is your starting point for database exploration and should be used first.

WHEN TO USE:
- Beginning any database exploration session
- User asks "what financial data is available?" or "show me the database structure"
- Need to understand the overall schema before diving into specific queries

USAGE PATTERN:
1. Call this tool first to see all available tables
2. Identify relevant tables for the user's question
3. Use describe_table() on specific tables for detailed structure

The main tables in our financial system are:
- unifiedreport: Financial report metadata (combines report info and financial statements)
- account: Chart of accounts with hierarchical structure
- financialentry: Individual financial values for accounts

RETURNS: JSON list of all tables with catalog, schema, and table names

NEXT STEPS: Use describe_table(table="table_name") for detailed table structure
    """,
)
def get_tables() -> str:
    """
    Retrieve and return a list containing information about all tables in the financial database.

    Returns:
        str: JSON string containing table information
    """
    try:
        # Use our database inspector to get table information
        tables_info = db_inspector.get_tables_info()
        
        # Convert to the expected format
        results = []
        for table_name in tables_info.keys():
            results.append({
                "TABLE_CAT": "financial_db", 
                "TABLE_SCHEM": "public", 
                "TABLE_NAME": table_name
            })

        return json.dumps(results, indent=2)
    except Exception as e:
        logger.error(f"Error retrieving tables: {e}")
        raise


@mcp.tool(
    name="describe_table",
    description="""📋 SCHEMA ANALYSIS TOOL: Get Detailed Table Structure

PURPOSE: Understand the complete structure of a specific table including columns, data types, 
relationships, and constraints. Essential for writing correct SQL queries.

WHEN TO USE:
- After identifying relevant tables with get_tables()
- Before writing any SQL queries involving a table
- User asks about specific table structure or column details
- Need to understand relationships between tables

Our financial data model includes:
- unifiedreport: Contains report metadata, periods, currency, calculated fields like gross_profit
- account: Chart of accounts with name, group (Revenue, Expenses, etc.), hierarchical parent_id
- financialentry: Individual financial values with date and amount
    
PARAMETERS:
- table (REQUIRED): Exact table name from the database (case-sensitive)

USAGE PATTERN:
1. Get table name from get_tables() or filter_table_names()
2. Call describe_table() to understand structure
3. Use the column and relationship info to write proper SQL queries

RETURNS: Comprehensive table definition including:
- Column names, data types, sizes, nullable status
- Primary key columns (marked with primary_key: true)
- Foreign key relationships with referenced tables
- Default values and constraints

CRITICAL: Use exact table names. If unsure, use filter_table_names() first.

NEXT STEPS: Use the structure info to write SQL queries with execute_query()
    """,
)
def describe_table(table: str) -> str:
    """
    Retrieve and return a dictionary containing the definition of a table in the financial database.

    Args:
        table: The name of the table to retrieve the definition for

    Returns:
        str: JSON string containing the table definition
    """
    try:
        # Use our database inspector to get detailed table information
        tables_info = db_inspector.get_tables_info()
        
        if table not in tables_info:
            return json.dumps(
                {"error": f"Table {table} not found in financial database"}, indent=2
            )

        # Get the table information from our inspector
        table_info = tables_info[table]
        
        # Format it similar to the original structure but with our data
        formatted_info = {
            "TABLE_CAT": "financial_db",
            "TABLE_SCHEM": "public", 
            "TABLE_NAME": table,
            "columns": table_info["columns"],
            "relationships": table_info["relationships"]
        }
        
        return json.dumps(formatted_info, indent=2)

    except Exception as e:
        logger.error(f"Error retrieving table definition: {e}")
        raise


def fuzzy_match(query: str, table_name: str) -> bool:
    """
    Check if the query matches the table name using fuzzy matching.
    """
    return fuzz.partial_ratio(query, table_name) > 80


@mcp.tool(
    name="filter_table_names",
    description="""🔎 TABLE DISCOVERY TOOL: Find Tables by Name Pattern

PURPOSE: Locate tables when you know part of the table name or need to find related tables.
Uses fuzzy matching to handle partial names and typos.

WHEN TO USE:
- User mentions a concept but you're unsure of exact table names
- Looking for related tables (e.g., all tables related to "report")
- User has typos in table names
- Exploring domain-specific tables

Our financial tables include:
- report, unified, account, financial - for financial data
- entry, value - for transaction data
    
PARAMETERS:
- query (REQUIRED): Substring or partial name to search for in table names

USAGE PATTERN:
1. Extract key concepts from user's question
2. Search for tables related to those concepts
3. Use describe_table() on found tables for detailed structure

SEARCH EXAMPLES:
- filter_table_names(query="report") → Find: unifiedreport
- filter_table_names(query="account") → Find: account 
- filter_table_names(query="financial") → Find: financialentry
- filter_table_names(query="entry") → Find: financialentry

FUZZY MATCHING: Uses 80% similarity threshold, so "reprot" will find "report"

RETURNS: JSON list of matching tables with catalog, schema, and table names

NEXT STEPS: Use describe_table() on found tables to understand their structure
    """,
)
def filter_table_names(query: str) -> str:
    """
    Retrieve and return a list containing information about tables whose names contain the substring.

    Args:
        query: The substring to filter table names by

    Returns:
        str: JSON string containing filtered table information
    """
    try:
        # Get all tables using our inspector
        tables_info = db_inspector.get_tables_info()
        
        results = []
        for table_name in tables_info.keys():
            if fuzzy_match(query, table_name):
                results.append({
                    "TABLE_CAT": "financial_db",
                    "TABLE_SCHEM": "public",
                    "TABLE_NAME": table_name,
                })
        
        logger.info(f"Results of fuzzy_match for '{query}': {results}")
        return json.dumps(results, indent=2)
    except Exception as e:
        logger.error(f"Error filtering table names: {e}")
        raise


@mcp.tool(
    name="execute_query",
    description="""📊 PRIMARY QUERY TOOL: Execute SQL and Get Formatted Results

PURPOSE: Execute SQL queries and return results in a beautiful, readable Markdown table format.
This is your main tool for answering user questions with financial data.

WHEN TO USE:
- Answering user questions that require data from the database
- Creating financial reports, summaries, or analysis
- When you want nicely formatted output for presentation
- Exploring data with limited result sets
    
PARAMETERS:
- query (REQUIRED): Valid SQL SELECT statement
- max_rows (OPTIONAL): Maximum rows to return (default: 100, prevents overwhelming output)
- params (OPTIONAL): Dictionary of parameters for parameterized queries (security best practice)

SQL BEST PRACTICES:
- Always use LIMIT for exploration queries
- Use meaningful column aliases for better readability
- Join tables properly using foreign key relationships
- Use WHERE clauses to filter relevant data
- Use ORDER BY for consistent, meaningful sorting

COMMON FINANCIAL QUERY PATTERNS:

📈 SUMMARY QUERIES:
- execute_query("SELECT report_basis, COUNT(*) as count FROM unifiedreport GROUP BY report_basis ORDER BY count DESC")
- execute_query("SELECT currency, COUNT(*) as report_count FROM unifiedreport WHERE currency IS NOT NULL GROUP BY currency ORDER BY report_count DESC LIMIT 10")

� FINANCIAL ANALYSIS:
- execute_query("SELECT report_name, gross_profit, operating_profit, net_profit FROM unifiedreport WHERE net_profit IS NOT NULL ORDER BY net_profit DESC LIMIT 10")
- execute_query("SELECT a.name, a.group, fe.value FROM account a JOIN financialentry fe ON a.id = fe.account_id WHERE a.group = 'Revenue' ORDER BY fe.value DESC LIMIT 20")

🔍 ACCOUNT HIERARCHY:
- execute_query("SELECT a.name as account, p.name as parent_account, a.group FROM account a LEFT JOIN account p ON a.parent_id = p.id ORDER BY a.group, a.name LIMIT 20")
- execute_query("SELECT group, COUNT(*) as account_count FROM account GROUP BY group ORDER BY account_count DESC")

� TIME-BASED ANALYSIS:
- execute_query("SELECT DATE_TRUNC('month', start_period) as month, COUNT(*) as reports FROM unifiedreport GROUP BY month ORDER BY month DESC LIMIT 12")
- execute_query("SELECT DATE_TRUNC('quarter', fe.date) as quarter, SUM(fe.value) as total_value FROM financialentry fe GROUP BY quarter ORDER BY quarter DESC")

RETURNS: Markdown table with column headers and formatted data rows

SECURITY: Always use parameterized queries for user input to prevent SQL injection

NEXT STEPS: Use query_database() if you need all results without row limits
    """,
)
def execute_query(
    query: str,
    max_rows: int = DEFAULT_MAX_ROWS,
    params: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Execute a SQL query and return results in Markdown table format.

    Args:
        query: The SQL query to execute
        max_rows: Maximum number of rows to return
        params: Optional dictionary of parameters to pass to the query

    Returns:
        str: Results in Markdown table format
    """
    try:
        logger.info(f"Executing query: {query}")

        with get_connection() as session:
            from sqlalchemy import text

            # Execute the query using SQLAlchemy
            if params:
                result = session.execute(text(query), params)
            else:
                result = session.execute(text(query))

            # Check if this is a SELECT query (has results)
            if result.returns_rows:
                columns = list(result.keys())
                results = []

                for row in result:
                    row_dict = dict(zip(columns, row))
                    # Truncate long string values
                    truncated_row = {
                        key: (str(value)[:MAX_LONG_DATA] if value is not None else None)
                        for key, value in row_dict.items()
                    }
                    results.append(truncated_row)

                    if len(results) >= max_rows:
                        break

                # Create the Markdown table header
                md_table = "| " + " | ".join(columns) + " |\n"
                md_table += "| " + " | ".join(["---"] * len(columns)) + " |\n"

                # Add rows to the Markdown table
                for row in results:
                    md_table += (
                        "| " + " | ".join(str(row[col]) for col in columns) + " |\n"
                    )

                return md_table
            else:
                # For non-SELECT queries (INSERT, UPDATE, DELETE)
                return f"**Query executed successfully**\n\nQuery: {query}"

    except Exception as e:
        logger.error(f"Error executing query: {e}")
        raise


@mcp.tool(
    name="query_database",
    description="""⚡ BULK DATA TOOL: Execute SQL and Get All Results

PURPOSE: Execute SQL queries and return ALL results without row limits. 
Use with caution as this can return large amounts of data.

WHEN TO USE:
- Need complete datasets for analysis
- Exporting data or creating comprehensive reports
- User specifically asks for "all" results
- Working with known small result sets

⚠️ IMPORTANT WARNINGS:
- NO ROW LIMIT: This returns ALL matching rows
- Can be slow and memory-intensive for large tables
- Use execute_query() with LIMIT for exploration first
- Consider the impact on system performance
    
    PARAMETERS:
- query (REQUIRED): Valid SQL SELECT statement

RECOMMENDED USAGE PATTERN:
1. First explore with execute_query() using LIMIT
2. Confirm the result size is reasonable
3. Use query_database() only when you need all results

SAFE QUERY EXAMPLES:
- query_database("SELECT DISTINCT location FROM job") → Get all unique locations
- query_database("SELECT * FROM company") → Get all companies (usually small table)
- query_database("SELECT status, COUNT(*) FROM application GROUP BY status") → Aggregated data

AVOID FOR LARGE TABLES:
- query_database("SELECT * FROM candidate") → Could return thousands of rows
- query_database("SELECT * FROM application") → Could return millions of rows

RETURNS: Markdown table with ALL matching results

ALTERNATIVE: Use execute_query() with appropriate LIMIT for safer exploration
    """,
)
def query_database(query: str) -> str:
    """
    Execute a SQL query and return all results in Markdown table format.

    Args:
        query: The SQL query to execute
    Returns:
        str: All results in Markdown table format
    """
    try:
        logger.info(f"Executing query (no row limit): {query}")

        with get_connection() as session:
            from sqlalchemy import text

            # Execute the query using SQLAlchemy
            result = session.execute(text(query))

            # Check if this is a SELECT query (has results)
            if result.returns_rows:
                columns = list(result.keys())
                results = []

                for row in result:
                    row_dict = dict(zip(columns, row))
                    # Truncate long string values
                    truncated_row = {
                        key: (str(value)[:MAX_LONG_DATA] if value is not None else None)
                        for key, value in row_dict.items()
                    }
                    results.append(truncated_row)

                # Create the Markdown table header
                md_table = "| " + " | ".join(columns) + " |\n"
                md_table += "| " + " | ".join(["---"] * len(columns)) + " |\n"

                # Add rows to the Markdown table
                for row in results:
                    md_table += (
                        "| " + " | ".join(str(row[col]) for col in columns) + " |\n"
                    )

                return md_table
            else:
                # For non-SELECT queries (INSERT, UPDATE, DELETE)
                return json.dumps(
                    {
                        "message": "Query executed successfully",
                        "query": query,
                    }
                )

    except Exception as e:
        logger.error(f"Error executing query: {e}")
        raise


@mcp.tool(
    name="fuzzy_search_table",
    description="""🔍 SMART SEARCH TOOL: Find Records with Fuzzy Matching

PURPOSE: Search for records when exact spelling is uncertain. Handles typos, variations,
and partial matches using PostgreSQL's trigram similarity.

WHEN TO USE:
- User provides names with potential typos ("Acounting" instead of "Accounting")
- Searching for partial report names or account names
- User remembers only part of a name or title
- Need to find similar entries when exact match fails

⚠️ REQUIREMENT: Requires pg_trgm extension in PostgreSQL database
    
PARAMETERS:
- table (REQUIRED): Table name to search in (e.g., 'unifiedreport', 'account', 'financialentry')
- column (REQUIRED): Column name to search (e.g., 'report_name', 'name', 'group')
- query (REQUIRED): Search term (can have typos or be partial)
- limit (OPTIONAL): Max results to return (default: 5, keeps results manageable)
- min_similarity (OPTIONAL): Similarity threshold 0.0-1.0 (default: 0.3, lower = more permissive)

SEARCH EXAMPLES:

� REPORT SEARCHES:
- fuzzy_search_table(table="unifiedreport", column="report_name", query="Quarterly Report") → Finds "Q1 Quarterly Report"
- fuzzy_search_table(table="unifiedreport", column="report_basis", query="cash") → Finds "Cash Basis"

� ACCOUNT SEARCHES:
- fuzzy_search_table(table="account", column="name", query="sales revenue") → Finds "Sales Revenue", "Total Sales Revenue"
- fuzzy_search_table(table="account", column="group", query="expense") → Finds "Operating Expense", "General Expense"

🏢 PLATFORM SEARCHES:
- fuzzy_search_table(table="unifiedreport", column="platform_id", query="quickbooks") → Finds "qbo", "quickbooks_online"

SIMILARITY TUNING:
- min_similarity=0.1 → Very permissive, finds distant matches
- min_similarity=0.3 → Balanced (default)
- min_similarity=0.7 → Strict, only close matches

RETURNS: JSON list of matching records ordered by similarity score (highest first)

NEXT STEPS: Use the found IDs in subsequent queries with execute_query()
    """,
)
def fuzzy_search_table(
    table: str, column: str, query: str, limit: int = 5, min_similarity: float = 0.3
) -> str:
    """
    Performs a fuzzy search on a table column using trigram similarity.
    """

    # We use f-strings for table and column names, but validate them against the schema first to prevent injection.
    sql_query = f"""
        SELECT *, similarity("{column}", :query_param) AS similarity
        FROM "{table}"
        WHERE similarity("{column}", :query_param) > :min_similarity
        ORDER BY similarity DESC
        LIMIT :limit_param
    """
    params = {
        "query_param": query,
        "min_similarity": min_similarity,
        "limit_param": limit,
    }

    try:
        with get_connection() as session:
            from sqlalchemy import text

            # Validate table exists
            table_exists_query = text("""
                SELECT COUNT(*) 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = :table_name
            """)

            result = session.execute(table_exists_query, {"table_name": table})
            if result.scalar() == 0:
                return json.dumps({"error": f"Table '{table}' not found in database."})

            # Validate column exists
            column_exists_query = text("""
                SELECT COUNT(*) 
                FROM information_schema.columns 
                WHERE table_schema = 'public' 
                AND table_name = :table_name 
                AND column_name = :column_name
            """)

            result = session.execute(
                column_exists_query, {"table_name": table, "column_name": column}
            )
            if result.scalar() == 0:
                return json.dumps(
                    {"error": f"Column '{column}' not found in table '{table}'."}
                )

            # Check if pg_trgm is enabled by trying a simple query
            try:
                session.execute(text("SELECT similarity('test', 'test')"))
            except Exception:
                return json.dumps(
                    {
                        "error": "The 'pg_trgm' extension is not enabled in the database. Fuzzy search is not available."
                    }
                )

            # Execute the fuzzy search query
            result = session.execute(text(sql_query), params)

            if not result.returns_rows:
                return json.dumps({"message": "No fuzzy matches found.", "results": []})

            columns = list(result.keys())
            results = []

            for row in result:
                row_dict = dict(zip(columns, row))
                # Truncate long string values
                truncated_row = {
                    key: (str(value)[:MAX_LONG_DATA] if value is not None else None)
                    for key, value in row_dict.items()
                }
                results.append(truncated_row)

            jsonl_results = "\n".join(json.dumps(row) for row in results)
            return jsonl_results

    except Exception as e:
        logger.error(f"Error executing fuzzy search query: {e}")
        raise


# Helper functions - removed old pyodbc functions, using SQLAlchemy with our db inspector


if __name__ == "__main__":
    logger.info("Starting Financial Reports MCP server...")
    mcp.run()
# Entry point for running the server locally with Uvicorn.
# Create a Starlette application that mounts the MCP SSE app.
# This allows the MCP server to use SSE for streaming responses.
# from mcp.server.fastmcp import FastMCP
# from starlette.applications import Starlette
# from starlette.routing import Mount
# import os

# app = Starlette(
#     routes=[
#         Mount("/", app=mcp.sse_app()),
#     ]
# )

# if __name__ == "__main__":
#     import uvicorn
#     uvicorn.run(app, host="0.0.0.0", port=8306)
