import os
os.environ["GOOGLE_API_KEY"] = "AIzaSyAsr9OJhukEP9vKjUd1NI8Rgbd-M5uTkHk" ## for testing
import sys
from typing import List, Dict, Any, Union, AsyncIterable

from pydantic_ai import Agent
from pydantic_ai.mcp import MCPServerStdio
from pydantic_ai.messages import ModelMessage
import logging
from pydantic_ai.exceptions import UserError
# Create logger
logger = logging.getLogger("SimpleLogger")
logger.setLevel(logging.DEBUG)

# Create console handler and set level
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.DEBUG)

# Create formatter
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)-8s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# Add formatter to handler
console_handler.setFormatter(formatter)

# Add handler to logger
logger.addHandler(console_handler)
try:
    # Ensure repo root is importable so we can load db_inspector and db
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    if repo_root not in sys.path:
        sys.path.insert(0, repo_root)
    from db import DATABASE_URL
    from db_inspector import DatabaseInspector
except Exception:
    # If imports fail, we'll fall back to no schema embedding.
    DATABASE_URL = None
    DatabaseInspector = None

class FinancialDataChat:
    """A chat client that interacts with a Pydantic-AI agent for financial data analysis."""

    def __init__(self, model: str = "gemini-2.0-flash"):
        """
        Initializes the financial data chat client.

        Args:
            model: The name of the LLM model to use.
        """
        # Create MCP server for financial data analysis
     
        server_script_path = os.path.join(os.path.dirname(__file__), "server.py")

        try:
            
            args = [server_script_path]
            command="python"
            logger.info(f"command {command}")
            
            # Ensure environment variables are passed to the subprocess
            env = os.environ.copy()
            logger.info(f"Passing DATABASE_URL {env.get('DATABASE_URL')} to subprocess: {bool(env.get('DATABASE_URL'))}")

            server = MCPServerStdio(
                command=command,
                args=args,
                env=env,
                cwd=os.path.dirname(__file__),
            )
            logger.info("Starting MCP server with: %s %s", command, " ".join(args))
        except Exception as e:
            logger.error(f"Failed to start MCP server: {e}")
            raise     

        from datetime import datetime

        # Build the system prompt and, when possible, embed the live DB schema
        schema_text = "(schema unavailable)"
        if DatabaseInspector and DATABASE_URL:
            try:
                inspector = DatabaseInspector(
                    DATABASE_URL,
                    skip_tables=["message", "conversation"],
                    distinct_fields={"financialstatement": ["account_name"]},
                )
                schema_text = inspector.get_schema_text()
            except Exception:
                schema_text = "(failed to fetch schema)"
        print(f"schema text overview: {schema_text}")

        self.system_prompt = f"""You are a specialized financial data analyst. Your primary tool is `query_database`, which allows you to interact with the financial database in three ways: fetching the schema, searching for account names, and executing SQL queries.

Today's date is: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

**DATABASE SCHEMA OVERVIEW:**
{schema_text}

**AGENT WORKFLOW:**

1.  **Understand the User's Goal:** What financial question is the user asking? (e.g., "What was our profit in Q1?", "Show me revenue trends.")

2.  **Identify Necessary Accounts:** Determine which `account_name` values are needed. If you are unsure, use the `query_database` tool with the `search_account_term` parameter to find the correct names.
    *   **Tool Call Example (Searching):** `query_database(search_account_term="profit")`

3.  **Construct the SQL Query:** Once you have the correct account names, write a standard SQL query to retrieve the data.
    *   Use `period` for dates (e.g., `period >= '2024-01-01'`).
    *   Use `amount` for financial values.
    *   Aggregate functions like `SUM()`, `AVG()`, `COUNT()` are fully supported.

4.  **Execute the Query:** Call the `query_database` tool with the `sql_query` parameter.
    *   **Tool Call Example (Querying):** `query_database(sql_query="SELECT SUM(amount) FROM financialstatement WHERE account_name = 'Net Profit'")`

5.  **Analyze and Respond:** Interpret the data returned by the tool. Provide a clear, business-focused answer to the user, including key figures and a brief explanation. Suggest follow-up questions where appropriate.

**RESPONSE GUIDELINES:**
-   Provide clear, business-focused insights with values formatted to two decimal places.
-   When presenting data, explain its meaning and context.
-   Always use the exact `account_name` values from the schema or your search results.
-   Be proactive: suggest next steps or deeper analysis.
"""

        try:
            self.agent = Agent(
                model,
                toolsets=[server],
                system_prompt=self.system_prompt,
            )
        except Exception:
            # If Agent can't be created in this environment, keep system_prompt available
            self.agent = None

        self.message_history: List[ModelMessage] = []
    async def run_interaction(self, prompt: str):
        """
        Sends a prompt to the agent and returns the full result, maintaining conversation history.
    
        Args:
            prompt: The user's input prompt.
    
        Returns:
            The agent's result object containing output, usage, and messages.
        """
        if not self.agent:
            raise RuntimeError("Agent is not available in this environment")
    
        result = await self.agent.run(prompt)
        
        return result