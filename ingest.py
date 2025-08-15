import json
import sqlite3
from datetime import datetime, date
from typing import Dict, List, Any, Optional
import os
from sqlmodel import SQLModel, create_engine, Session, Field
from data.models import FinancialStatement
# Define our simplified database model


def parse_first_file_format(file_path: str) -> List[Dict[str, Any]]:
    """Parse the first file format (QuickBooks-like column-based format)"""
    with open(file_path, 'r') as f:
        data = json.load(f)
    
    results = []
    
    # Extract column metadata to map column positions to dates
    columns = data["data"]["Columns"]["Column"]
    # Skip the first column (account names), start from index 1
    month_columns = columns[1:]
    
    # Helper: recursively walk nested Row structures and yield rows of type "Data"
    def walk_rows(row_list):
        for r in row_list:
            if r.get("type") == "Data":
                yield r
            # nested rows may appear under r.get("Rows") which can be a dict with key "Row"
            nested = r.get("Rows") or {}
            nested_rows = None
            if isinstance(nested, dict):
                nested_rows = nested.get("Row")
            elif isinstance(nested, list):
                nested_rows = nested

            if nested_rows:
                # nested_rows can be a single dict or a list
                if isinstance(nested_rows, dict):
                    yield from walk_rows([nested_rows])
                else:
                    yield from walk_rows(nested_rows)

    # Start from top-level rows (may be a list)
    top_rows = data["data"].get("Rows", {}).get("Row", [])
    if isinstance(top_rows, dict):
        top_rows = [top_rows]

    # Process each data row (recursively found)
    for row in walk_rows(top_rows):
        coldata = row.get("ColData", [])
        if not coldata:
            continue

        # Extract account ID and name safely
        first_col = coldata[0]
        account_id = first_col.get("id") or first_col.get("account_id") or first_col.get("value")
        account_name = first_col.get("value") or first_col.get("name") or ""

        # Process each month's value and map to month_columns (be defensive about lengths)
        for i, col_data in enumerate(coldata[1:]):  # Skip first column
            val = col_data.get("value")
            if val is None or val == "":
                continue

            try:
                amount = float(str(val).replace(",", ""))
            except (ValueError, TypeError):
                # skip values that aren't numeric
                continue

            # Determine period from corresponding month column metadata; be defensive
            period = None
            try:
                col_meta = month_columns[i] if i < len(month_columns) else None
                if col_meta:
                    meta_list = col_meta.get("MetaData", []) or []
                    for meta in meta_list:
                        if isinstance(meta, dict) and meta.get("Value"):
                            period = datetime.strptime(meta["Value"], "%Y-%m-%d").date()
                            break
            except Exception:
                period = None

            # Fallback: try parsing "ColTitle" like "Jan 2020" into first-of-month
            if period is None:
                try:
                    col_title = month_columns[i].get("ColTitle", "") if i < len(month_columns) else ""
                    if col_title:
                        try:
                            dt = datetime.strptime(col_title, "%b %Y")
                            period = date(dt.year, dt.month, 1)
                        except Exception:
                            period = None
                except Exception:
                    period = None

            if period is None:
                # can't map this column to a period; skip
                continue

            results.append({
                "period": period,
                "account_id": account_id,
                "account_name": account_name,
                "amount": amount,
                "parent_account_id": None  # First format doesn't explicitly show hierarchy
            })
    
    return results

