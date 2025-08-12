#!/usr/bin/env python3
"""
Demo script showing the enhanced financial MCP server tools in action.

This demonstrates the core functionality without requiring pydantic-ai dependencies.
"""

import os
import sys
import json

# Add the tomato directory to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'tomato'))

def demo_table_discovery():
    """Demonstrate table discovery functionality."""
    print("🔍 Table Discovery Demo")
    print("-" * 30)
    
    import server
    
    # Test get_tables tool
    print("1. Getting all tables:")
    tables_result = server.get_tables()
    tables = json.loads(tables_result)
    
    for table in tables:
        print(f"   📋 {table['TABLE_NAME']}")
    
    print(f"\nFound {len(tables)} tables in database")
    
    # Test filter_table_names tool
    print("\n2. Filtering tables by 'report':")
    filtered_result = server.filter_table_names("report")
    filtered_tables = json.loads(filtered_result)
    
    for table in filtered_tables:
        print(f"   📋 {table['TABLE_NAME']}")
    
    return tables


def demo_table_structure():
    """Demonstrate table structure analysis."""
    print("\n🏗️  Table Structure Demo")
    print("-" * 30)
    
    import server
    
    # Describe the main tables
    main_tables = ["unifiedreport", "account", "financialentry"]
    
    for table_name in main_tables:
        print(f"\n📊 Structure of '{table_name}':")
        
        try:
            structure_result = server.describe_table(table_name)
            structure = json.loads(structure_result)
            
            if "error" in structure:
                print(f"   ❌ {structure['error']}")
                continue
                
            print(f"   Columns: {len(structure['columns'])}")
            print("   Key columns:")
            
            for col in structure['columns'][:5]:  # Show first 5 columns
                nullable = "NULL" if col['nullable'] else "NOT NULL"
                desc = f" - {col.get('description', '')}" if col.get('description') else ""
                print(f"     • {col['name']} ({col['type']}, {nullable}){desc}")
            
            if len(structure['columns']) > 5:
                print(f"     ... and {len(structure['columns']) - 5} more columns")
                
            if structure['relationships']:
                print(f"   Relationships: {len(structure['relationships'])}")
                for rel in structure['relationships']:
                    print(f"     🔗 {rel['from']} → {rel['to']}")
        
        except Exception as e:
            print(f"   ❌ Error: {e}")


def demo_financial_queries():
    """Demonstrate financial data queries."""
    print("\n💰 Financial Data Queries Demo")
    print("-" * 35)
    
    import server
    
    # Sample financial queries
    queries = [
        ("Count of reports by basis", 
         "SELECT report_basis, COUNT(*) as count FROM unifiedreport GROUP BY report_basis ORDER BY count DESC"),
        
        ("Available currencies", 
         "SELECT DISTINCT currency FROM unifiedreport WHERE currency IS NOT NULL ORDER BY currency"),
        
        ("Account groups summary", 
         "SELECT \"group\", COUNT(*) as account_count FROM account GROUP BY \"group\" ORDER BY account_count DESC"),
        
        ("Recent reports", 
         "SELECT report_name, report_basis, start_period, end_period FROM unifiedreport ORDER BY generated_time DESC LIMIT 5"),
        
        ("Top revenue accounts", 
         "SELECT name, \"group\" FROM account WHERE \"group\" LIKE '%Revenue%' LIMIT 10"),
    ]
    
    for query_name, sql_query in queries:
        print(f"\n📊 {query_name}:")
        
        try:
            result = server.execute_query(sql_query, max_rows=10)
            print(result)
            
        except Exception as e:
            print(f"   ❌ Error executing query: {e}")


def demo_fuzzy_search():
    """Demonstrate fuzzy search functionality."""
    print("\n🔍 Fuzzy Search Demo") 
    print("-" * 25)
    
    import server
    
    # Test fuzzy search on different tables
    search_tests = [
        ("unifiedreport", "report_name", "quarterly"),
        ("account", "name", "revenue"),
        ("account", "group", "expense"),
    ]
    
    for table, column, search_term in search_tests:
        print(f"\n🔎 Searching {table}.{column} for '{search_term}':")
        
        try:
            result = server.fuzzy_search_table(
                table=table, 
                column=column, 
                query=search_term,
                limit=3
            )
            
            if result.startswith('{"error"'):
                error_data = json.loads(result)
                print(f"   ⚠️  {error_data['error']}")
            else:
                # Parse JSONL results
                lines = result.strip().split('\n')
                if lines and lines[0]:
                    print(f"   Found {len(lines)} matches:")
                    for line in lines:
                        if line.strip():
                            match_data = json.loads(line)
                            similarity = match_data.get('similarity', 'N/A')
                            value = match_data.get(column, 'N/A')
                            print(f"     • {value} (similarity: {similarity})")
                else:
                    print("   No matches found")
                    
        except Exception as e:
            print(f"   ❌ Error: {e}")


def main():
    """Run the financial MCP demo."""
    print("🏦 Enhanced Financial MCP Server Demo")
    print("=" * 45)
    
    try:
        # Run all demos
        demo_table_discovery()
        demo_table_structure()  
        demo_financial_queries()
        demo_fuzzy_search()
        
        print("\n" + "=" * 45)
        print("🎉 Demo completed successfully!")
        print("\nThe enhanced MCP server provides:")
        print("✅ Financial database schema discovery")
        print("✅ Detailed table structure analysis")
        print("✅ SQL query execution with formatting")
        print("✅ Fuzzy search capabilities")
        print("✅ Integration with your unified financial data model")
        
        print("\nNext steps:")
        print("📝 Install pydantic-ai to use the full chat interface")
        print("🔧 Customize the system prompts for your specific use case")
        print("📊 Add more financial analysis tools as needed")
        
    except Exception as e:
        print(f"❌ Demo failed: {e}")
        return False
        
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
