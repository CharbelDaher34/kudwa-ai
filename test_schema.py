#!/usr/bin/env python3
"""
Test script to validate the FinancialReport schema against the actual JSON data
"""

import json
from data.modvvvels import FinancialReport, LineItem

def test_data_set_2():
    """Test the schema against data_set_2.json"""
    print("🧪 Testing schema against data_set_2.json...")
    
    # Read the JSON file
    with open("AI Engineer x Kudwa Take-Home Test 24a14e124c6780a68e6cdcdeb5442fdf/data_set_2.json", "r") as f:
        data = json.load(f)
    
    # Test the first few records
    test_records = data["data"][:3]  # Test first 3 records
    
    for i, record in enumerate(test_records):
        try:
            # Create FinancialReport instance
            financial_report = FinancialReport(**record)
            print(f"✅ Record {i+1}: Successfully created FinancialReport")
            
            # Test serialization
            serialized = financial_report.model_dump()
            print(f"✅ Record {i+1}: Successfully serialized")
            
            # Test JSON serialization (which is more likely to be used)
            json_data = financial_report.model_dump_json()
            print(f"✅ Record {i+1}: Successfully JSON serialized")
            
            # Test specific line items if they exist using property getters
            revenue_items = financial_report.revenue_items
            if revenue_items:
                print(f"   📊 Revenue items: {len(revenue_items)}")
                for rev_item in revenue_items:
                    print(f"      - {rev_item.name}: {rev_item.value}")
                    if rev_item.line_items:
                        for sub_item in rev_item.line_items:
                            print(f"        └─ {sub_item.name}: {sub_item.value}")
            
            expense_items = financial_report.operating_expenses_items
            if expense_items:
                print(f"   💰 Operating expense items: {len(expense_items)}")
                # Just show first item details to avoid too much output
                first_expense = expense_items[0]
                print(f"      - {first_expense.name}: {first_expense.value}")
                if first_expense.line_items:
                    print(f"        └─ Has {len(first_expense.line_items)} sub-items")
            
            print(f"   💵 Gross Profit: {financial_report.gross_profit}")
            print(f"   📈 Net Profit: {financial_report.net_profit}")
            print()
            
        except Exception as e:
            print(f"❌ Record {i+1}: Failed - {e}")
            print(f"   Record data keys: {list(record.keys())}")
            return False
    
    return True

def test_line_item_validation():
    """Test LineItem validation specifically"""
    print("🧪 Testing LineItem validation...")
    
    # Test with integer value
    try:
        item1 = LineItem(name="Test Item", value=1000)  # integer
        print(f"✅ Integer value: {item1.value} (type: {type(item1.value)})")
    except Exception as e:
        print(f"❌ Integer value failed: {e}")
        return False
    
    # Test with float value
    try:
        item2 = LineItem(name="Test Item", value=1000.50)  # float
        print(f"✅ Float value: {item2.value} (type: {type(item2.value)})")
    except Exception as e:
        print(f"❌ Float value failed: {e}")
        return False
    
    # Test with nested line items
    try:
        nested_item = LineItem(
            name="Parent Item",
            value=5000.0,
            line_items=[
                LineItem(name="Child 1", value=2000),
                LineItem(name="Child 2", value=3000.50, account_id="123")
            ]
        )
        print(f"✅ Nested items: {len(nested_item.line_items)} children")
        print(f"   └─ Child values: {[child.value for child in nested_item.line_items]}")
    except Exception as e:
        print(f"❌ Nested items failed: {e}")
        return False
    
    return True

if __name__ == "__main__":
    print("🚀 Starting schema validation tests...\n")
    
    # Test LineItem validation first
    if not test_line_item_validation():
        print("❌ LineItem validation tests failed")
        exit(1)
    
    print("\n" + "="*50 + "\n")
    
    # Test against actual data
    if not test_data_set_2():
        print("❌ Data validation tests failed")
        exit(1)
    
    print("🎉 All tests passed! The schema is working correctly with the JSON data.")
