import os
import sys

sys.path.append(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)
from core.database import get_session_rls
import logging
from typing import Any, Dict, Optional
import json
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP
from rapidfuzz import fuzz

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


# Global variable to store the employer_id filter
EMPLOYER_ID_FILTER: Optional[int] = None


def get_connection():
    """
    Create a database session using SQLAlchemy with RLS (Row Level Security).

    The session automatically filters data based on the employer_id through RLS policies.
    This replaces the manual employer filtering logic.

    Returns:
        SQLAlchemy Session: Database session object with RLS enabled

    Raises:
        ValueError: If required credentials are missing
        Exception: If session creation fails
    """
    logger.info(f"Getting connection with EMPLOYER_ID_FILTER: {os.getcwd()}")

    if EMPLOYER_ID_FILTER is None:
        raise ValueError("EMPLOYER_ID_FILTER must be set before creating a session")

    logger.info(
        f"Creating SQLAlchemy session with RLS for employer_id: {EMPLOYER_ID_FILTER}"
    )

    try:
        # Return the context manager directly - it will be used in a 'with' statement
        return get_session_rls(EMPLOYER_ID_FILTER)
    except Exception as e:
        logger.error(f"Failed to create database session: {e}")
        raise


def set_employer_id_filter(employer_id: int) -> None:
    """Set the global employer_id filter for all database queries."""
    global EMPLOYER_ID_FILTER
    EMPLOYER_ID_FILTER = employer_id
    logger.info(f"Employer ID filter set to: {employer_id}")


# MCP Server initialization
mcp = FastMCP("mcp-sqlalchemy-server")


@mcp.tool(
    name="get_tables",
    description="""🔍 DISCOVERY TOOL: Explore Database Schema

PURPOSE: Get a complete overview of all available tables in the job matching database.
This is your starting point for database exploration and should be used first.

WHEN TO USE:
- Beginning any database exploration session
- User asks "what data is available?" or "show me the database structure"
- Need to understand the overall schema before diving into specific queries

USAGE PATTERN:
1. Call this tool first to see all available tables
2. Identify relevant tables for the user's question
3. Use describe_table() on specific tables for detailed structure

RETURNS: JSON list of all tables with catalog, schema, and table names

EXAMPLE OUTPUT:
[
  {"TABLE_CAT": "matching_db", "TABLE_SCHEM": "public", "TABLE_NAME": "company"},
  {"TABLE_CAT": "matching_db", "TABLE_SCHEM": "public", "TABLE_NAME": "job"},
  {"TABLE_CAT": "matching_db", "TABLE_SCHEM": "public", "TABLE_NAME": "candidate"}
]

NEXT STEPS: Use describe_table(table="table_name") for detailed table structure
    """,
)
def get_tables() -> str:
    """
    Retrieve and return a list containing information about all tables in matching_db.

    Returns:
        str: JSON string containing table information
    """
    try:
        with get_connection() as session:
            from sqlalchemy import text

            # Query to get all tables in the public schema
            query = text("""
                SELECT table_catalog, table_schema, table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_type = 'BASE TABLE'
                ORDER BY table_name
            """)

            result = session.execute(query)
            results = []
            for row in result:
                results.append(
                    {"TABLE_CAT": row[0], "TABLE_SCHEM": row[1], "TABLE_NAME": row[2]}
                )

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

EXAMPLE USAGE:
- describe_table(table="job") → Get job table structure
- describe_table(table="candidate") → Get candidate table structure

CRITICAL: Use exact table names. If unsure, use filter_table_names() first.

