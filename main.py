"""
main.py - FastAPI application for the NL2SQL Clinic Chatbot.

Provides:
  POST /chat          — Ask a natural-language question, get SQL + results
  GET  /health        — Health-check endpoint
  GET  /              — Vanna 2.0 built-in web UI (via VannaFastAPIServer)
  POST /api/vanna/v2/chat_sse — Streaming chat (auto-registered by Vanna)

Run:  uvicorn main:app --port 8000
"""

import logging
import re
import sqlite3
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from vanna.servers.fastapi import VannaFastAPIServer
from vanna.servers.base import ChatHandler
from vanna.servers.fastapi.routes import register_chat_routes

from vanna_setup import get_agent, get_agent_memory, DB_PATH

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger("nl2sql")

# ---------------------------------------------------------------------------
# SQL Validation  (Step 7)
# ---------------------------------------------------------------------------

# Dangerous patterns — reject immediately
_FORBIDDEN_PATTERNS = re.compile(
    r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|TRUNCATE|EXEC|EXECUTE|"
    r"xp_|sp_|GRANT|REVOKE|SHUTDOWN|MERGE|REPLACE)\b",
    re.IGNORECASE,
)

# System table access
_SYSTEM_TABLE_PATTERN = re.compile(
    r"\b(sqlite_master|sqlite_schema|sqlite_temp_master|"
    r"information_schema|pg_catalog|sys\.)\b",
    re.IGNORECASE,
)


def validate_sql(sql: str) -> tuple[bool, str]:
    """
    Validate that *sql* is a safe SELECT-only query.

    Returns:
        (is_valid, error_message)
    """
    stripped = sql.strip().rstrip(";").strip()

    if not stripped:
        return False, "Empty SQL query."

    # Must start with SELECT or WITH (CTEs)
    first_word = stripped.split()[0].upper()
    if first_word not in ("SELECT", "WITH"):
        return False, f"Only SELECT queries are allowed. Got: {first_word}"

    if _FORBIDDEN_PATTERNS.search(stripped):
        return False, "Query contains forbidden keywords (INSERT/UPDATE/DELETE/DROP/...)."

    if _SYSTEM_TABLE_PATTERN.search(stripped):
        return False, "Access to system tables is not allowed."

    return True, ""


# ---------------------------------------------------------------------------
# Request / Response models  (for the custom /chat endpoint)
# ---------------------------------------------------------------------------


class ChatRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000)


class ChatResponse(BaseModel):
    message: str
    sql_query: str | None = None
    columns: list[str] = []
    rows: list[list[Any]] = []
    row_count: int = 0
    chart: dict | None = None
    chart_type: str | None = None


# ---------------------------------------------------------------------------
# Build the FastAPI app
# ---------------------------------------------------------------------------

agent = get_agent()

# Use VannaFastAPIServer to get the built-in streaming endpoint & web UI
server = VannaFastAPIServer(agent)
app = server.create_app()

# Add CORS (already added by VannaFastAPIServer, but ensure * is set)
# VannaFastAPIServer sets CORS by default; we keep this explicit for clarity.

# ---------------------------------------------------------------------------
# GET /health
# ---------------------------------------------------------------------------


@app.get("/health")
async def health():
    """Health-check: DB connectivity + memory count."""
    db_status = "connected"
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.execute("SELECT 1")
        conn.close()
    except Exception:
        db_status = "disconnected"

    memory = get_agent_memory()
    # DemoAgentMemory stores items in _memories list
    memory_count = len(memory._memories)

    return {
        "status": "ok",
        "database": db_status,
        "agent_memory_items": memory_count,
    }


# ---------------------------------------------------------------------------
# POST /chat  — Custom endpoint (Option B from the assignment)
# ---------------------------------------------------------------------------


