from sqlmodel import Session, select, func
from data.models import UnifiedReport, Account, FinancialEntry
from db import get_db_session

def analyze_data():
    with get_db_session() as session:
        # Detailed analysis of the data
        print('=== DETAILED DATA ANALYSIS ===')
        
        # QBO Data Analysis
        qbo_reports = session.exec(select(UnifiedReport).where(UnifiedReport.platform_id == 'qbo')).all()
        if qbo_reports:
            qbo_report = qbo_reports[0]
            print(f'QBO Report: {qbo_report.report_name}')
            print(f'Period: {qbo_report.start_period} to {qbo_report.end_period}')
            print(f'Currency: {qbo_report.currency}')
            
            # Count entries by date for QBO
            qbo_entries = session.exec(
                select(FinancialEntry.date, func.count(FinancialEntry.id), func.sum(FinancialEntry.value))
                .join(Account)
                .where(Account.report_id == qbo_report.id)
                .group_by(FinancialEntry.date)
                .order_by(FinancialEntry.date)
            ).all()
            
            print(f'QBO has entries for {len(qbo_entries)} different dates')
            if qbo_entries:
                print(f'First date: {qbo_entries[0][0]}, Entries: {qbo_entries[0][1]}, Total: ${qbo_entries[0][2]:,.2f}')
                print(f'Last date: {qbo_entries[-1][0]}, Entries: {qbo_entries[-1][1]}, Total: ${qbo_entries[-1][2]:,.2f}')
        
        print()
        
        # Rootfi Data Analysis
        rootfi_reports = session.exec(select(UnifiedReport).where(UnifiedReport.platform_id == 'rootfi')).all()
        print(f'Rootfi Reports: {len(rootfi_reports)}')
        
        if rootfi_reports:
            # Show date range of rootfi reports
            periods = [(r.start_period, r.end_period, r.gross_profit, r.net_profit) for r in rootfi_reports[:5]]
            print('Sample Rootfi periods:')
            for start, end, gross, net in periods:
                print(f'  {start.date()} to {end.date()}: Gross=${gross or 0:,.2f}, Net=${net or 0:,.2f}')
            
            # Check if we have the expected monthly reports
            rootfi_by_year = {}
            for report in rootfi_reports:
                year = report.start_period.year
                if year not in rootfi_by_year:
                    rootfi_by_year[year] = 0
                rootfi_by_year[year] += 1
            
            print(f'Rootfi reports by year: {rootfi_by_year}')
        
        print()
        
        # Account group analysis
        print('=== ACCOUNT GROUPS ANALYSIS ===')
        account_groups = session.exec(
            select(Account.group, func.count(Account.id))
            .group_by(Account.group)
        ).all()
        
        for group, count in account_groups:
            print(f'{group}: {count} accounts')
            
            # Sample total for each group
            group_total = session.exec(
                select(func.sum(FinancialEntry.value))
                .join(Account)
                .where(Account.group == group)
            ).one_or_none() or 0
            
            print(f'  Total value: ${group_total:,.2f}')
        
        print()
        
        # Check for potential data issues
        print('=== DATA QUALITY CHECKS ===')
        
        # Check for accounts without entries
        accounts_without_entries = session.exec(
            select(func.count(Account.id))
            .outerjoin(FinancialEntry)
            .where(FinancialEntry.id.is_(None))
        ).one()
        print(f'Accounts without entries: {accounts_without_entries}')
        
        # Check for entries with zero values (we filter these out, so should be 0)
        zero_entries = session.exec(
            select(func.count(FinancialEntry.id))
            .where(FinancialEntry.value == 0)
        ).one()
        print(f'Entries with zero value: {zero_entries}')
        
        # Check for negative values (could be normal for expenses)
        negative_entries = session.exec(
            select(func.count(FinancialEntry.id))
            .where(FinancialEntry.value < 0)
        ).one()
        print(f'Entries with negative values: {negative_entries}')

        # Check income vs expenses ratio
        print()
        print('=== FINANCIAL LOGIC CHECKS ===')
        
        income_total = session.exec(
            select(func.sum(FinancialEntry.value))
            .join(Account)
            .where(Account.group == 'Income')
        ).one_or_none() or 0
        
        expense_groups = ['Operating Expense', 'Cost of Goods Sold', 'Non-Operating Expense']
        expense_total = 0
        for group in expense_groups:
            group_total = session.exec(
                select(func.sum(FinancialEntry.value))
                .join(Account)
                .where(Account.group == group)
            ).one_or_none() or 0
            expense_total += group_total
        
        print(f'Total Income: ${income_total:,.2f}')
        print(f'Total Expenses: ${expense_total:,.2f}')
        print(f'Net Income: ${income_total - expense_total:,.2f}')

if __name__ == "__main__":
    analyze_data()
