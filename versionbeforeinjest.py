import json
from pathlib import Path
from sqlmodel import SQLModel, Session, select
from data.models import UnifiedReport, Account, FinancialEntry # Assumes you saved the new models in data/unified_models.py
from db import engine, get_db_session
from typing import Optional, List, Dict
from datetime import datetime
from sqlmodel import SQLModel, Session, select, func

# ==============================================================================
# UNIFIED FINANCIAL REPORTING SCHEMA
# ==============================================================================

class UnifiedReport(SQLModel, table=True):
    """
    Stores metadata for a single financial report, combining fields from
    both the original 'Report' and 'FinancialStatement' models.
    """
    id: Optional[int] = Field(default=None, primary_key=True)
    
    # --- Fields from Schema 2 ('Report') ---
    report_name: str = Field(index=True)
    report_basis: str
    start_period: datetime
    end_period: datetime
    currency: Optional[str]
    generated_time: datetime

    # --- Fields from Schema 1 ('FinancialStatement') ---
    platform_id: str  # To identify the source system (e.g., 'rootfi', 'qbo')
    platform_unique_id: Optional[str] = None # The original ID from the source system
    rootfi_company_id: Optional[int] = None # Specific ID if the source is rootfi
    
    # --- Calculated/Summary Fields from Schema 1 ---
    # These are kept for quick access but could also be calculated on the fly
    # from the associated accounts.
    gross_profit: Optional[float] = None
    operating_profit: Optional[float] = None
    net_profit: Optional[float] = None
    earnings_before_taxes: Optional[float] = None
    taxes: Optional[float] = None
    
    # --- Relationships ---
    # A single relationship to a flexible chart of accounts.
    accounts: List["Account"] = Relationship(back_populates="report")


class Account(SQLModel, table=True):
    """
    Represents a single account in the report (e.g., "Revenue", "Software Fees").
    This model replaces all the separate `...Item` tables from Schema 1.
    The hierarchy is self-contained.
    """
    id: Optional[int] = Field(default=None, primary_key=True)
    
    # --- Fields from Schema 2 ('Account') ---
    name: str
    # The 'group' field is the key to replacing Schema 1's separate tables.
    group: str = Field(description="The financial group, e.g., 'Revenue', 'Cost of Goods Sold', 'Operating Expense'")
    
    # Source-specific ID (e.g., from QBO or another system)
    source_account_id: Optional[str] = Field(default=None, index=True) 

    # --- Hierarchy Management (from both schemas) ---
    parent_id: Optional[int] = Field(default=None, foreign_key="account.id")
    parent: Optional["Account"] = Relationship(
        back_populates="children",
        sa_relationship_kwargs={"remote_side": "Account.id"}
    )
    children: List["Account"] = Relationship(back_populates="parent")

    # --- Relationship to the main report ---
    report_id: int = Field(foreign_key="unifiedreport.id")
    report: "UnifiedReport" = Relationship(back_populates="accounts")
    
    # --- Relationship to its financial values ---
    financial_entries: List["FinancialEntry"] = Relationship(back_populates="account")


class FinancialEntry(SQLModel, table=True):
    """
    Stores a single financial value for a specific account.
    This model is more granular than Schema 1's simple 'value' field,
    which is an advantage.
    """
    id: Optional[int] = Field(default=None, primary_key=True)
    value: float
    # We keep the 'date' field from Schema 2 for granularity. For Schema 1 data,
    # this could simply be the 'end_period' of the report.
    date: datetime

    # --- Relationship to the account ---
    account_id: int = Field(foreign_key="account.id")
    account: "Account" = Relationship(back_populates="financial_entries")

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
        value = item_data.get("value", 0.0)
        if value != 0:  # Only create entries for non-zero values
            entry = FinancialEntry(
                value=value,
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
            # Skip records that don't have essential fields
            if not record_data.get("period_end") or not record_data.get("period_start") or not record_data.get("rootfi_updated_at"):
                continue
                
            # 1. Create the UnifiedReport for this record
            report_end_date = datetime.fromisoformat(record_data["period_end"])
            report = UnifiedReport(
                report_name=f"Financial Statement - {record_data['period_start']} to {record_data['period_end']}",
                report_basis="Unknown", # Not provided in this data source
                start_period=datetime.fromisoformat(record_data["period_start"]),
                end_period=report_end_date,
                currency=record_data.get("currency_id") or "USD",
                generated_time=datetime.fromisoformat(record_data["rootfi_updated_at"]),
                platform_id="rootfi",  # Static identifier for this data source
                platform_unique_id=str(record_data.get("rootfi_id")) if record_data.get("rootfi_id") else None,
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
                    if isinstance(items_data, list) and len(items_data) > 0:
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
        # Get ColData from Header, Summary, or the row itself
        col_data = None
        if 'Header' in row_data and 'ColData' in row_data['Header']:
            col_data = row_data['Header']['ColData']
        elif 'Summary' in row_data and 'ColData' in row_data['Summary']:
            col_data = row_data['Summary']['ColData']
        elif 'ColData' in row_data:
            col_data = row_data['ColData']
            
        if not col_data or not isinstance(col_data, list) or len(col_data) == 0:
            # Process child rows even if current row has no ColData
            if 'Rows' in row_data and 'Row' in row_data['Rows']:
                _create_accounts_from_qbo_rows(
                    session, row_data['Rows']['Row'], report_id, date_map, accounts_cache, parent_account, parent_group
                )
            continue

        account_info = col_data[0]
        source_id = account_info.get('id')
        account_name = account_info.get('value', 'Unnamed Account')
        
        # Skip if there's no account name
        if not account_name or account_name.strip() == '':
            continue
            
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
                    try:
                        value = float(cell['value'])
                        if value != 0:  # Only create entries for non-zero values
                            entry = FinancialEntry(
                                date=date_map[i],
                                value=value,
                                account_id=current_account.id
                            )
                            session.add(entry)
                    except (ValueError, TypeError):
                        # Skip invalid values
                        continue
        
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
    date_map = {}
    for i, col in enumerate(data['Columns']['Column']):
        if i > 0:  # Skip the first column (Account column)
            meta_data = col.get('MetaData', [])
            end_date_meta = next((m for m in meta_data if m['Name'] == 'EndDate'), None)
            if end_date_meta:
                date_map[i] = datetime.fromisoformat(end_date_meta['Value'])

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