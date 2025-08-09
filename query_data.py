#!/usr/bin/env python3
"""
Query script to demonstrate accessing the ingested financial data
"""

import json
import os
from sqlmodel import SQLModel, Session, select
from sqlalchemy import create_engine
from data.models import FinancialReport

def query_financial_data():
    """Query and display financial data from the database"""
    
    # Connect to the database
    db_url = os.getenv("DATABASE_URL", "sqlite:///financial_reports.db")
    engine = create_engine(db_url, echo=False)
    
    with Session(engine) as session:
        # Get all financial reports
        statement = select(FinancialReport)
        reports = session.exec(statement).all()
        
        print(f"📊 Found {len(reports)} financial reports in database\n")
        
        # Show summary of first few reports
        for i, report in enumerate(reports[:1]):
            print(json.dumps(record := report.model_dump(), indent=2))
            continue  # Skip detailed output for brevity
            print(f"🏢 Report {i+1}:")
            print(f"   Period: {report.period_start} to {report.period_end}")
            print(f"   Gross Profit: ${report.gross_profit:,.2f}")
            print(f"   Net Profit: ${report.net_profit:,.2f}")
            
            # Use property getters to access structured LineItem data
            revenue_items = report.revenue_items
            if revenue_items:
                print(f"   Revenue Categories: {len(revenue_items)}")
                for rev_item in revenue_items[:2]:  # Show first 2
                    print(f"      - {rev_item.name}: ${rev_item.value:,.2f}")
                    if rev_item.line_items:
                        print(f"        └─ Has {len(rev_item.line_items)} sub-items")
                        # Show first sub-item
                        first_sub = rev_item.line_items[0]
                        print(f"        └─ {first_sub.name}: ${first_sub.value:,.2f}")
            
            expense_items = report.operating_expenses_items
            if expense_items:
                print(f"   Expense Categories: {len(expense_items)}")
                for exp_item in expense_items[:1]:  # Show first 1
                    print(f"      - {exp_item.name}: ${exp_item.value:,.2f}")
                    if exp_item.line_items:
                        print(f"        └─ Has {len(exp_item.line_items)} detailed items")
            
            print()

def monthly_summary():
    """Show monthly profit summary"""
    db_url = os.getenv("DATABASE_URL", "sqlite:///financial_reports.db")
    engine = create_engine(db_url, echo=False)
    
    with Session(engine) as session:
        statement = select(FinancialReport).order_by(FinancialReport.period_start)
        reports = session.exec(statement).all()
        
        print("📈 Monthly Financial Summary:")
        print("-" * 60)
        print(f"{'Period':<20} {'Gross Profit':<15} {'Net Profit':<15}")
        print("-" * 60)
        
        total_gross = 0
        total_net = 0
        
        for report in reports:
            period = f"{report.period_start} to {report.period_end}"
            gross = report.gross_profit or 0
            net = report.net_profit or 0
            
            total_gross += gross
            total_net += net
            
            print(f"{period:<20} ${gross:>12,.2f} ${net:>12,.2f}")
        
        print("-" * 60)
        print(f"{'TOTAL':<20} ${total_gross:>12,.2f} ${total_net:>12,.2f}")

if __name__ == "__main__":
    print("🚀 Querying Financial Data\n")
    query_financial_data()
    # print("\n" + "="*70 + "\n")
    # monthly_summary()
