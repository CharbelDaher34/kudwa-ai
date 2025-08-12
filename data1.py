import json
import warnings
from datetime import datetime
from typing import List, Optional
from db import engine, get_db_session
from sqlmodel import Field, Relationship, SQLModel, create_engine, Session, select, func
from data.modvvvels import *

# 2. PARSING AND DATA INJECTION LOGIC
# ==============================================================================

def parse_and_load_pnl(session: Session, json_filepath: str):
    """
    Parses the P&L JSON file and loads the data into the database
    using the defined SQLModel classes.

    Args:
        session: The SQLModel session object for database interaction.
        json_filepath: The path to the input JSON file.
    """
    print(f"Loading data from {json_filepath}...")
    with open(json_filepath, 'r') as f:
        data = json.load(f)['data']

    # --- Create the Report record ---
    header = data['Header']
    report = Report(
        report_name=header['ReportName'],
        report_basis=header['ReportBasis'],
        start_period=datetime.fromisoformat(header['StartPeriod']),
        end_period=datetime.fromisoformat(header['EndPeriod']),
        currency=header['Currency'],
        generated_time=datetime.fromisoformat(header['Time'])
    )
    session.add(report)
    session.commit()
    session.refresh(report)
    print(f"Created Report ID: {report.id}")

    # --- Prepare column date mapping ---
    # Create a mapping from column index to its end date.
    columns = data['Columns']['Column']
    date_map = {}
    for i, col in enumerate(columns):
        # Skip the first column which is the account name
        if i == 0:
            continue
        # Find the EndDate metadata, default to today if not present (for 'Total' col)
        end_date_str = next((meta['Value'] for meta in col.get('MetaData', []) if meta['Name'] == 'EndDate'), None)
        if end_date_str:
            date_map[i] = datetime.fromisoformat(end_date_str)

    # --- Recursively process rows to create Accounts and Financial Entries ---
    accounts_cache = {} # Cache to keep track of created accounts by ID

    def process_rows(rows: List[dict], parent_account: Optional[Account] = None, parent_group: Optional[str] = None):
        """Helper function to recursively process the nested row structure."""
        for row_data in rows:
            # Handle different row types (Section, Data, Summary)
            if 'Header' in row_data:
                col_data = row_data['Header']['ColData']
            elif 'Summary' in row_data:
                col_data = row_data['Summary']['ColData']
            elif 'ColData' in row_data:
                col_data = row_data['ColData']
            else:
                # Skip rows that don't have any column data
                continue
            
            account_info = col_data[0]
            account_id = int(account_info.get('id', -1))
            account_name = account_info['value']

            # Determine the group for this account
            current_group = row_data.get('group', parent_group)

            # For rows with IDs, create the account
            current_account = parent_account
            if account_id != -1:
                # Create the Account if it doesn't exist
                if account_id not in accounts_cache:
                    new_account = Account(
                        qbo_id=account_id,
                        name=account_name,
                        type="Account",  # Default type
                        group=current_group or "Other",  # Ensure group is not None
                        report_id=report.id,
                        parent_id=parent_account.id if parent_account else None
                    )
                    session.add(new_account)
                    session.flush()  # Get the database-generated ID
                    accounts_cache[account_id] = new_account
                
                current_account = accounts_cache[account_id]

                # Create FinancialEntry records for the account
                # We iterate through the columns of the current row
                for i, cell in enumerate(col_data):
                    if i in date_map and cell.get('value') and cell['value'] != "":
                        entry = FinancialEntry(
                            date=date_map[i],
                            value=float(cell['value']),
                            account_id=current_account.id
                        )
                        session.add(entry)
            # Recursively process child rows if they exist
            if 'Rows' in row_data and 'Row' in row_data['Rows']:
                process_rows(row_data['Rows']['Row'], parent_account=current_account, parent_group=current_group)

    # Start processing from the top-level rows
    process_rows(data['Rows']['Row'])
    
    session.commit()
    print("Successfully parsed and loaded all data into the database.")


    # --- Verification Step ---
    # You can query the data to make sure it was inserted correctly.
    print("\n--- Verification ---")
    report_count = len(session.exec(select(Report)).all())
    account_count = len(session.exec(select(Account)).all())
    entry_count = len(session.exec(select(FinancialEntry)).all())
    
    print(f"Total Reports: {report_count}")
    print(f"Total Accounts: {account_count}")
    print(f"Total Financial Entries: {entry_count}")
    
    # Example query: Get total income for August 2024
    from sqlalchemy import extract
    
    # Use SQLModel's exec with select for the query
    income_entries = session.exec(
        select(FinancialEntry.value)
        .join(Account)
        .where(
            Account.group == 'Income',
            extract('year', FinancialEntry.date) == 2024,
            extract('month', FinancialEntry.date) == 8
        )
    ).all()
    
    total_income_aug_2024 = sum(income_entries) if income_entries else 0
    
    print(f"Total Income for August 2024: ${total_income_aug_2024:,.2f}")

# 3. EXAMPLE USAGE
# ==============================================================================

if __name__ == "__main__":
    # Setup the database engine (using SQLite in-memory for this example)
    # For a real application, you would connect to PostgreSQL, MySQL, etc.
    # DATABASE_URL = "sqlite:///pnl_data.db"
    # engine = create_engine(DATABASE_URL, echo=False) # Set echo=True to see SQL statements

    # Create the database and tables
    SQLModel.metadata.create_all(engine)

    # Create a session and run the parsing function
    with get_db_session() as session:
        # Clear existing data to prevent duplicates on re-runs
        # SQLModel doesn't have built-in delete methods, so we'll keep using query for deletions
        # but use exec for counting
        # Delete all records from each table
        # Another alternative - select all records then delete them
        from sqlmodel import delete
        
        # Create delete statements
        stmt1 = delete(FinancialEntry)
        stmt2 = delete(Account)
        stmt3 = delete(Report)
        
        # Execute deletions
        session.exec(stmt1)
        session.exec(stmt2)
        session.exec(stmt3)
        session.commit()

        # Path to your JSON file
        json_file = 'AI Engineer x Kudwa Take-Home Test 24a14e124c6780a68e6cdcdeb5442fdf/data_set_1.json'
        
        # Run the main function
        parse_and_load_pnl(session, json_file)

        # --- Verification Step ---
        # You can query the data to make sure it was inserted correctly.
        print("\n--- Verification ---")
        report_count = len(session.exec(select(Report)).all())
        account_count = len(session.exec(select(Account)).all())
        entry_count = len(session.exec(select(FinancialEntry)).all())
        
        print(f"Total Reports: {report_count}")
        print(f"Total Accounts: {account_count}")
        print(f"Total Financial Entries: {entry_count}")
        
        # Example query: Get total income for August 2024
        from sqlalchemy import extract
        
        # Use SQLModel's exec with select for the query
        income_entries = session.exec(
            select(FinancialEntry.value)
            .join(Account)
            .where(
                Account.group == 'Income',
                extract('year', FinancialEntry.date) == 2024,
                extract('month', FinancialEntry.date) == 8
            )
        ).all()
        
        total_income_aug_2024 = sum(income_entries) if income_entries else 0
        
        print(f"Total Income for August 2024: ${total_income_aug_2024:,.2f}")