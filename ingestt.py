import json
from pathlib import Path
from sqlmodel import SQLModel, Session, select
from data.models import UnifiedReport, Account, FinancialEntry # Assumes you saved the new models in data/unified_models.py
from db import engine, get_db_session
from typing import Optional, List, Dict
from datetime import datetime
from sqlmodel import SQLModel, Session, select, func

# --- Constants for Standardizing Account Groups ---
# Using standard group names makes querying consistent across data sources.
GROUP_REVENUE = "Income"
GROUP_COGS = "Cost of Goods Sold"
GROUP_OPEX = "Operating Expense"
GROUP_NON_OP_REVENUE = "Non-Operating Revenue"
GROUP_NON_OP_EXPENSE = "Non-Operating Expense"
GROUP_OTHER = "Other"

# ==============================================================================
# INGESTION LOGIC FOR data_set_2.json (rootfi)
# ==============================================================================

def _create_accounts_from_rootfi_items(
    session: Session,
    items_data: List[Dict],
    group_name: str,
    report_id: int,
    report_end_date: datetime,
    parent_id: Optional[int] = None,
):
    """
    Recursively processes a list of items from the rootfi data, creating
    unified Account and FinancialEntry records.
    """
    for item_data in items_data:
        if not isinstance(item_data, dict):
            continue

        # 1. Create the Account record
        new_account = Account(
            name=item_data.get("name", "Unnamed Account"),
            group=group_name,
            source_account_id=item_data.get("account_id"),
            report_id=report_id,
            parent_id=parent_id,
        )
        session.add(new_account)
        session.flush()  # Assigns an ID to new_account for linking

        # 2. Create the corresponding FinancialEntry record
        # rootfi data provides one value for the whole period, so we use the report's end_date
        entry = FinancialEntry(
            value=item_data.get("value", 0.0),
            date=report_end_date,
            account_id=new_account.id,
        )
        session.add(entry)

        # 3. Recurse for any nested child items
        if child_items := item_data.get("line_items"):
            _create_accounts_from_rootfi_items(
                session, child_items, group_name, report_id, report_end_date, parent_id=new_account.id
            )

def ingest_rootfi_data(session: Session, data_path: Path):
    """Parses and ingests financial data from the rootfi JSON file."""
    print(f"📄 Loading rootfi data from {data_path}...")
    with open(data_path, 'r') as f:
        financial_records = json.load(f).get("data", [])

    print(f"📊 Found {len(financial_records)} financial records to ingest from rootfi.")

    for record_data in financial_records:
        try:
            # 1. Create the UnifiedReport for this record
            report_end_date = datetime.fromisoformat(record_data["period_end"])
            report = UnifiedReport(
                report_name=f"Financial Statement - {record_data['period_start']} to {record_data['period_end']}",
                report_basis="Unknown", # Not provided in this data source
                start_period=datetime.fromisoformat(record_data["period_start"]),
                end_period=report_end_date,
                currency=record_data.get("currency_id", "USD"),
                generated_time=datetime.fromisoformat(record_data["rootfi_updated_at"]),
                platform_id=record_data.get("platform_id"),
                platform_unique_id=str(record_data.get("rootfi_id")),
                rootfi_company_id=record_data.get("rootfi_company_id"),
                gross_profit=record_data.get("gross_profit"),
                operating_profit=record_data.get("operating_profit"),
                net_profit=record_data.get("net_profit"),
                earnings_before_taxes=record_data.get("earnings_before_taxes"),
                taxes=record_data.get("taxes"),
            )
            session.add(report)
            session.flush()  # Get the ID for linking accounts

            # 2. Process each section, mapping it to the unified Account model
            item_mapping = {
                "revenue": GROUP_REVENUE,
                "cost_of_goods_sold": GROUP_COGS,
                "operating_expenses": GROUP_OPEX,
                "non_operating_revenue": GROUP_NON_OP_REVENUE,
                "non_operating_expenses": GROUP_NON_OP_EXPENSE,
            }

            for json_key, group_name in item_mapping.items():
                if items_data := record_data.get(json_key):
                    _create_accounts_from_rootfi_items(
                        session, items_data, group_name, report.id, report.end_period
                    )
        except Exception as e:
            print(f"❌ Error ingesting rootfi record: {e}")
            session.rollback()

# ==============================================================================
# INGESTION LOGIC FOR data_set_1.json (QBO)
# ==============================================================================

