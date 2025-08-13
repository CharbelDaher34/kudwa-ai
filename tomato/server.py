import os
import sys
import logging
from typing import Any, Dict, Optional
import json
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
    name="fetch_tables_info",
    description="Get database schema information including table names, columns, and structure."
)
def fetch_tables_info() -> str:
    """
    Fetch comprehensive database schema information.
    
    Returns:
        str: Database schema information in JSON format
    """
    try:
        print("Fetching database schema information...")
        logger.info("Fetching database schema information")
        
        # Get schema summary from database inspector
        schema_info = db_inspector.get_schema_text()
        
        return schema_info
        
    except Exception as e:
        logger.error(f"Error fetching database schema: {e}")
        return json.dumps({
            "error": f"Failed to fetch database schema: {str(e)}"
        })


@mcp.tool(
    name="execute_query",
    description="Execute a SQL query and return results in Markdown table format."
)
def execute_query(query: str) -> str:
    """
    Execute a SQL query and return all results in Markdown table format.

    Args:
        query: The SQL query to execute
        
    Returns:
        str: Query results in Markdown table format or success message
    """
    try:
        logger.info(f"Executing query: {query}")
        print(f"Executing query: {query}")
        with get_connection() as session:
            from sqlalchemy import text

            # Execute the query using SQLAlchemy
            result = session.exec(text(query))

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
        return json.dumps({
            "error": f"Query execution failed: {str(e)}",
            "query": query
        })

if __name__ == "__main__":
    logger.info("Starting Financial Reports MCP server...")
    mcp.run()
