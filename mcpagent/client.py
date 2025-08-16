import os
import sys
from typing import List, Optional

from pydantic_ai import Agent
from pydantic_ai.mcp import MCPServerStdio
from pydantic_ai.messages import ModelMessage
import logging
import asyncio
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
    """Chat client wrapper; supports reuse and automatic retry if MCP subprocess dies."""

    def __init__(self, model: str = "gemini-2.0-flash"):
        self.model_name = model
        self._init_agent()

    def _build_system_prompt(self) -> str:
        from datetime import datetime
        schema_text = "(schema disabled)" if os.getenv("DISABLE_DB") else "(schema unavailable)"
        if not os.getenv("DISABLE_DB") and DatabaseInspector and DATABASE_URL:
            try:
                inspector = DatabaseInspector(
                    DATABASE_URL,
                    skip_tables=["message", "conversation"],
                    distinct_fields={"financialstatement": ["account_name"]},
                )
                schema_text = inspector.get_schema_text()
            except Exception as e:
                logger.warning("Schema fetch failed: %s", e)
                schema_text = "(failed to fetch schema)"
        return f"You are a specialized financial data analyst. Today's date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\nSCHEMA OVERVIEW:\n{schema_text}\n"

    def _init_agent(self):
        server_script_path = os.path.join(os.path.dirname(__file__), "server.py")
        args = [server_script_path]
        command = os.getenv("PYTHON_CMD", "python")
        env = os.environ.copy()
        logger.info("Launching MCP server: %s %s", command, " ".join(args))
        server = MCPServerStdio(command=command, args=args, env=env, cwd=os.path.dirname(__file__))
        system_prompt = self._build_system_prompt()
        self.agent = Agent(self.model_name, toolsets=[server], system_prompt=system_prompt)

    async def run_interaction(self, prompt: str, retries: int = 1):
        if not self.agent:
            raise RuntimeError("Agent not initialized")
        attempt = 0
        while True:
            try:
                return await self.agent.run(prompt)
            except Exception as e:
                if attempt >= retries:
                    raise
                logger.warning("Agent run failed (%s); reinitializing and retrying...", e)
                await asyncio.sleep(0.2)
                self._init_agent()
                attempt += 1


_singleton_chat: Optional[FinancialDataChat] = None


def get_financial_data_chat() -> FinancialDataChat:
    global _singleton_chat
    if _singleton_chat is None:
        _singleton_chat = FinancialDataChat()
    return _singleton_chat