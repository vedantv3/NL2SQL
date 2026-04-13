"""
vanna_setup.py - Initializes the Vanna 2.0 Agent with all required components.

Components:
  1. OpenAILlmService   — LLM provider (Groq, free tier, OpenAI-compatible)
  2. SqliteRunner       — Executes SQL against clinic.db
  3. ToolRegistry       — Registers all tools the agent can use
  4. DemoAgentMemory    — In-memory learning system (Vanna 2.0 memory)
  5. UserResolver       — Simple default-user resolver
  6. Agent              — Orchestrates everything
"""

import os
from dotenv import load_dotenv

# Vanna 2.0 core
from vanna import Agent, AgentConfig
from vanna.core.registry import ToolRegistry
from vanna.core.user import UserResolver, User, RequestContext
from vanna.core.system_prompt import DefaultSystemPromptBuilder

# Tools
from vanna.tools import RunSqlTool, VisualizeDataTool
from vanna.tools.agent_memory import (
    SaveQuestionToolArgsTool,
    SearchSavedCorrectToolUsesTool,
)

# Integrations
from vanna.integrations.sqlite import SqliteRunner
from vanna.integrations.local.agent_memory import DemoAgentMemory
from vanna.integrations.openai import OpenAILlmService

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

load_dotenv()  # reads .env

DB_PATH = os.getenv("DB_PATH", "clinic.db")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

if not GROQ_API_KEY:
    raise EnvironmentError(
        "GROQ_API_KEY is not set. "
        "Create a .env file with GROQ_API_KEY=your-key "
        "or export it as an environment variable."
    )


# ---------------------------------------------------------------------------
# 1. LLM Service — Groq (free tier, OpenAI-compatible API)
# ---------------------------------------------------------------------------

llm_service = OpenAILlmService(
    model="llama-3.3-70b-versatile",
    api_key=GROQ_API_KEY,
    base_url="https://api.groq.com/openai/v1",
)


# ---------------------------------------------------------------------------
# 2. SQL Runner — SQLite (built-in, no installation needed)
# ---------------------------------------------------------------------------

sql_runner = SqliteRunner(DB_PATH)


# ---------------------------------------------------------------------------
# 3. Agent Memory — DemoAgentMemory (in-RAM, no external DB)
# ---------------------------------------------------------------------------

agent_memory = DemoAgentMemory()


# ---------------------------------------------------------------------------
# 4. Tool Registry — register all required tools
# ---------------------------------------------------------------------------

tool_registry = ToolRegistry()

# Core tools
tool_registry.register_local_tool(RunSqlTool(sql_runner=sql_runner), access_groups=["admin", "user"])
tool_registry.register_local_tool(VisualizeDataTool(), access_groups=["admin", "user"])

# Agent-memory tools  (learn from successful interactions)
tool_registry.register_local_tool(SaveQuestionToolArgsTool(), access_groups=["admin"])
tool_registry.register_local_tool(SearchSavedCorrectToolUsesTool(), access_groups=["admin", "user"])


# ---------------------------------------------------------------------------
# 5. User Resolver — simple default user (no auth in demo)
# ---------------------------------------------------------------------------

class SimpleUserResolver(UserResolver):
    """Resolves every request to a default demo user."""

    async def resolve_user(self, request_context: RequestContext) -> User:
        return User(
            id="demo_user",
            email="demo@clinic.local",
            group_memberships=["admin", "user"],
        )


# ---------------------------------------------------------------------------
# 6. Assemble the Agent
# ---------------------------------------------------------------------------

# Custom system prompt with clinic-specific context
CLINIC_SYSTEM_PROMPT = (
    "You are a helpful clinic data assistant. The database is a SQLite "
    "clinic management system with the following tables:\n"
    "- patients (id, first_name, last_name, email, phone, date_of_birth, gender, city, registered_date)\n"
    "- doctors (id, name, specialization, department, phone)\n"
    "- appointments (id, patient_id, doctor_id, appointment_date, status, notes)\n"
    "- treatments (id, appointment_id, treatment_name, cost, duration_minutes)\n"
    "- invoices (id, patient_id, invoice_date, total_amount, paid_amount, status)\n\n"
    "Always generate SELECT-only SQL. Never modify data.\n"
    "When results contain numeric data suitable for charting, also call "
    "the visualize_data tool to produce a Plotly chart.\n"
    "Use SQLite date functions like date(), strftime(), etc."
)

agent = Agent(
    llm_service=llm_service,
    tool_registry=tool_registry,
    user_resolver=SimpleUserResolver(),
    agent_memory=agent_memory,
    system_prompt_builder=DefaultSystemPromptBuilder(base_prompt=CLINIC_SYSTEM_PROMPT),
    config=AgentConfig(),
)


def get_agent() -> Agent:
    """Return the configured agent singleton."""
    return agent


def get_agent_memory() -> DemoAgentMemory:
    """Return the agent memory instance (used by seed_memory.py)."""
    return agent_memory