@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    """
    Accept a natural-language question, generate SQL via Vanna 2.0 Agent,
    validate the SQL, run it against clinic.db, and return results.
    """
    question = req.question.strip()
    logger.info("Question: %s", question)

    # 1. Ask the agent to generate SQL ---------------------------------
    try:
        from vanna.core.user import RequestContext

        request_context = RequestContext(metadata={})

        # send_message is an async generator of UiComponents
        components = []
        async for component in agent.send_message(
            request_context=request_context,
            message=question,
        ):
            components.append(component)
    except Exception as exc:
        logger.exception("Agent error")
        raise HTTPException(status_code=500, detail=f"Agent error: {exc}") from exc

    # 2. Extract SQL from the collected components ----------------------
    sql_query = _extract_sql_from_components(components)

    if not sql_query:
        return ChatResponse(
            message=_extract_text_from_components(components),
            sql_query=None,
        )

    # 3. Validate SQL --------------------------------------------------
    valid, err = validate_sql(sql_query)
    if not valid:
        logger.warning("SQL validation failed: %s | SQL: %s", err, sql_query)
        return ChatResponse(
            message=f"SQL validation failed: {err}",
            sql_query=sql_query,
        )

    # 4. Execute SQL ---------------------------------------------------
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cur = conn.execute(sql_query)
        raw_rows = cur.fetchall()
        columns = [desc[0] for desc in cur.description] if cur.description else []
        rows = [list(r) for r in raw_rows]
        conn.close()
    except Exception as exc:
        logger.exception("Database error")
        return ChatResponse(
            message=f"Database error: {exc}",
            sql_query=sql_query,
        )

    if not rows:
        return ChatResponse(
            message="Query executed successfully but returned no data.",
            sql_query=sql_query,
            columns=columns,
            rows=[],
            row_count=0,
        )

    # 5. Build chart (best-effort) ------------------------------------
    chart, chart_type = _build_chart(columns, rows)

    # 6. Build summary text -------------------------------------------
    summary = f"Query returned {len(rows)} row(s) with columns: {', '.join(columns)}."

    return ChatResponse(
        message=summary,
        sql_query=sql_query,
        columns=columns,
        rows=rows,
        row_count=len(rows),
        chart=chart,
        chart_type=chart_type,
    )


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------


def _extract_sql_from_components(components: list) -> str | None:
    """Extract SQL string from a list of UiComponents returned by the agent."""
    for comp in components:
        # Check rich_component metadata for SQL
        rich = getattr(comp, "rich_component", None)
        if rich is not None:
            # DataFrameComponent or StatusCardComponent may carry metadata
            metadata = getattr(rich, "metadata", None)
            if isinstance(metadata, dict):
                for key in ("sql", "sql_query"):
                    if key in metadata:
                        return metadata[key]
                # Check if arguments contain sql
                if "sql" in metadata:
                    return metadata["sql"]

        # Check simple_component text for SQL
        simple = getattr(comp, "simple_component", None)
        if simple is not None:
            text = getattr(simple, "text", "")
            if text:
                sql = _sql_from_codeblock(text)
                if sql:
                    return sql

        # Check rich_component content for SQL code blocks
        if rich is not None:
            content = getattr(rich, "content", "")
            if isinstance(content, str) and content:
                sql = _sql_from_codeblock(content)
                if sql:
                    return sql

    return None


def _sql_from_codeblock(text: str) -> str | None:
    """Extract SQL from markdown ```sql ... ``` blocks or bare SELECT statements."""
    # Markdown code blocks
    match = re.search(r"```sql\s*\n?(.*?)```", text, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip()
    # Bare SELECT
    match = re.search(r"(SELECT\s.+?;)", text, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip().rstrip(";")
    return None


def _extract_text_from_components(components: list) -> str:
    """Pull human-readable text from UiComponents."""
    parts = []
    for comp in components:
        # Try rich_component content
        rich = getattr(comp, "rich_component", None)
        if rich is not None:
            content = getattr(rich, "content", None)
            if isinstance(content, str) and content:
                parts.append(content)
                continue
            message = getattr(rich, "message", None)
            if isinstance(message, str) and message:
                parts.append(message)
                continue

        # Try simple_component text
        simple = getattr(comp, "simple_component", None)
        if simple is not None:
            text = getattr(simple, "text", "")
            if text:
                parts.append(text)

    return "\n".join(parts) if parts else "No response generated."


def _build_chart(columns: list[str], rows: list[list]) -> tuple[dict | None, str | None]:
    """Best-effort Plotly chart from query results."""
    try:
        import plotly.express as px
        import pandas as pd

        df = pd.DataFrame(rows, columns=columns)

        if len(columns) < 2:
            return None, None

        # Heuristic: first column = labels, second = values
        x_col, y_col = columns[0], columns[1]

        # Pick chart type based on data
        if df[y_col].dtype in ("int64", "float64") and len(df) <= 30:
            fig = px.bar(df, x=x_col, y=y_col, title=f"{y_col} by {x_col}")
            chart_type = "bar"
        elif df[y_col].dtype in ("int64", "float64"):
            fig = px.line(df, x=x_col, y=y_col, title=f"{y_col} over {x_col}")
            chart_type = "line"
        else:
            return None, None

        return fig.to_dict(), chart_type
    except Exception:
        return None, None


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="localhost", port=8000, reload=True)
