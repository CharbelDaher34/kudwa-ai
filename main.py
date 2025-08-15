from __future__ import annotations

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy import create_engine
from sqlmodel import SQLModel
from sqlmodel import select, func

from routers.routes import router


@asynccontextmanager
async def lifespan(app: FastAPI):
    from db import DATABASE_URL, engine, SessionLocal, get_db_session
    from data.models import FinancialStatement
    import subprocess
    import sys

    # Store DB engine/session factory in app state
    app.state.engine = engine
    app.state.SessionLocal = SessionLocal

    # Optional: Drop and recreate schema if needed
    # from sqlalchemy import text
    # with engine.begin() as conn:
    #     conn.exec_driver_sql("DROP SCHEMA IF EXISTS public CASCADE;")
    #     conn.exec_driver_sql("CREATE SCHEMA public;")

    # Create tables
    # SQLModel.metadata.drop_all(engine)
    
    SQLModel.metadata.create_all(engine)
    
    # Check if database is empty and run ingest if needed
    print("Checking if database has financial statement data...")
    try:
        with get_db_session() as session:
            count = session.exec(select(func.count()).select_from(FinancialStatement)).one()
            print(f"Found {count} financial statement records in database")
            
            if count == 0:
                print("Database is empty. Running data ingestion...")
                # Run the ingest script
                result = subprocess.run([sys.executable, "ingest.py"], 
                                      capture_output=True, text=True, cwd=os.getcwd())
                
                if result.returncode == 0:
                    print("Data ingestion completed successfully!")
                    print(result.stdout)
                else:
                    print(f"Data ingestion failed with error: {result.stderr}")
                    print(f"Return code: {result.returncode}")
            else:
                print("Database already contains financial statement data. Skipping ingestion.")
                
    except Exception as e:
        print(f"Error checking database or running ingestion: {e}")

    # Startup phase
    yield

    # Shutdown phase (close connections)
    engine.dispose()


app = FastAPI(
    title="Schema-Agnostic Text-to-SQL",
    lifespan=lifespan
)

app.include_router(router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8430)#, reload=True)
