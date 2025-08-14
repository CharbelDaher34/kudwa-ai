from __future__ import annotations

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy import create_engine
from sqlmodel import SQLModel

from routers.routes import router


@asynccontextmanager
async def lifespan(app: FastAPI):
    from db import DATABASE_URL, engine, SessionLocal

    # Store DB engine/session factory in app state
    app.state.engine = engine
    app.state.SessionLocal = SessionLocal

    # Optional: Drop and recreate schema if needed
    # from sqlalchemy import text
    # with engine.begin() as conn:
    #     conn.exec_driver_sql("DROP SCHEMA IF EXISTS public CASCADE;")
    #     conn.exec_driver_sql("CREATE SCHEMA public;")

    # Create tables
    SQLModel.metadata.create_all(engine)

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
    uvicorn.run("main:app", host="0.0.0.0", port=8430, reload=True)
