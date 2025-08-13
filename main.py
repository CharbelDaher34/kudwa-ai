"""
Schema-agnostic Text-to-SQL service

Run:
  pip install -U fastapi uvicorn sqlalchemy sqlglot pydantic sentence-transformers faiss-cpu openai python-dotenv

Env:
  DATABASE_URL=postgresql+psycopg2://user:pass@host:5432/dbname   # or sqlite:///example.db
  LLM_MODEL=gpt-4o-mini                                          # any OpenAI-compatible chat model
  OPENAI_API_KEY=...                                             # required if using OpenAI-compatible
  OPENAI_BASE_URL=...                                            # optional; for local/Ollama/OpenRouter, etc.

Start:
  uvicorn main:app --reload --port 8000

Test:
  curl -X POST http://localhost:8000/ask \
    -H 'Content-Type: application/json' \
    -d '{"question":"total revenue by month in 2024"}'
"""

from __future__ import annotations

import os
from fastapi import FastAPI
from sqlalchemy import create_engine

from routers.routes import router


app = FastAPI(title="Schema-Agnostic Text-to-SQL")


@app.on_event("startup")
def _startup():
    from db import DATABASE_URL, engine, SessionLocal
    from sqlmodel import SQLModel
    
    app.state.engine = engine
    app.state.SessionLocal = SessionLocal
    
    # First drop and recreate schema, then create tables
    # from sqlalchemy import text
    # with engine.begin() as conn:
    #     conn.exec_driver_sql("DROP SCHEMA IF EXISTS public CASCADE;")
    #     conn.exec_driver_sql("CREATE SCHEMA public;")
    
    # Create tables after schema is clean
    SQLModel.metadata.create_all(engine)

app.include_router(router)

if __name__ == "__main__":
  import uvicorn
  uvicorn.run("main:app", host="0.0.0.0", port=8430, reload=True)

