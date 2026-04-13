# NL2SQL Clinic Chatbot — Vanna 2.0 + FastAPI

An AI-powered Natural Language to SQL system that lets users ask questions in plain English and get results from a clinic management database — without writing any SQL.

**Example:**
> **User:** "Show me the top 5 patients by total spending"
> **System:** Generates SQL, executes it, and returns results + a summary + chart.

---

## Tech Stack

| Technology | Version | Purpose |
|---|---|---|
| Python | 3.10+ | Backend language |
| Vanna | 2.0.x | AI Agent for NL2SQL |
| FastAPI | Latest | REST API framework |
| SQLite | Built-in | Database (no installation needed) |
| Google Gemini | gemini-2.5-flash | LLM for SQL generation **(free tier)** |
| Plotly | Latest | Chart generation |

### LLM Provider Choice: **Google Gemini (Option A)**

This project uses **Google Gemini** via AI Studio (free tier). Get your API key at: <https://aistudio.google.com/apikey>

---

## Architecture

```
User Question (English)
        │
        ▼
   FastAPI Backend
        │
        ▼
   Vanna 2.0 Agent
   (GeminiLlmService + RunSqlTool + DemoAgentMemory)
        │
        ▼
   SQL Validation (SELECT only, no dangerous queries)
        │
        ▼
   Database Execution (SQLite via built-in SqliteRunner)
        │
        ▼
   Results + Summary + Chart returned to user
```

**Key Components:**

| File | Purpose |
|---|---|
| `setup_database.py` | Creates clinic.db with schema + 200 patients, 15 doctors, 500 appointments, 350 treatments, 300 invoices |
| `vanna_setup.py` | Initialises the Vanna 2.0 Agent (LLM, ToolRegistry, Memory, UserResolver) |
| `seed_memory.py` | Pre-seeds 20 Q&A pairs into DemoAgentMemory |
| `main.py` | FastAPI app with `/chat`, `/health`, and Vanna built-in streaming endpoints |

---

## Setup Instructions

### 1. Clone the repository

```bash
git clone https://github.com/vedantv3/nl2sql-clinic-chatbot.git
cd nl2sql-clinic-chatbot
```

### 2. Create a virtual environment (recommended)

```bash
python -m venv venv
# Windows
venv\Scripts\activate
# macOS / Linux
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Set up the API key

Copy the example env file and add your Gemini key:

```bash
cp .env.example .env
# Edit .env and replace 'your-google-api-key-here' with your actual key
```

### 5. Create the database

```bash
python setup_database.py
```

Expected output:
```
Created 200 patients, 15 doctors, 500 appointments, 350 treatments, 300 invoices.
Database saved to clinic.db
```

### 6. Seed the agent memory

```bash
python seed_memory.py
```

Expected output:
```
Seeded 20 question-SQL pairs into agent memory.
```

### 7. Start the API server

```bash
uvicorn main:app --port 8000
```

The app will be available at **http://localhost:8000**.

### One-liner (full setup)

```bash
pip install -r requirements.txt && python setup_database.py && python seed_memory.py && uvicorn main:app --port 8000
```

---

## API Documentation

### `POST /chat`

Ask a natural-language question about the clinic database.

**Request:**
```json
{
  "question": "Show me the top 5 patients by total spending"
}
```

**Response:**
```json
{
  "message": "Query returned 5 row(s) with columns: first_name, last_name, total_spending.",
  "sql_query": "SELECT p.first_name, p.last_name, SUM(i.total_amount) AS total_spending FROM patients p JOIN invoices i ON p.id = i.patient_id GROUP BY p.id ORDER BY total_spending DESC LIMIT 5",
  "columns": ["first_name", "last_name", "total_spending"],
  "rows": [["John", "Smith", 4500], ["Jane", "Doe", 3200]],
  "row_count": 5,
  "chart": { "data": [], "layout": {} },
  "chart_type": "bar"
}
```

**Error responses:**
- SQL validation failure → `{ "message": "SQL validation failed: ...", "sql_query": "..." }`
- No results → `{ "message": "Query executed successfully but returned no data." }`

### `GET /health`

```json
{
  "status": "ok",
  "database": "connected",
  "agent_memory_items": 20
}
```

### `POST /api/vanna/v2/chat_sse`

Vanna 2.0 built-in streaming endpoint (SSE). Used by the `<vanna-chat>` web component at `GET /`.

### `GET /`

Vanna 2.0 built-in web UI — an interactive chat interface.

---

## SQL Validation

Before executing any AI-generated SQL, the system validates:

1. **SELECT only** — Rejects INSERT, UPDATE, DELETE, DROP, ALTER, CREATE, TRUNCATE
2. **No dangerous keywords** — Rejects EXEC, xp_, sp_, GRANT, REVOKE, SHUTDOWN
3. **No system tables** — Rejects sqlite_master, information_schema, etc.

If validation fails, an error message is returned instead of executing the query.

---

## Error Handling

| Scenario | Behaviour |
|---|---|
| AI generates invalid SQL | Friendly validation error returned |
| Database query fails | Exception caught, error message returned |
| No results found | "No data found" message returned |
| Empty/too-long question | FastAPI validation error (min 1 char, max 2000) |

---

## Project Structure

```
project/
├── setup_database.py      # Database creation + dummy data
├── seed_memory.py         # Agent memory seeding with 20 Q&A pairs
├── vanna_setup.py         # Vanna 2.0 Agent initialisation
├── main.py                # FastAPI application
├── requirements.txt       # All dependencies
├── .env.example           # Template for environment variables
├── .env                   # Your actual API key (git-ignored)
├── .gitignore             # Git ignore rules
├── README.md              # This file
├── RESULTS.md             # Test results for 20 questions
└── clinic.db              # Generated database file
```

---

## Bonus Features Implemented

- **Chart Generation** — Plotly bar/line charts auto-generated for numeric results
- **Input Validation** — Question length validated (1–2000 chars) via Pydantic
- **SQL Validation** — Comprehensive reject-list for dangerous SQL patterns
- **Structured Logging** — All steps logged with timestamps and severity levels
- **Streaming UI** — Built-in Vanna web component available at `/`

---

## License


