import sqlite3
from datetime import datetime
import os
import json
from typing import List, Dict, Any, Optional

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "scheduled_tasks.db")


def get_connection():
    """Returns a SQLite connection object configured for safe multi-threaded access."""
    conn = sqlite3.connect(DB_PATH, timeout=30.0, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Creates the scheduled_tasks, chat_history, and user_impression tables if they do not exist."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("PRAGMA journal_mode=WAL;")
        cursor.execute("PRAGMA busy_timeout=5000;")

        # 1. Scheduled Tasks Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS scheduled_tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                prompt TEXT NOT NULL,
                run_time TEXT NOT NULL,
                last_run TEXT DEFAULT ''
            )
        """)

        # 2. Multi-turn Conversational History Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS chat_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                user_prompt TEXT NOT NULL,
                agent_response TEXT NOT NULL,
                department_used TEXT DEFAULT 'general_ops',
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 3. User Cognitive Profile & Persona Impression Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_impression_profile (
                id INTEGER PRIMARY KEY,
                user_id TEXT UNIQUE NOT NULL,
                summary_impression TEXT NOT NULL,
                technical_level TEXT DEFAULT 'Expert / Lead Systems Engineer',
                preferred_tone TEXT DEFAULT 'Concise, direct, highly structured with citations',
                key_preferences TEXT DEFAULT '[]',
                active_projects TEXT DEFAULT '[]',
                total_interactions INTEGER DEFAULT 0,
                last_updated DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Initialize default cognitive profile if empty
        cursor.execute("SELECT COUNT(*) as count FROM user_impression_profile WHERE user_id = 'primary_user'")
        if cursor.fetchone()["count"] == 0:
            initial_prefs = json.dumps([
                "Prefers concise, executive, high-density structured answers",
                "Requires markdown hyperlinked citations [Title](URL) over bare URLs",
                "Working on MAK Autonomous Cognitive Core with LangGraph & Electron",
                "Values robust error handling, key failover, and headless architecture"
            ])
            initial_projects = json.dumps([
                "MAK Enterprise AI Agency",
                "LangGraph Multi-Agent Orchestrator",
                "Electron Desktop OS & FastAPI Backend"
            ])
            cursor.execute("""
                INSERT INTO user_impression_profile (
                    id, user_id, summary_impression, technical_level, preferred_tone,
                    key_preferences, active_projects, total_interactions, last_updated
                ) VALUES (
                    1, 'primary_user',
                    'Senior AI Systems Architect & Founder. Decisive, focused on high-performance decoupled systems. Values depth, conciseness, structured deliverables, and zero conversational fluff.',
                    'Expert / Lead Systems Engineer',
                    'Direct, concise, analytical with rich hyperlinked citations and structured metrics',
                    ?, ?, 1, CURRENT_TIMESTAMP
                )
            """, (initial_prefs, initial_projects))

        conn.commit()


# =====================================================================
# Chat History Management
# =====================================================================

def save_chat_turn(session_id: str, user_prompt: str, agent_response: str, department_used: str = "general_ops") -> int:
    """Records a single conversation turn in SQLite database."""
    init_db()
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO chat_history (session_id, user_prompt, agent_response, department_used, timestamp)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
        """, (session_id, user_prompt, agent_response, department_used))
        conn.commit()
        return cursor.lastrowid


def get_recent_chat_history(session_id: str = "default", limit: int = 6) -> List[Dict[str, Any]]:
    """Retrieves recent conversation exchanges for conversational continuity."""
    init_db()
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, session_id, user_prompt, agent_response, department_used, timestamp
            FROM chat_history
            WHERE session_id = ?
            ORDER BY id DESC
            LIMIT ?
        """, (session_id, limit))
        rows = cursor.fetchall()
        # Return in chronological order
        return [dict(row) for row in reversed(rows)]


def clear_chat_history(session_id: Optional[str] = None):
    """Clears conversation history."""
    init_db()
    with get_connection() as conn:
        cursor = conn.cursor()
        if session_id:
            cursor.execute("DELETE FROM chat_history WHERE session_id = ?", (session_id,))
        else:
            cursor.execute("DELETE FROM chat_history")
        conn.commit()


# =====================================================================
# User Cognitive Impression & Persona Management
# =====================================================================

def get_user_profile(user_id: str = "primary_user") -> Dict[str, Any]:
    """Retrieves the user's cognitive profile and impression data."""
    init_db()
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM user_impression_profile WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        if row:
            data = dict(row)
            try:
                data["key_preferences"] = json.loads(data.get("key_preferences", "[]"))
            except Exception:
                data["key_preferences"] = []
            try:
                data["active_projects"] = json.loads(data.get("active_projects", "[]"))
            except Exception:
                data["active_projects"] = []
            return data
        return {}


def update_user_profile(
    summary_impression: str,
    technical_level: Optional[str] = None,
    preferred_tone: Optional[str] = None,
    key_preferences: Optional[List[str]] = None,
    active_projects: Optional[List[str]] = None,
    user_id: str = "primary_user"
):
    """Updates the learned user impression and cognitive profile."""
    init_db()
    with get_connection() as conn:
        cursor = conn.cursor()
        prefs_json = json.dumps(key_preferences) if key_preferences is not None else None
        proj_json = json.dumps(active_projects) if active_projects is not None else None

        cursor.execute("""
            UPDATE user_impression_profile
            SET summary_impression = COALESCE(?, summary_impression),
                technical_level = COALESCE(?, technical_level),
                preferred_tone = COALESCE(?, preferred_tone),
                key_preferences = COALESCE(?, key_preferences),
                active_projects = COALESCE(?, active_projects),
                total_interactions = total_interactions + 1,
                last_updated = CURRENT_TIMESTAMP
            WHERE user_id = ?
        """, (summary_impression, technical_level, preferred_tone, prefs_json, proj_json, user_id))
        conn.commit()


def reset_user_profile(user_id: str = "primary_user"):
    """Resets user cognitive profile to defaults."""
    init_db()
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM user_impression_profile WHERE user_id = ?", (user_id,))
        conn.commit()
    init_db()


# =====================================================================
# Scheduled Tasks
# =====================================================================

def add_task(prompt: str, run_time: str) -> int:
    """Adds a new scheduled task into the database."""
    init_db()
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO scheduled_tasks (prompt, run_time, last_run)
            VALUES (?, ?, '')
        """, (prompt.strip(), run_time.strip()))
        conn.commit()
        return cursor.lastrowid


def get_all_tasks() -> list[dict]:
    """Retrieves all scheduled tasks from the database."""
    init_db()
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, prompt, run_time, last_run FROM scheduled_tasks ORDER BY run_time ASC")
        rows = cursor.fetchall()
        return [dict(row) for row in rows]


def delete_task(task_id: int):
    """Deletes a scheduled task by ID."""
    init_db()
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM scheduled_tasks WHERE id = ?", (task_id,))
        conn.commit()


def update_last_run(task_id: int, date_string: str):
    """Updates the last_run date for a scheduled task to prevent duplicate executions."""
    init_db()
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE scheduled_tasks SET last_run = ? WHERE id = ?", (date_string, task_id))
        conn.commit()


if __name__ == "__main__":
    init_db()
    print("Database initialized successfully at:", DB_PATH)
    print("User Profile:", get_user_profile())
