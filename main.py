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
    db_url = os.getenv("DATABASE_URL", "sqlite:///example.db")
    engine = create_engine(db_url, pool_pre_ping=True)

    app.state.engine = engine



app.include_router(router)


