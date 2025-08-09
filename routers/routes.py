from __future__ import annotations

from typing import List, Dict

from fastapi import APIRouter, HTTPException, Request
from sqlalchemy import text
from sqlalchemy.engine import Engine

from services import (
    AskRequest,
    AskResponse,
    SchemaGraph,
    SchemaIndex,
    _dialect_from_engine,
    bfs_join_path,
    build_join_skeleton,
    build_schema_snippet,
    build_prompt,
    call_llm_sql,
    guard_sql,
)


router = APIRouter()


@router.get("/health")
def health(request: Request):
    try:
        eng: Engine = request.app.state.engine
        with eng.connect() as c:
            c.execute(text("SELECT 1"))
        return {"status": "ok"}
    except Exception as e:
        return {"status": "error", "detail": str(e)}


@router.post("/ask", response_model=AskResponse)
def ask(request: Request, req: AskRequest):
    engine: Engine = request.app.state.engine
    graph: SchemaGraph = request.app.state.graph
    sindex: SchemaIndex = request.app.state.sindex

    dialect = _dialect_from_engine(engine)

    # 1) Retrieve relevant columns → tables
    col_cands = sindex.search(req.question, k=req.k)
    tables_ranked: List[str] = []
    for t, c in col_cands:
        if t not in tables_ranked:
            tables_ranked.append(t)
    tables = tables_ranked[: max(1, req.max_tables)]

    if not tables:
        raise HTTPException(400, detail="No tables detected")

    # 2) Build join plan
    joins = bfs_join_path(graph, tables)
    join_skeleton = build_join_skeleton(joins)

    # 3) Allowed columns: all columns of selected tables (keeps LLM inside rails)
    allowed: Dict[str, List[str]] = {}
    for t in tables:
        allowed[t] = [c.name for c in graph.columns if c.table == t]

    # 4) Build schema text (with samples)
    schema_text = build_schema_snippet(graph, tables)

    # 5) Prompt & generate
    prompt = build_prompt(req.question, dialect, allowed, schema_text, join_skeleton)

    attempted_repairs = 0
    warnings: List[str] = []

    for attempt in range(2):  # one try + one self-repair
        try:
            sql_raw = call_llm_sql(prompt)
            sql_norm = guard_sql(sql_raw, dialect)
            # 6) Execute
            with engine.connect() as conn:
                rs = conn.execute(text(sql_norm))
                cols = list(rs.keys())
                rows = [list(r) for r in rs.fetchall()[:200]]
            return AskResponse(sql=sql_norm, columns=cols, rows=rows, attempted_repairs=attempted_repairs, warnings=warnings)
        except Exception as e:
            attempted_repairs += 1
            # enrich prompt with last error and full allowed schema to help repair
            prompt = (
                prompt
                + f"\n\nThe previous SQL caused this {dialect} error: {str(e)}. "
                  "Fix the SQL. Return only a single SELECT that adheres to the allowed tables/columns and joins."
            )
            last_err = str(e)
    # If we got here, fail gracefully
    raise HTTPException(422, detail={"message": "Failed to generate/execute SQL after retries.", "last_error": last_err, "prompt": prompt[-1500:]})


