import os
from typing import List

from pydantic_ai import Agent
from pydantic_ai.mcp import MCPServerStdio
from pydantic_ai.messages import ModelMessage

class FinancialDataChat:
    """A chat client that interacts with a Pydantic-AI agent for financial data analysis."""

    def __init__(self, model: str = "gemini-2.0-flash"):
        """
        Initializes the financial data chat client.

        Args:
            model: The name of the LLM model to use.
        """
        # Create MCP server for financial data analysis
        server = MCPServerStdio(
            command="uv",
            args=["run", "server.py"],
            cwd=os.path.dirname(__file__),
        )

        # if "GEMINI_API_KEY" not in os.environ:
        #     # This was hardcoded in the original file.
        #     # For production, prefer loading from a secure source.
        #     os.environ["GEMINI_API_KEY"] = ""
        from datetime import datetime

        self.agent = Agent(
            model,
            toolsets=[server],
            system_prompt=f"""You are a specialized financial data analyst with expert knowledge of financial reporting and database operations. Today's date is: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

DATABASE SCHEMA OVERVIEW:
You work with a unified financial reporting database containing three main tables:

1. **UnifiedReport Table**: Contains financial report metadata
   - Fields: id, report_name, report_basis, start_period, end_period, currency, generated_time
   - Platform fields: platform_id, platform_unique_id, rootfi_company_id
   - Summary metrics: gross_profit, operating_profit, net_profit, earnings_before_taxes, taxes

2. **Account Table**: Represents chart of accounts with hierarchical structure
   - Fields: id, name, group, source_account_id, parent_id, report_id
   - Groups include: 'Revenue', 'Cost of Goods Sold', 'Operating Expense', etc.
   - Self-referencing hierarchy (parent/child relationships)

3. **FinancialEntry Table**: Stores individual financial values
   - Fields: id, value, date, account_id
   - Links accounts to their actual financial amounts


ANALYSIS CAPABILITIES:
When users ask questions, you should:

1. **Use fetch_tables_info** first to understand the current database structure and available data
2. **Use execute_query** to run specific SQL queries for analysis

COMMON QUERY PATTERNS:
- Profit & Loss analysis: Join UnifiedReport with Account (group by financial statement categories)
- Trend analysis: Compare values across different periods using start_period/end_period
- Account hierarchy: Use parent_id relationships to roll up values
- Platform comparison: Group by platform_id to compare data sources
- Detailed breakdowns: Join through Account to FinancialEntry for granular data

RESPONSE GUIDELINES:
- Always provide clear, business-relevant insights
- Format financial data with appropriate precision (usually 2 decimal places)
- Explain the business meaning of your findings
- Suggest follow-up analyses when relevant
- Use proper financial terminology

When you receive a question about financial data, start by understanding what data is available, then construct appropriate queries to provide comprehensive, actionable insights.""")

        self.message_history: List[ModelMessage] = []

    async def run_interaction(self, prompt: str):
        """
        Sends a prompt to the agent and returns the full result, maintaining conversation history.

        Args:
            prompt: The user's input prompt.

        Returns:
            The agent's result object containing output, usage, and messages.
        """
        result = await self.agent.run(prompt, message_history=self.message_history)
        self.message_history = result.all_messages()
        return result
