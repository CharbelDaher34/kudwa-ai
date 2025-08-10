## Ingest JSON financial data into the database using SQLModel and SQLAlchemy
# This file is used to ingest data into the database using SQLModel and SQLAlchemy
import json
from pathlib import Path
from sqlmodel import SQLModel, Session, select
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
from db import engine, get_db_session
from typing import Optional, List
from datetime import datetime
def ingest_report_data():
    """
    Parses the P&L JSON file and loads the data into the database
    using the defined SQLModel classes.

    Args:
        session: The SQLModel session object for database interaction.
        json_filepath: The path to the input JSON file.
    """
    with get_db_session() as session:
        
        data_dir = Path("AI Engineer x Kudwa Take-Home Test 24a14e124c6780a68e6cdcdeb5442fdf")
    
        # Load data_set_1.json (this contains the compatible format)
        json_filepath = data_dir / "data_set_1.json"
        
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


## rootfi
def create_line_items(items_data, item_class, financial_statement_id, session, parent_id=None):
    """Recursively create line items from JSON data"""
    created_items = []
    
    for item_data in items_data:
        if not item_data or not isinstance(item_data, dict):
            continue
            
        # Create the main item
        item = item_class(
            name=item_data.get("name", ""),
            value=item_data.get("value", 0.0),
            account_id=item_data.get("account_id"),
            financial_statement_id=financial_statement_id,
            parent_id=parent_id
        )
        session.add(item)
        session.flush()  # Get the ID for child items
        created_items.append(item)
        
        # Process nested line_items if they exist
        line_items = item_data.get("line_items", [])
        if line_items:
            create_line_items(line_items, item_class, financial_statement_id, session, item.id)
    
    return created_items
def ingest_rootfi_data():
    # Path to JSON data files
    data_dir = Path("AI Engineer x Kudwa Take-Home Test 24a14e124c6780a68e6cdcdeb5442fdf")
    
    # Load data_set_2.json (this contains the compatible format)
    data_set_2_path = data_dir / "data_set_2.json"
    
    if not data_set_2_path.exists():
        print(f"❌ Error: {data_set_2_path} not found!")
        return
    
    print(f"📄 Loading data from {data_set_2_path}")
    
    with open(data_set_2_path, 'r') as f:
        json_data = json.load(f)
    
    # Extract the data array
    financial_records = json_data.get("data", [])
    
    if not financial_records:
        print("❌ No financial records found in the JSON file!")
        return
    
    print(f"📊 Found {len(financial_records)} financial records to ingest")
    
    # Ingest the data
    successful_ingests = 0
    failed_ingests = 0
    
    with get_db_session() as session:
        for i, record_data in enumerate(financial_records):
            try:
                # Skip records with missing essential data
                if not record_data or not isinstance(record_data, dict):
                    print(f"⚠️  Skipping record {i+1}: Invalid record structure")
                    failed_ingests += 1
                    continue
                
                # Check if record has required fields
                required_fields = ["rootfi_id", "rootfi_created_at", "rootfi_updated_at", 
                                 "rootfi_company_id", "platform_id", "period_end", "period_start"]
                
                missing_fields = [field for field in required_fields if field not in record_data]
                if missing_fields:
                    print(f"⚠️  Skipping record {i+1}: Missing required fields: {missing_fields}")
                    failed_ingests += 1
                    continue
                
                # Extract nested arrays for separate processing
                revenue_data = record_data.pop("revenue", [])
                cost_of_goods_sold_data = record_data.pop("cost_of_goods_sold", [])
                operating_expenses_data = record_data.pop("operating_expenses", [])
                non_operating_revenue_data = record_data.pop("non_operating_revenue", [])
                non_operating_expenses_data = record_data.pop("non_operating_expenses", [])
                
                # Create FinancialStatement instance
                financial_statement = FinancialStatement(**record_data)
                session.add(financial_statement)
                session.flush()  # Get the ID for related items
                
                # Create related line items
                create_line_items(revenue_data, RevenueItem, financial_statement.rootfi_id, session)
                create_line_items(cost_of_goods_sold_data, CostOfGoodsSoldItem, financial_statement.rootfi_id, session)
                create_line_items(operating_expenses_data, OperatingExpenseItem, financial_statement.rootfi_id, session)
                create_line_items(non_operating_revenue_data, NonOperatingRevenueItem, financial_statement.rootfi_id, session)
                create_line_items(non_operating_expenses_data, NonOperatingExpenseItem, financial_statement.rootfi_id, session)
                
                successful_ingests += 1
                
                # Print progress for every 10 records
                if (i + 1) % 10 == 0:
                    print(f"✅ Processed {i + 1} records...")
                    
            except Exception as e:
                print(f"❌ Error ingesting record {i+1}: {e}")
                failed_ingests += 1
                session.rollback()  # Rollback this transaction
                continue
        
        # Commit all successful records
        try:
            session.commit()
            print(f"\n🎉 Successfully ingested {successful_ingests} financial statements!")
            if failed_ingests > 0:
                print(f"⚠️  Failed to ingest {failed_ingests} records")
        except Exception as e:
            print(f"❌ Error committing to database: {e}")
            session.rollback()

def check_existing_data():
    """Check what data already exists in the database"""
    # Create tables if they don't exist
    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)

    try:
        with get_db_session() as session:
            statement = select(FinancialStatement)
            results = session.exec(statement).all()
            count = len(results)
            print(f"📊 Current database contains {count} financial statements")
            
            if count > 0:
                # Show sample of existing data
                sample_records = results[:3]
                print("\n📋 Sample records in database:")
                for record in sample_records:
                    print(f"   - ID: {record.rootfi_id}, Company ID: {record.rootfi_company_id}, "
                          f"Period: {record.period_start} to {record.period_end}, "
                          f"Gross Profit: {record.gross_profit}")
            else:
                print("📋 Database is empty - ready for new data")
    except Exception as e:
        print(f"⚠️  Could not check existing data: {e}")
        print("📋 Database appears to be empty or needs initialization")

def main():
    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)
    """Main function to handle data ingestion"""
    print("🚀 Starting Report Data Ingestion")
    print("=" * 50)
    
    ingest_report_data()
    
    print("🚀 Starting RootFI Data Ingestion")
    
    ingest_rootfi_data()
    

if __name__ == "__main__":
    main()