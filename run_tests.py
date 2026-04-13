"""
Run all 20 test questions with retry logic for Gemini rate limits.

Gemini free tier: 20 requests/minute, but Vanna uses multiple LLM calls per
question. This script retries on rate-limit (429) errors with backoff.

Usage:
    python run_tests.py              # run all 20
    python run_tests.py --start 4    # resume from Q4
"""
import requests
import json
import time
import sys
import os

questions = [
    "How many patients do we have?",
    "List all doctors and their specializations",
    "Show me appointments for last month",
    "Which doctor has the most appointments?",
    "What is the total revenue?",
    "Show revenue by doctor",
    "How many cancelled appointments last quarter?",
    "Top 5 patients by spending",
    "Average treatment cost by specialization",
    "Show monthly appointment count for the past 6 months",
    "Which city has the most patients?",
    "List patients who visited more than 3 times",
    "Show unpaid invoices",
    "What percentage of appointments are no-shows?",
    "Show the busiest day of the week for appointments",
    "Revenue trend by month",
    "Average appointment duration by doctor",
    "List patients with overdue invoices",
    "Compare revenue between departments",
    "Show patient registration trend by month",
]

url = "http://127.0.0.1:8000/chat"
RESULTS_FILE = "test_results.json"
DELAY_BETWEEN = 5  # seconds between questions (Groq has generous limits)
MAX_RETRIES = 3
RETRY_WAIT = 15  # seconds to wait on 429 before retrying

# Load previous results if resuming
start_q = 1
if "--start" in sys.argv:
    start_q = int(sys.argv[sys.argv.index("--start") + 1])

results = []
if start_q > 1 and os.path.exists(RESULTS_FILE):
    with open(RESULTS_FILE) as f:
        results = json.load(f)
    results = [r for r in results if r["q"] < start_q]
    print(f"Loaded {len(results)} previous results, resuming from Q{start_q}")


def run_query(question, retries=MAX_RETRIES):
    """Send a question with retry on rate-limit errors."""
    for attempt in range(retries):
        try:
            r = requests.post(url, json={"question": question}, timeout=180)
            data = r.json()
            msg = data.get("message", "")
            # Check if the response indicates a rate-limit error
            if "rate" in msg.lower() or "quota" in msg.lower() or "429" in msg:
                if attempt < retries - 1:
                    print(f"  Rate limited, waiting {RETRY_WAIT}s (attempt {attempt+1}/{retries})...")
                    time.sleep(RETRY_WAIT)
                    continue
            return data
        except requests.exceptions.Timeout:
            if attempt < retries - 1:
                print(f"  Timeout, retrying in {RETRY_WAIT}s (attempt {attempt+1}/{retries})...")
                time.sleep(RETRY_WAIT)
                continue
            return {"message": "Request timed out after retries", "sql_query": None,
                    "row_count": 0, "columns": [], "rows": []}
        except Exception as e:
            return {"message": str(e), "sql_query": None,
                    "row_count": 0, "columns": [], "rows": []}
    return {"message": "Failed after max retries (rate limited)",
            "sql_query": None, "row_count": 0, "columns": [], "rows": []}


for i, q in enumerate(questions, 1):
    if i < start_q:
        continue

    print(f"\n===== Q{i}: {q} =====")
    data = run_query(q)

    sql = data.get("sql_query") or "None"
    msg = data.get("message", "")
    row_count = data.get("row_count", 0)
    cols = data.get("columns", [])
    rows = data.get("rows", [])

    print(f"SQL: {sql}")
    print(f"Message: {msg}")
    print(f"Rows: {row_count}, Cols: {cols}")
    if rows and len(rows) <= 5:
        for row in rows:
            print(f"  {row}")
    elif rows:
        for row in rows[:3]:
            print(f"  {row}")
        print(f"  ... ({row_count} total)")

    results.append({
        "q": i, "question": q, "sql": sql, "message": msg,
        "row_count": row_count, "columns": cols, "status": 200
    })

    # Save incrementally
    with open(RESULTS_FILE, "w") as f:
        json.dump(results, f, indent=2)

    if i < len(questions):
        print(f"  Waiting {DELAY_BETWEEN}s before next query...")
        time.sleep(DELAY_BETWEEN)

print("\n\n===== SUMMARY =====")
for r in results:
    has_sql = r["sql"] not in ("None", "ERROR", "N/A")
    status = "OK" if has_sql and r["row_count"] > 0 else ("SQL_ONLY" if has_sql else "FAIL")
    sql_preview = r["sql"][:100] if r["sql"] else "None"
    print(f'Q{r["q"]:2d}: {status:8s} | rows={r["row_count"]:4d} | SQL={sql_preview}')

passed = sum(1 for r in results if r["sql"] not in ("None", "ERROR", "N/A") and r["row_count"] > 0)
print(f"\nScore: {passed} / {len(results)}")
print(f"Results saved to {RESULTS_FILE}")
