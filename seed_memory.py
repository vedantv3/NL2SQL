"""
seed_memory.py - Pre-seeds the Vanna 2.0 DemoAgentMemory with 15+ known-good
question-SQL pairs so the agent has a head start.

Run:  python seed_memory.py  (after setup_database.py)
"""

import asyncio
from vanna.core.user import User
from vanna.core.tool import ToolContext

from vanna_setup import get_agent_memory

# ---------------------------------------------------------------------------
# 15+ curated Q&A pairs covering every required category
# ---------------------------------------------------------------------------

SEED_PAIRS: list[dict] = [
    # ── Patient queries ──────────────────────────────────────
    {
        "question": "How many patients do we have?",
        "tool_name": "run_sql",
        "args": {"sql": "SELECT COUNT(*) AS total_patients FROM patients"},
    },
    {
        "question": "List all patients from New York",
        "tool_name": "run_sql",
        "args": {
            "sql": "SELECT first_name, last_name, email, phone FROM patients WHERE city = 'New York'"
        },
    },
    {
        "question": "How many male and female patients do we have?",
        "tool_name": "run_sql",
        "args": {
            "sql": "SELECT gender, COUNT(*) AS count FROM patients GROUP BY gender"
        },
    },
    {
        "question": "Which city has the most patients?",
        "tool_name": "run_sql",
        "args": {
            "sql": "SELECT city, COUNT(*) AS patient_count FROM patients GROUP BY city ORDER BY patient_count DESC LIMIT 1"
        },
    },
    # ── Doctor queries ───────────────────────────────────────
    {
        "question": "List all doctors and their specializations",
        "tool_name": "run_sql",
        "args": {
            "sql": "SELECT name, specialization, department FROM doctors ORDER BY name"
        },
    },
    {
        "question": "Which doctor has the most appointments?",
        "tool_name": "run_sql",
        "args": {
            "sql": (
                "SELECT d.name, COUNT(a.id) AS appointment_count "
                "FROM doctors d JOIN appointments a ON d.id = a.doctor_id "
                "GROUP BY d.id ORDER BY appointment_count DESC LIMIT 1"
            )
        },
    },
    # ── Appointment queries ──────────────────────────────────
    {
        "question": "Show me appointments for last month",
        "tool_name": "run_sql",
        "args": {
            "sql": (
                "SELECT a.id, p.first_name || ' ' || p.last_name AS patient, "
                "d.name AS doctor, a.appointment_date, a.status "
                "FROM appointments a "
                "JOIN patients p ON p.id = a.patient_id "
                "JOIN doctors d ON d.id = a.doctor_id "
                "WHERE a.appointment_date >= date('now', '-1 month') "
                "ORDER BY a.appointment_date DESC"
            )
        },
    },
    {
        "question": "How many cancelled appointments last quarter?",
        "tool_name": "run_sql",
        "args": {
            "sql": (
                "SELECT COUNT(*) AS cancelled_count FROM appointments "
                "WHERE status = 'Cancelled' "
                "AND appointment_date >= date('now', '-3 months')"
            )
        },
    },
    {
        "question": "Show monthly appointment count for the past 6 months",
        "tool_name": "run_sql",
        "args": {
            "sql": (
                "SELECT strftime('%Y-%m', appointment_date) AS month, "
                "COUNT(*) AS appointment_count FROM appointments "
                "WHERE appointment_date >= date('now', '-6 months') "
                "GROUP BY month ORDER BY month"
            )
        },
    },
    # ── Financial queries ────────────────────────────────────
    {
        "question": "What is the total revenue?",
        "tool_name": "run_sql",
        "args": {
            "sql": "SELECT SUM(total_amount) AS total_revenue FROM invoices"
        },
    },
    {
        "question": "Show revenue by doctor",
        "tool_name": "run_sql",
        "args": {
            "sql": (
                "SELECT d.name, SUM(i.total_amount) AS total_revenue "
                "FROM invoices i "
                "JOIN appointments a ON a.patient_id = i.patient_id "
                "JOIN doctors d ON d.id = a.doctor_id "
                "GROUP BY d.name ORDER BY total_revenue DESC"
            )
        },
    },
    {
        "question": "Show unpaid invoices",
        "tool_name": "run_sql",
        "args": {
            "sql": (
                "SELECT i.id, p.first_name || ' ' || p.last_name AS patient, "
                "i.total_amount, i.paid_amount, i.status "
                "FROM invoices i JOIN patients p ON p.id = i.patient_id "
                "WHERE i.status IN ('Pending', 'Overdue') "
                "ORDER BY i.total_amount DESC"
            )
        },
    },
    {
        "question": "Average treatment cost by specialization",
        "tool_name": "run_sql",
        "args": {
            "sql": (
                "SELECT d.specialization, ROUND(AVG(t.cost), 2) AS avg_cost "
                "FROM treatments t "
                "JOIN appointments a ON a.id = t.appointment_id "
                "JOIN doctors d ON d.id = a.doctor_id "
                "GROUP BY d.specialization ORDER BY avg_cost DESC"
            )
        },
    },
    # ── Time-based queries ───────────────────────────────────
    {
        "question": "Revenue trend by month",
        "tool_name": "run_sql",
        "args": {
            "sql": (
                "SELECT strftime('%Y-%m', invoice_date) AS month, "
                "SUM(total_amount) AS revenue FROM invoices "
                "GROUP BY month ORDER BY month"
            )
        },
    },
    {
        "question": "Show patient registration trend by month",
        "tool_name": "run_sql",
        "args": {
            "sql": (
                "SELECT strftime('%Y-%m', registered_date) AS month, "
                "COUNT(*) AS new_patients FROM patients "
                "GROUP BY month ORDER BY month"
            )
        },
    },
    # ── Extra pairs for better coverage ──────────────────────
    {
        "question": "Top 5 patients by spending",
        "tool_name": "run_sql",
        "args": {
            "sql": (
                "SELECT p.first_name, p.last_name, SUM(i.total_amount) AS total_spending "
                "FROM patients p JOIN invoices i ON p.id = i.patient_id "
                "GROUP BY p.id ORDER BY total_spending DESC LIMIT 5"
            )
        },
    },
    {
        "question": "List patients who visited more than 3 times",
        "tool_name": "run_sql",
        "args": {
            "sql": (
                "SELECT p.first_name, p.last_name, COUNT(a.id) AS visit_count "
                "FROM patients p JOIN appointments a ON p.id = a.patient_id "
                "GROUP BY p.id HAVING visit_count > 3 ORDER BY visit_count DESC"
            )
        },
    },
    {
        "question": "What percentage of appointments are no-shows?",
        "tool_name": "run_sql",
        "args": {
            "sql": (
                "SELECT ROUND(100.0 * SUM(CASE WHEN status = 'No-Show' THEN 1 ELSE 0 END) "
                "/ COUNT(*), 2) AS no_show_percentage FROM appointments"
            )
        },
    },
    {
        "question": "Show the busiest day of the week for appointments",
        "tool_name": "run_sql",
        "args": {
            "sql": (
                "SELECT CASE CAST(strftime('%w', appointment_date) AS INTEGER) "
                "WHEN 0 THEN 'Sunday' WHEN 1 THEN 'Monday' WHEN 2 THEN 'Tuesday' "
                "WHEN 3 THEN 'Wednesday' WHEN 4 THEN 'Thursday' "
                "WHEN 5 THEN 'Friday' WHEN 6 THEN 'Saturday' END AS day_of_week, "
                "COUNT(*) AS appointment_count FROM appointments "
                "GROUP BY day_of_week ORDER BY appointment_count DESC"
            )
        },
    },
    {
        "question": "Average appointment duration by doctor",
        "tool_name": "run_sql",
        "args": {
            "sql": (
                "SELECT d.name, ROUND(AVG(t.duration_minutes), 1) AS avg_duration "
                "FROM doctors d "
                "JOIN appointments a ON d.id = a.doctor_id "
                "JOIN treatments t ON a.id = t.appointment_id "
                "GROUP BY d.id ORDER BY avg_duration DESC"
            )
        },
    },
]


async def seed():
    """Seed agent memory with curated Q&A pairs."""
    memory = get_agent_memory()

    # Build a minimal ToolContext for seeding
    demo_user = User(
        id="seed_user",
        email="seed@clinic.local",
        group_memberships=["admin"],
    )
    ctx = ToolContext(
        user=demo_user,
        conversation_id="seed-conversation",
        request_id="seed-request",
        agent_memory=memory,
        metadata={},
    )

    count = 0
    for pair in SEED_PAIRS:
        await memory.save_tool_usage(
            question=pair["question"],
            tool_name=pair["tool_name"],
            args=pair["args"],
            context=ctx,
            success=True,
        )
        count += 1

    print(f"Seeded {count} question-SQL pairs into agent memory.")


if __name__ == "__main__":
    asyncio.run(seed())
