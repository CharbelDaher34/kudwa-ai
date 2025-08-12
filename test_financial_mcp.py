#!/usr/bin/env python3
"""
Test script for the enhanced financial MCP server components.

This script tests the database connection, inspector, and data models
without requiring the full MCP/pydantic-ai setup.
"""

import os
import sys
import json

# Add current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_database_connection():
    """Test basic database connection and session creation."""
    print("🔌 Testing database connection...")
    
    try:
        from db import get_db_session, DATABASE_URL
        print(f"✅ Database URL configured: {DATABASE_URL}")
        
        # Test session creation
        with get_db_session() as session:
            from sqlalchemy import text
            result = session.execute(text("SELECT 1"))
            if result.scalar() == 1:
                print("✅ Database connection successful")
                return True
            else:
                print("❌ Database connection failed")
                return False
                
    except Exception as e:
        print(f"❌ Database connection error: {e}")
        return False


def test_database_inspector():
    """Test the database inspector functionality."""
    print("\n🔍 Testing database inspector...")
    
    try:
        from db_inspector import DatabaseInspector
        from db import DATABASE_URL
        
        inspector = DatabaseInspector(DATABASE_URL)
        
        # Get tables info
        tables_info = inspector.get_tables_info()
        print(f"✅ Found {len(tables_info)} tables in database")
        
        # Print table names
        if tables_info:
            print("📋 Available tables:")
            for table_name in tables_info.keys():
                print(f"  - {table_name}")
                
            # Test detailed info for first table
            first_table = list(tables_info.keys())[0]
            table_details = tables_info[first_table]
            print(f"📊 Sample table structure for '{first_table}':")
            print(f"  Columns: {len(table_details['columns'])}")
            print(f"  Relationships: {len(table_details['relationships'])}")
        else:
            print("⚠️  No tables found in database")
            
        return True
        
    except Exception as e:
        print(f"❌ Database inspector error: {e}")
        return False


def test_data_models():
    """Test the SQLModel data models."""
    print("\n📊 Testing data models...")
    
    try:
        from data.models import UnifiedReport, Account, FinancialEntry
        print("✅ UnifiedReport model imported successfully")
        print("✅ Account model imported successfully") 
        print("✅ FinancialEntry model imported successfully")
        
        # Test model structure
        print("📋 UnifiedReport fields:")
        for field_name, field_info in UnifiedReport.model_fields.items():
            print(f"  - {field_name}: {field_info.annotation}")
            
        return True
        
    except Exception as e:
        print(f"❌ Data models error: {e}")
        return False


def test_mcp_server_tools():
    """Test MCP server tool functions (without running the full server)."""
    print("\n🛠️  Testing MCP server components...")
    
    try:
        # Import and test get_connection function
        sys.path.append(os.path.join(os.path.dirname(__file__), 'tomato'))
        
        # Test if we can import the server module
        import server
        print("✅ MCP server module imported successfully")
        
        # Test database connection function
        with server.get_connection() as session:
            print("✅ MCP server database connection works")
            
        # Test database inspector in server
        if hasattr(server, 'db_inspector'):
            tables = server.db_inspector.get_tables_info()
            print(f"✅ MCP server database inspector found {len(tables)} tables")
        
        return True
        
    except Exception as e:
        print(f"❌ MCP server components error: {e}")
        return False


def main():
    """Run all tests."""
    print("🧪 Financial MCP Server Enhancement Tests")
    print("=" * 50)
    
    tests = [
        ("Database Connection", test_database_connection),
        ("Database Inspector", test_database_inspector), 
        ("Data Models", test_data_models),
        ("MCP Server Components", test_mcp_server_tools),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n🔍 Running {test_name} test...")
        try:
            success = test_func()
            results.append((test_name, success))
        except Exception as e:
            print(f"❌ {test_name} test failed with exception: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 Test Results Summary:")
    
    passed = 0
    total = len(results)
    
    for test_name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"  {status} - {test_name}")
        if success:
            passed += 1
    
    print(f"\n🎯 Overall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Your enhanced MCP setup is ready to use.")
    else:
        print("⚠️  Some tests failed. Please check the error messages above.")
        
    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
