#!/usr/bin/env python3
"""
Query script to demonstrate accessing the ingested financial data
"""

from sqlmodel import SQLModel, Session, select, func
from data.models import (
    FinancialStatement, 
    RevenueItem, 
    CostOfGoodsSoldItem, 
    OperatingExpenseItem, 
    NonOperatingRevenueItem, 
    NonOperatingExpenseItem,
    Report,
    Account,
    FinancialEntry
)
import random
from db import engine, get_db_session
def display_line_items(items, indent="      "):
    """Helper function to display nested line items"""
    for item in items:
        print(f"{indent}- {item.name}: ${item.value:,.2f}")
        if item.account_id:
            print(f"{indent}  Account ID: {item.account_id}")
        
        # Display children if they exist
        if item.children:
            print(f"{indent}  Sub-items:")
            display_line_items(item.children, indent + "    ")

def query_financial_data():
    """Query and display financial data from the database"""

    with get_db_session() as session:
        # Get all financial statements
        statement = select(FinancialStatement)
        statements = session.exec(statement).all()
        
        print(f"📊 Found {len(statements)} financial statements in database\n")
        
        # Show summary of first few statements
        for i, statement in enumerate(statements[:3]):
            print(f"🏢 Financial Statement {i+1}:")
            print(f"   RootFI ID: {statement.rootfi_id}")
            print(f"   Company ID: {statement.rootfi_company_id}")
            print(f"   Period: {statement.period_start} to {statement.period_end}")
            print(f"   Gross Profit: ${statement.gross_profit:,.2f}")
            print(f"   Operating Profit: ${statement.operating_profit:,.2f}")
            print(f"   Net Profit: ${statement.net_profit:,.2f}")
            
            # Display revenue items with nested structure
            if statement.revenue_items:
                print(f"   Revenue Categories: {len(statement.revenue_items)}")
                display_line_items(statement.revenue_items)
            
            # Display cost of goods sold items
            if statement.cost_of_goods_sold_items:
                print(f"   Cost of Goods Sold: {len(statement.cost_of_goods_sold_items)}")
                display_line_items(statement.cost_of_goods_sold_items)
            
            # Display operating expense items
            if statement.operating_expense_items:
                print(f"   Operating Expenses: {len(statement.operating_expense_items)}")
                display_line_items(statement.operating_expense_items[:2])  # Show first 2 for brevity
                if len(statement.operating_expense_items) > 2:
                    print(f"      ... and {len(statement.operating_expense_items) - 2} more")
            
            # Display non-operating revenue
            if statement.non_operating_revenue_items:
                print(f"   Non-Operating Revenue: {len(statement.non_operating_revenue_items)}")
                display_line_items(statement.non_operating_revenue_items)
            
            # Display non-operating expenses
            if statement.non_operating_expense_items:
                print(f"   Non-Operating Expenses: {len(statement.non_operating_expense_items)}")
                display_line_items(statement.non_operating_expense_items[:1])  # Show first 1 for brevity
                if len(statement.non_operating_expense_items) > 1:
                    print(f"      ... and {len(statement.non_operating_expense_items) - 1} more")
            
            print()

def monthly_summary():
    """Show monthly profit summary"""
    
    with get_db_session() as session:
        statement = select(FinancialStatement).order_by(FinancialStatement.period_start)
        statements = session.exec(statement).all()
        
        print("📈 Monthly Financial Summary:")
        print("-" * 70)
        print(f"{'Period':<20} {'Gross Profit':<15} {'Operating Profit':<15} {'Net Profit':<15}")
        print("-" * 70)
        
        total_gross = 0
        total_operating = 0
        total_net = 0
        
        for statement in statements:
            period = f"{statement.period_start} to {statement.period_end}"
            gross = statement.gross_profit or 0
            operating = statement.operating_profit or 0
            net = statement.net_profit or 0
            
            total_gross += gross
            total_operating += operating
            total_net += net
            
            print(f"{period:<20} ${gross:>12,.2f} ${operating:>12,.2f} ${net:>12,.2f}")
        
        print("-" * 70)
        print(f"{'TOTAL':<20} ${total_gross:>12,.2f} ${total_operating:>12,.2f} ${total_net:>12,.2f}")