NEXT STEPS: Use the structure info to write SQL queries with execute_query()
    """,
)
def describe_table(table: str) -> str:
    """
    Retrieve and return a dictionary containing the definition of a table in matching_db.

    Args:
        table: The name of the table to retrieve the definition for

    Returns:
        str: JSON string containing the table definition
    """
    try:
        with get_connection() as session:
            from sqlalchemy import text

            # Check if table exists
            table_exists_query = text("""
                SELECT COUNT(*) 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = :table_name
            """)

            result = session.execute(table_exists_query, {"table_name": table})
            if result.scalar() == 0:
                return json.dumps(
                    {"error": f"Table {table} not found in matching_db"}, indent=2
                )

            # Get table definition using SQLAlchemy inspection
            table_definition = _get_table_info_sqlalchemy(session, table)
            return json.dumps(table_definition, indent=2)

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
- Looking for related tables (e.g., all tables related to "job")
- User has typos in table names
- Exploring domain-specific tables
    
    PARAMETERS:
- query (REQUIRED): Substring or partial name to search for in table names

USAGE PATTERN:
1. Extract key concepts from user's question
2. Search for tables related to those concepts
3. Use describe_table() on found tables for detailed structure

SEARCH EXAMPLES:
- filter_table_names(query="candidate") → Find: candidate, candidate_skills, etc.
- filter_table_names(query="job") → Find: job, job_application, job_match, etc.
- filter_table_names(query="application") → Find: application, job_application, etc.
- filter_table_names(query="company") → Find: company, company_profile, etc.
- filter_table_names(query="match") → Find: match, job_match, skill_match, etc.

FUZZY MATCHING: Uses 80% similarity threshold, so "aplications" will find "applications"

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
        with get_connection() as session:
            from sqlalchemy import text

            # Query to get all tables in the public schema
            table_query = text("""
                SELECT table_catalog, table_schema, table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_type = 'BASE TABLE'
                ORDER BY table_name
            """)

            result = session.execute(table_query)
            results = []
            for row in result:
                if fuzzy_match(query, row[2]):
                    results.append(
                        {
                            "TABLE_CAT": row[0],
                            "TABLE_SCHEM": row[1],
                            "TABLE_NAME": row[2],
                        }
                    )
            logger.info(f"Results of fuzzy_match: {results}")
            return json.dumps(results, indent=2)
    except Exception as e:
        logger.error(f"Error filtering table names: {e}")
        raise


@mcp.tool(
    name="execute_query",
    description="""📊 PRIMARY QUERY TOOL: Execute SQL and Get Formatted Results

PURPOSE: Execute SQL queries and return results in a beautiful, readable Markdown table format.
This is your main tool for answering user questions with data.

WHEN TO USE:
- Answering user questions that require data from the database
- Creating reports, summaries, or analysis
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

COMMON QUERY PATTERNS:

📈 SUMMARY QUERIES:
- execute_query("SELECT status, COUNT(*) as count FROM job GROUP BY status ORDER BY count DESC")
- execute_query("SELECT location, COUNT(*) as job_count FROM job WHERE status = 'published' GROUP BY location ORDER BY job_count DESC LIMIT 10")

👥 RELATIONSHIP QUERIES:
- execute_query("SELECT c.full_name, j.title, a.status FROM application a JOIN candidate c ON a.candidate_id = c.id JOIN job j ON a.job_id = j.id LIMIT 10")
- execute_query("SELECT co.name as company, COUNT(j.id) as active_jobs FROM company co JOIN job j ON co.id = j.employer_id WHERE j.status = 'published' GROUP BY co.name ORDER BY active_jobs DESC")

