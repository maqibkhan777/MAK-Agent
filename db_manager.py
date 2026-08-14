import sqlite3
from datetime import datetime
import os

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "scheduled_tasks.db")

def get_connection():
    """Returns a SQLite connection object configured for safe multi-threaded access."""
    conn = sqlite3.connect(DB_PATH, timeout=30.0, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Creates the scheduled_tasks table if it does not exist and enables WAL mode."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("PRAGMA journal_mode=WAL;")
        cursor.execute("PRAGMA busy_timeout=5000;")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS scheduled_tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                prompt TEXT NOT NULL,
                run_time TEXT NOT NULL,
                last_run TEXT DEFAULT ''
            )
        """)
        conn.commit()

def add_task(prompt: str, run_time: str) -> int:
    """Adds a new scheduled task into the database."""
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
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM scheduled_tasks WHERE id = ?", (task_id,))
        conn.commit()

def update_last_run(task_id: int, date_string: str):
    """Updates the last_run date for a scheduled task to prevent duplicate executions."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE scheduled_tasks SET last_run = ? WHERE id = ?", (date_string, task_id))
        conn.commit()

if __name__ == "__main__":
    init_db()
    print("Database initialized successfully at:", DB_PATH)
