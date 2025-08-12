#!/usr/bin/env python3
"""
Example script showing how to use the enhanced financial MCP client.

This script demonstrates:
1. Setting up the financial data chat client
2. Making queries about financial reports, accounts, and entries
3. Analyzing financial data with natural language

Before running this script, ensure:
1. Database is set up with financial data
2. MCP server dependencies are installed
3. Environment variables are configured (if needed)
"""

import asyncio
import os
import sys

# Add the parent directory to the path to import our modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from tomato.client import FinancialDataChat
except ImportError:
    print("Warning: pydantic_ai not installed. This is a demonstration of the enhanced setup.")
    print("Install with: pip install pydantic-ai")
    sys.exit(1)


async def main():
    """Demonstrate financial data analysis with the enhanced MCP setup."""
    
    print("🏦 Financial Data Analysis Chat Demo")
    print("=" * 50)
    
    # Initialize the financial chat client
    try:
        chat = FinancialDataChat(model="gemini-2.0-flash")
        print("✅ Financial chat client initialized successfully")
    except Exception as e:
        print(f"❌ Error initializing chat client: {e}")
        return
    
    # Example queries to demonstrate the financial capabilities
    example_queries = [
        "What tables are available in our financial database?",
        "Show me the structure of the unifiedreport table",
        "What are the different report types we have?",
        "Show me the revenue accounts from our chart of accounts",
        "What's the total revenue for all reports?",
        "Show me reports with the highest net profit",
        "What are the different currencies in our financial data?",
        "Show me the account hierarchy for expense accounts",
    ]
    
    print("\n🚀 Example Financial Queries:")
    print("-" * 30)
    
    for i, query in enumerate(example_queries, 1):
        print(f"\n{i}. {query}")
        
        try:
            response = await chat.run_interaction(query)
            print(f"📊 Response:\n{response}")
            print("-" * 50)
            
            # Add a small delay between queries
            await asyncio.sleep(1)
            
        except Exception as e:
            print(f"❌ Error processing query: {e}")
            continue
    
    print("\n🎯 Interactive Mode:")
    print("You can now ask questions about your financial data!")
    print("Type 'quit' to exit")
    
    while True:
        try:
            user_query = input("\n💭 Your question: ").strip()
            
            if user_query.lower() in ['quit', 'exit', 'bye']:
                print("👋 Goodbye!")
                break
                
            if not user_query:
                continue
                
            response = await chat.run_interaction(user_query)
            print(f"\n📊 Answer:\n{response}")
            
        except KeyboardInterrupt:
            print("\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"❌ Error: {e}")


if __name__ == "__main__":
    # Run the async main function
    asyncio.run(main())