🔍 FILTERED SEARCHES:
- execute_query("SELECT title, location, job_type, experience_level FROM job WHERE status = 'published' AND location ILIKE '%london%' ORDER BY created_at DESC LIMIT 20")
- execute_query("SELECT full_name, email FROM candidate WHERE parsed_resume->>'skills' ILIKE '%python%' LIMIT 15")

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
        # With RLS enabled, we don't need manual employer filtering
        logger.info(f"Executing query with RLS: {query}")

        with get_connection() as session:
            from sqlalchemy import text

            if "company_id" in query:
                query = query.replace("company_id", "employer_id")
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
    Execute a SQL query and return all results in JSONL format.

    Args:
        query: The SQL query to execute
    Returns:
        str: All results in JSONL format
    """
    try:
        # With RLS enabled, we don't need manual employer filtering
        logger.info(f"Executing query with RLS (no row limit): {query}")

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
- User provides names with potential typos ("Jon Doe" instead of "John Doe")
- Searching for partial company names or job titles
- User remembers only part of a name or title
- Need to find similar entries when exact match fails

⚠️ REQUIREMENT: Requires pg_trgm extension in PostgreSQL database
    
    PARAMETERS:
- table (REQUIRED): Table name to search in (e.g., 'candidate', 'job', 'company')
- column (REQUIRED): Column name to search (e.g., 'full_name', 'title', 'name')
- query (REQUIRED): Search term (can have typos or be partial)
- limit (OPTIONAL): Max results to return (default: 5, keeps results manageable)
- min_similarity (OPTIONAL): Similarity threshold 0.0-1.0 (default: 0.3, lower = more permissive)

SEARCH EXAMPLES:

👤 CANDIDATE SEARCHES:
- fuzzy_search_table(table="candidate", column="full_name", query="Jon Doe") → Finds "John Doe"
- fuzzy_search_table(table="candidate", column="email", query="john.smith") → Finds "john.smith@company.com"

💼 JOB SEARCHES:
- fuzzy_search_table(table="job", column="title", query="data scientist") → Finds "Data Scientist", "Senior Data Scientist"
- fuzzy_search_table(table="job", column="location", query="san francisco") → Finds "San Francisco, CA"

🏢 COMPANY SEARCHES:
- fuzzy_search_table(table="company", column="name", query="google") → Finds "Google Inc.", "Google LLC"

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
    # Note: RLS will automatically filter results based on employer_id
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
            # Note: RLS will automatically filter results based on employer_id
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


# Helper functions
def _get_table_info_sqlalchemy(session, table: str) -> Dict[str, Any]:
    """Get comprehensive table information using SQLAlchemy."""
    from sqlalchemy import text

    # Get column information
    columns_query = text("""
        SELECT 
            column_name,
            data_type,
            character_maximum_length,
            is_nullable,
            column_default
        FROM information_schema.columns 
        WHERE table_schema = 'public' 
        AND table_name = :table_name
        ORDER BY ordinal_position
    """)

    result = session.execute(columns_query, {"table_name": table})
    columns = []
    for row in result:
        columns.append(
            {
                "name": row[0],
                "type": row[1],
                "column_size": row[2],
                "nullable": row[3] == "YES",
                "default": row[4],
                "primary_key": False,  # Will be updated below
            }
        )

    # Get primary key information
    pk_query = text("""
        SELECT column_name
        FROM information_schema.table_constraints tc
        JOIN information_schema.key_column_usage kcu 
            ON tc.constraint_name = kcu.constraint_name
        WHERE tc.table_schema = 'public'
        AND tc.table_name = :table_name
        AND tc.constraint_type = 'PRIMARY KEY'
    """)

    result = session.execute(pk_query, {"table_name": table})
    primary_keys = [row[0] for row in result]

    # Update primary key flags in columns
    for column in columns:
        if column["name"] in primary_keys:
            column["primary_key"] = True

    # Get foreign key information
    fk_query = text("""
        SELECT 
            kcu.column_name,
            ccu.table_name AS foreign_table_name,
            ccu.column_name AS foreign_column_name,
            tc.constraint_name
        FROM information_schema.table_constraints AS tc 
        JOIN information_schema.key_column_usage AS kcu
            ON tc.constraint_name = kcu.constraint_name
        JOIN information_schema.constraint_column_usage AS ccu
            ON ccu.constraint_name = tc.constraint_name
        WHERE tc.constraint_type = 'FOREIGN KEY' 
        AND tc.table_schema = 'public'
        AND tc.table_name = :table_name
    """)

    result = session.execute(fk_query, {"table_name": table})
    foreign_keys = []
    for row in result:
        foreign_keys.append(
            {
                "name": row[3],
                "constrained_columns": [row[0]],
                "referred_table": row[1],
                "referred_columns": [row[2]],
            }
        )

    return {
        "TABLE_CAT": "matching_db",
        "TABLE_SCHEM": "public",
        "TABLE_NAME": table,
        "columns": columns,
        "primary_keys": primary_keys,
        "foreign_keys": foreign_keys,
    }


# Old pyodbc helper functions removed - replaced with SQLAlchemy equivalents


def initialize_server_with_args():
    """Initialize the server with command line arguments."""
    import sys

    # Parse command line arguments for employer_id
    if len(sys.argv) > 1:
        try:
            employer_id = int(sys.argv[1])
            set_employer_id_filter(employer_id)
            logger.info(f"Server initialized with employer_id filter: {employer_id}")
        except ValueError:
            logger.error(
                f"Invalid employer_id argument: {sys.argv[1]}. Must be an integer."
            )
            sys.exit(1)
    else:
        logger.warning(
            "No employer_id provided. Server will return data for all employers."
        )


if __name__ == "__main__":
    initialize_server_with_args()
    logger.info("Starting MCP SQLAlchemy server for matching_db...")
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