def get_financial_statement_by_id(rootfi_id: int):
    """
    Get complete financial statement data by RootFI ID including all related items.
    If the specified ID is not found, returns a random financial statement instead.
    
    Args:
        rootfi_id (int): The RootFI ID of the financial statement
        
    Returns:
        FinancialStatement or None: Complete financial statement with all relationships
    """
    with get_db_session() as session:
        # Query with eager loading of all relationships
        statement_query = select(FinancialStatement).where(
            FinancialStatement.rootfi_id == rootfi_id
        )
        
        financial_statement = session.exec(statement_query).first()
        
        if not financial_statement:
            print(f"❌ No financial statement found with RootFI ID: {rootfi_id}")
            print("🎲 Selecting a random financial statement instead...")
            
            # Get a random financial statement
            all_statements = session.exec(select(FinancialStatement)).all()
            if not all_statements:
                print("❌ No financial statements found in database")
                return None
            
            financial_statement = random.choice(all_statements)
            print(f"🎯 Selected random financial statement with RootFI ID: {financial_statement.rootfi_id}")
            
        print(f"📊 Financial Statement (RootFI ID: {financial_statement.rootfi_id})")
        print(f"   Company ID: {financial_statement.rootfi_company_id}")
        print(f"   Platform: {financial_statement.platform_id}")
        print(f"   Period: {financial_statement.period_start} to {financial_statement.period_end}")
        print(f"   Currency: {financial_statement.currency_id}")
        print(f"   Gross Profit: ${financial_statement.gross_profit:,.2f}")
        print(f"   Operating Profit: ${financial_statement.operating_profit:,.2f}")
        print(f"   Net Profit: ${financial_statement.net_profit:,.2f}")
        
        if financial_statement.earnings_before_taxes:
            print(f"   Earnings Before Taxes: ${financial_statement.earnings_before_taxes:,.2f}")
        if financial_statement.taxes:
            print(f"   Taxes: ${financial_statement.taxes:,.2f}")
            
        print(f"   Created: {financial_statement.rootfi_created_at}")
        print(f"   Updated: {financial_statement.rootfi_updated_at}")
        
        # Display all line items with hierarchical structure
        if financial_statement.revenue_items:
            print(f"\n   💰 Revenue Items ({len(financial_statement.revenue_items)}):")
            display_line_items(financial_statement.revenue_items)
            
        if financial_statement.cost_of_goods_sold_items:
            print(f"\n   📦 Cost of Goods Sold ({len(financial_statement.cost_of_goods_sold_items)}):")
            display_line_items(financial_statement.cost_of_goods_sold_items)
            
        if financial_statement.operating_expense_items:
            print(f"\n   💼 Operating Expenses ({len(financial_statement.operating_expense_items)}):")
            display_line_items(financial_statement.operating_expense_items)
            
        if financial_statement.non_operating_revenue_items:
            print(f"\n   📈 Non-Operating Revenue ({len(financial_statement.non_operating_revenue_items)}):")
            display_line_items(financial_statement.non_operating_revenue_items)
            
        if financial_statement.non_operating_expense_items:
            print(f"\n   📉 Non-Operating Expenses ({len(financial_statement.non_operating_expense_items)}):")
            display_line_items(financial_statement.non_operating_expense_items)
            
        return financial_statement

def get_report_by_id(report_id: int):
    """
    Get complete report data by ID including all accounts and financial entries.
    If the specified ID is not found, returns a random report instead.
    
    Args:
        report_id (int): The ID of the report
        
    Returns:
        Report or None: Complete report with all relationships
    """
    with get_db_session() as session:
        # Query the report with its accounts
        report_query = select(Report).where(Report.id == report_id)
        report = session.exec(report_query).first()
        
        if not report:
            print(f"❌ No report found with ID: {report_id}")
            print("🎲 Selecting a random report instead...")
            
            # Get a random report
            all_reports = session.exec(select(Report)).all()
            if not all_reports:
                print("❌ No reports found in database")
                return None
            
            report = random.choice(all_reports)
            print(f"🎯 Selected random report with ID: {report.id}")
            
        print(f"📋 Report (ID: {report.id})")
        print(f"   Name: {report.report_name}")
        print(f"   Basis: {report.report_basis}")
        print(f"   Period: {report.start_period} to {report.end_period}")
        print(f"   Currency: {report.currency}")
        print(f"   Generated: {report.generated_time}")
        
        # Display accounts with hierarchical structure
        if report.accounts:
            print(f"\n   🏦 Accounts ({len(report.accounts)}):")
            
            # Group accounts by their hierarchy (root accounts first)
            root_accounts = [acc for acc in report.accounts if acc.parent_id is None]
            
            def display_account_hierarchy(accounts, indent="      "):
                """Display accounts in hierarchical format"""
                for account in accounts:
                    print(f"{indent}🏷️  {account.name} (QBO ID: {account.qbo_id})")
                    print(f"{indent}   Type: {account.type} | Group: {account.group}")
                    
                    # Display financial entries for this account
                    if account.financial_entries:
                        print(f"{indent}   💹 Financial Entries ({len(account.financial_entries)}):")
                        for entry in account.financial_entries:
                            print(f"{indent}      {entry.date}: ${entry.value:,.2f}")
                    
                    # Display child accounts recursively
                    if account.children:
                        print(f"{indent}   📁 Sub-accounts:")
                        display_account_hierarchy(account.children, indent + "      ")
                    
                    print()  # Empty line between accounts
            
            display_account_hierarchy(root_accounts)
            
            # Show summary statistics
            total_accounts = len(report.accounts)
            total_entries = sum(len(acc.financial_entries) for acc in report.accounts)
            print(f"   📊 Summary: {total_accounts} accounts, {total_entries} financial entries")
            
        return report

if __name__ == "__main__":
    # print("🚀 Querying Financial Data\n")
    # query_financial_data()
    # print("\n" + "="*70 + "\n")
    # monthly_summary()
    
    # Example usage of the new functions:
    # 
    # # Get a specific financial statement by RootFI ID
    # print("\n" + "="*70 + "\n")
    print("📊 Getting Financial Statement by ID:")
    financial_statement = get_financial_statement_by_id(34)  # Replace with actual ID
    # 
    # # Get a specific report by ID  
    print("\n" + "="*70 + "\n")
    print("📋 Getting Report by ID:")
    report = get_report_by_id(1)  # Replace with actual ID