def extract_line_items(line_items: List[Dict], parent_account_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """Recursively extract line items from the hierarchical structure"""
    results = []
    
    for item in line_items:
        current_id = item.get("account_id")
        results.append({
            "period": None,  # Will be filled in later
            "account_id": current_id,
            "account_name": item["name"],
            "amount": item["value"],
            "parent_account_id": parent_account_id
        })
        
        # Process nested line items
        if "line_items" in item and item["line_items"]:
            results.extend(extract_line_items(item["line_items"], current_id))
    
    return results

def parse_second_file_format(file_path: str) -> List[Dict[str, Any]]:
    """Parse the second file format (hierarchical JSON with account IDs)"""
    with open(file_path, 'r') as f:
        data = json.load(f)
    
    results = []
    
    for entry in data["data"]:
        # Extract period start date
        period_start = datetime.strptime(entry["period_start"], "%Y-%m-%d").date()
        
        # Process revenue
        for revenue_section in entry["revenue"]:
            results.append({
                "period": period_start,
                "account_id": revenue_section.get("account_id", revenue_section["name"].replace(" ", "_").lower()),
                "account_name": revenue_section["name"],
                "amount": revenue_section["value"],
                "parent_account_id": None
            })
            
            if "line_items" in revenue_section:
                line_items = extract_line_items(revenue_section["line_items"], 
                                              revenue_section.get("account_id"))
                for item in line_items:
                    item["period"] = period_start
                    results.append(item)
        
        # Process cost of goods sold
        for cogs_section in entry["cost_of_goods_sold"]:
            results.append({
                "period": period_start,
                "account_id": cogs_section.get("account_id", cogs_section["name"].replace(" ", "_").lower()),
                "account_name": cogs_section["name"],
                "amount": cogs_section["value"],
                "parent_account_id": None
            })
            
            if "line_items" in cogs_section and cogs_section["line_items"]:
                line_items = extract_line_items(cogs_section["line_items"], 
                                              cogs_section.get("account_id"))
                for item in line_items:
                    item["period"] = period_start
                    results.append(item)
        
        # Process operating expenses
        for expense_section in entry["operating_expenses"]:
            results.append({
                "period": period_start,
                "account_id": expense_section.get("account_id", expense_section["name"].replace(" ", "_").lower()),
                "account_name": expense_section["name"],
                "amount": expense_section["value"],
                "parent_account_id": None
            })
            
            if "line_items" in expense_section:
                line_items = extract_line_items(expense_section["line_items"], 
                                              expense_section.get("account_id"))
                for item in line_items:
                    item["period"] = period_start
                    results.append(item)
        
        # Process non-operating revenue
        for non_op_rev in entry["non_operating_revenue"]:
            results.append({
                "period": period_start,
                "account_id": non_op_rev.get("account_id", non_op_rev["name"].replace(" ", "_").lower()),
                "account_name": non_op_rev["name"],
                "amount": non_op_rev["value"],
                "parent_account_id": None
            })
            
            if "line_items" in non_op_rev and non_op_rev["line_items"]:
                line_items = extract_line_items(non_op_rev["line_items"], 
                                              non_op_rev.get("account_id"))
                for item in line_items:
                    item["period"] = period_start
                    results.append(item)
        
        # Process non-operating expenses
        for non_op_exp in entry["non_operating_expenses"]:
            results.append({
                "period": period_start,
                "account_id": non_op_exp.get("account_id", non_op_exp["name"].replace(" ", "_").lower()),
                "account_name": non_op_exp["name"],
                "amount": non_op_exp["value"],
                "parent_account_id": None
            })
            
            if "line_items" in non_op_exp and non_op_exp["line_items"]:
                line_items = extract_line_items(non_op_exp["line_items"], 
                                              non_op_exp.get("account_id"))
                for item in line_items:
                    item["period"] = period_start
                    results.append(item)
        
        # Add gross profit as a top-level metric
        if entry["gross_profit"] is not None:
            results.append({
                "period": period_start,
                "account_id": "gross_profit",
                "account_name": "Gross Profit",
                "amount": entry["gross_profit"],
                "parent_account_id": None
            })
        
        # Add operating profit as a top-level metric
        if entry["operating_profit"] is not None:
            results.append({
                "period": period_start,
                "account_id": "operating_profit",
                "account_name": "Operating Profit",
                "amount": entry["operating_profit"],
                "parent_account_id": None
            })
        
        # Add net profit as a top-level metric
        if entry["net_profit"] is not None:
            results.append({
                "period": period_start,
                "account_id": "net_profit",
                "account_name": "Net Profit",
                "amount": entry["net_profit"],
                "parent_account_id": None
            })
    
    return results

def save_to_database(records: List[Dict[str, Any]]):
    """Save parsed records to SQLite database"""
    from db import get_db_session
    
    # Insert data using the context manager provided by get_db_session()
    with get_db_session() as session:
        for record in records:
            # Convert date objects to strings for JSON serialization if needed
            db_record = FinancialStatement(
                period=record["period"],
                account_id=record["account_id"],
                account_name=record["account_name"],
                amount=record["amount"],
                parent_account_id=record["parent_account_id"]
            )
            session.add(db_record)

        # commit here (context manager will also commit after yield)
        try:
            session.commit()
        except Exception:
            session.rollback()
            raise


def main():
    # Paths to your JSON files
    first_file_path = "AI Engineer x Kudwa Take-Home Test 24a14e124c6780a68e6cdcdeb5442fdf/data_set_1.json"
    second_file_path = "AI Engineer x Kudwa Take-Home Test 24a14e124c6780a68e6cdcdeb5442fdf/data_set_2.json"
    
    # Parse both files
    print("Parsing first file format...")
    first_file_records = parse_first_file_format(first_file_path)
    print(f"Parsed {len(first_file_records)} records from the first file.")
    
    print("Parsing second file format...")
    second_file_records = parse_second_file_format(second_file_path)
    print(f"Parsed {len(second_file_records)} records from the second file.")
    
    # Combine records
    all_records = first_file_records + second_file_records
    
    # Save to database
    print(f"Total records to insert: {len(all_records)}")
    save_to_database(all_records)
    
    print("Data ingestion completed successfully!")

if __name__ == "__main__":
    main()