def _create_accounts_from_qbo_rows(
    session: Session,
    rows: List[dict],
    report_id: int,
    date_map: Dict[int, datetime],
    accounts_cache: Dict[str, Account],
    parent_account: Optional[Account] = None,
    parent_group: Optional[str] = None,
):
    """Recursively processes rows from QBO data to create unified Account and FinancialEntry records."""
    for row_data in rows:
        col_data = row_data.get('Header', row_data.get('Summary', row_data)).get('ColData')
        if not col_data:
            continue

        account_info = col_data[0]
        source_id = account_info.get('id')
        account_name = account_info['value']
        current_group = row_data.get('group', parent_group) or GROUP_OTHER
        current_account = parent_account

        if source_id:
            if source_id not in accounts_cache:
                new_account = Account(
                    source_account_id=source_id,
                    name=account_name,
                    group=current_group,
                    report_id=report_id,
                    parent_id=parent_account.id if parent_account else None
                )
                session.add(new_account)
                session.flush()
                accounts_cache[source_id] = new_account
            
            current_account = accounts_cache[source_id]

            # Create FinancialEntry records for each time-based column
            for i, cell in enumerate(col_data):
                if i in date_map and cell.get('value'):
                    entry = FinancialEntry(
                        date=date_map[i],
                        value=float(cell['value']),
                        account_id=current_account.id
                    )
                    session.add(entry)
        
        # Recurse for child rows
        if 'Rows' in row_data and 'Row' in row_data['Rows']:
            _create_accounts_from_qbo_rows(
                session, row_data['Rows']['Row'], report_id, date_map, accounts_cache, current_account, current_group
            )

def ingest_qbo_data(session: Session, data_path: Path):
    """Parses and ingests financial data from the QBO-style JSON file."""
    print(f"📄 Loading QBO data from {data_path}...")
    with open(data_path, 'r') as f:
        data = json.load(f)['data']

    # 1. Create the UnifiedReport
    header = data['Header']
    report = UnifiedReport(
        report_name=header['ReportName'],
        report_basis=header['ReportBasis'],
        start_period=datetime.fromisoformat(header['StartPeriod']),
        end_period=datetime.fromisoformat(header['EndPeriod']),
        currency=header['Currency'],
        generated_time=datetime.fromisoformat(header['Time']),
        platform_id="qbo" # Hardcode the platform for this source
    )
    session.add(report)
    session.commit() # Commit here to get the final ID and ensure it exists
    session.refresh(report)
    print(f"📊 Created Report '{report.report_name}' with ID: {report.id}")

    # 2. Prepare column-to-date mapping
    date_map = {
        i: datetime.fromisoformat(meta['Value'])
        for i, col in enumerate(data['Columns']['Column'])
        if i > 0 and (meta := next((m for m in col.get('MetaData', []) if m['Name'] == 'EndDate'), None))
    }

    # 3. Process all rows to create Accounts and Entries
    _create_accounts_from_qbo_rows(session, data['Rows']['Row'], report.id, date_map, accounts_cache={})

# ==============================================================================
# MAIN EXECUTION AND VERIFICATION
# ==============================================================================

def verify_data(session: Session):
    """Runs a few queries to verify that data was ingested correctly."""
    print("\n" + "="*20 + " VERIFICATION " + "="*20)
    
    report_count = session.exec(select(func.count(UnifiedReport.id))).one()
    account_count = session.exec(select(func.count(Account.id))).one()
    entry_count = session.exec(select(func.count(FinancialEntry.id))).one()
    
    print(f"✅ Total Reports in DB: {report_count}")
    print(f"✅ Total Accounts in DB: {account_count}")
    print(f"✅ Total Financial Entries in DB: {entry_count}")

    if entry_count > 0:
        # Example query: Get total income across all reports
        total_income_result = session.exec(
            select(func.sum(FinancialEntry.value))
            .join(Account)
            .where(Account.group == GROUP_REVENUE)
        ).one_or_none()
        total_income = total_income_result or 0
        print(f"💰 Total Combined Income (from all sources): ${total_income:,.2f}")

def main():
    """Main function to clear DB and handle data ingestion from all sources."""
    print("🚀 Starting Data Ingestion to Unified Schema...")
    
    # Reset the database for a clean run
    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)
    print("🧹 Database has been reset.")

    data_dir = Path("AI Engineer x Kudwa Take-Home Test 24a14e124c6780a68e6cdcdeb5442fdf")
    
    with get_db_session() as session:
        # Ingest data from the first file
        ingest_qbo_data(session, data_dir / "data_set_1.json")
        
        # Ingest data from the second file
        ingest_rootfi_data(session, data_dir / "data_set_2.json")
        
        print("\nCommitting all transactions...")
        session.commit()
        
        # Run verification queries on the combined data
        verify_data(session)

    print("\n🎉 Ingestion process complete!")

if __name__ == "__main__":
    main()