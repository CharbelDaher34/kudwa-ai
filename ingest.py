## Ingest JSON financial data into the database using SQLModel and SQLAlchemy
# This file is used to ingest data into the database using SQLModel and SQLAlchemy
from sqlmodel import SQLModel, Session, select
from sqlalchemy import create_engine
from data.models import FinancialReport, LineItem
import os
import json
from pathlib import Path
def ingest_data():
    # Create the database engine
    db_url = os.getenv("DATABASE_URL", "sqlite:///financial_reports.db")
    engine = create_engine(db_url, echo=True)

    # Create the tables if they don't exist
    SQLModel.metadata.create_all(engine)

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
    
    with Session(engine) as session:
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
                
                # Create FinancialReport instance
                financial_report = FinancialReport(**record_data)
                session.add(financial_report)
                successful_ingests += 1
                
                # Print progress for every 10 records
                if (i + 1) % 10 == 0:
                    print(f"✅ Processed {i + 1} records...")
                    
            except Exception as e:
                print(f"❌ Error ingesting record {i+1}: {e}")
                failed_ingests += 1
                continue
        
        # Commit all successful records
        try:
            session.commit()
            print(f"\n🎉 Successfully ingested {successful_ingests} financial records!")
            if failed_ingests > 0:
                print(f"⚠️  Failed to ingest {failed_ingests} records")
        except Exception as e:
            print(f"❌ Error committing to database: {e}")
            session.rollback()

def check_existing_data():
    """Check what data already exists in the database"""
    db_url = os.getenv("DATABASE_URL", "sqlite:///financial_reports.db")
    engine = create_engine(db_url, echo=False)
    
    # Create tables if they don't exist
    SQLModel.metadata.create_all(engine)
    
    try:
        with Session(engine) as session:
            statement = select(FinancialReport)
            results = session.exec(statement).all()
            count = len(results)
            print(f"📊 Current database contains {count} financial reports")
            
            if count > 0:
                # Show sample of existing data
                sample_records = results[:3]
                print("\n📋 Sample records in database:")
                for record in sample_records:
                    print(f"   - ID: {record.id}, RootFI ID: {record.rootfi_id}, "
                          f"Period: {record.period_start} to {record.period_end}, "
                          f"Gross Profit: {record.gross_profit}")
            else:
                print("📋 Database is empty - ready for new data")
    except Exception as e:
        print(f"⚠️  Could not check existing data: {e}")
        print("📋 Database appears to be empty or needs initialization")

def main():
    """Main function to handle data ingestion"""
    print("🚀 Starting Financial Data Ingestion")
    print("=" * 50)
    
    # Check existing data first
    check_existing_data()
    
    # Ask user if they want to proceed
    response = input("\n❓ Do you want to proceed with data ingestion? (y/n): ").lower().strip()
    
    if response in ['y', 'yes']:
        print("\n🔄 Starting data ingestion...")
        ingest_data()
    else:
        print("❌ Data ingestion cancelled.")

if __name__ == "__main__":
    main()