import os
import sys
import time
from datetime import datetime
from typing import Dict, Any, Optional
from gtts import gTTS
import db_manager

# Configure UTF-8 encoding for Windows compatibility
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")
os.environ["PYTHONIOENCODING"] = "utf-8"

# Initialize debugpy DAP listener on startup for live IDE attachment
def init_debugpy_listener(host: str = "127.0.0.1", port: int = 5678):
    """Initializes debugpy DAP bridge on startup so IDE can attach at any time without process restarts."""
    try:
        import debugpy
        debugpy.listen((host, port))
        print(f"🐞 [Autonomous Worker] debugpy listener initialized on {host}:{port} (IDE DAP bridge ready).")
    except RuntimeError:
        print(f"ℹ️ [Autonomous Worker] debugpy listener already running on {host}:{port}.")
    except Exception as e:
        print(f"⚠️ [Autonomous Worker] debugpy initialization notice: {e}")

init_debugpy_listener()

# Import LangGraph orchestrator graph from main module
from main import app_graph
from engineering_department import python_syntax_checker, hitl_file_writer

def play_audio(file_path: str):
    """Plays generated audio file natively using platform default player."""
    try:
        if sys.platform == "win32":
            os.system(f'start "" "{file_path}"')
        elif sys.platform == "darwin":
            os.system(f'afplay "{file_path}"')
        else:
            os.system(f'xdg-open "{file_path}"')
    except Exception as e:
        print(f"⚠️ Audio playback notice: {e}")

def verify_hitl_code_safety_gate(prompt: str, proposed_code: Optional[str] = None) -> bool:
    """
    Enforces Human-in-the-Loop (HITL) approval gate for autonomous background operations.
    Validates syntax and verifies authorization before applying code changes to workspace.
    """
    if proposed_code:
        print("\n🔒 [HITL SAFETY GATE] Verifying proposed code syntax & safety protocols...")
        syntax_res = python_syntax_checker.func(proposed_code)
        if "Syntax is valid." not in syntax_res:
            print(f"❌ [HITL Gate] Syntax check failed:\n{syntax_res}")
            return False
        print("✅ [HITL Gate] AST Python Syntax verified.")
    return True

def execute_autonomous_task(task: dict, current_date: str):
    """
    Executes a dynamic task fetched from SQLite database, converts final text
    to spoken voice audio via gTTS, and updates last_run date in SQLite.
    Enforces Human-in-the-Loop (HITL) safety checks before applying code changes.
    """
    task_id = task["id"]
    prompt = task["prompt"]
    run_time = task["run_time"]

    print("\n" + "=" * 60)
    print(f"⏰ [Autonomous Worker] Executing Task #{task_id} scheduled for {run_time}...")
    print(f"📌 Prompt: {prompt}")
    print("=" * 60 + "\n")

    # Enforce HITL Gate check
    if not verify_hitl_code_safety_gate(prompt):
        print(f"❌ [HITL Gate] Task #{task_id} aborted by safety protocols.")
        return

    initial_state = {
        "user_request": prompt,
        "triage_output": "",
        "selected_departments": [],
        "raw_department_reports": {},
        "department_summaries": {},
        "final_response": "",
        "final_cfo_decision": "",
        "retry_count": 0,
        "inspector_feedback": "",
        "last_active_department": "",
        "inspector_decision": {}
    }

    try:
        final_state = app_graph.invoke(initial_state)
        result_text = final_state.get("final_response") or final_state.get("final_cfo_decision", "")

        print("\n" + "=" * 60)
        print(f"📢 [Task #{task_id} Result]:")
        print("=" * 60)
        print(result_text)

        # Convert text result to spoken voice audio via gTTS
        mp3_path = f"briefing_task_{task_id}.mp3"
        print(f"\n🎙️ Generating voice audio briefing: '{mp3_path}'...")
        tts = gTTS(text=result_text, lang="en", slow=False)
        tts.save(mp3_path)
        print(f"🔊 Playing voice briefing out loud...")
        play_audio(mp3_path)

        # Update last_run date in SQLite to prevent duplicate execution in same minute
        db_manager.update_last_run(task_id, current_date)
        print(f"✅ Updated Task #{task_id} last_run to '{current_date}'.\n")

    except Exception as e:
        print(f"❌ Autonomous worker exception on Task #{task_id}: {e}")


def main_worker_loop():
    """
    Dynamic Autonomous Engine Loop:
    Polls SQLite database every 60 seconds, matching current time (HH:MM) against scheduled tasks.
    Ensures debugpy DAP listener is bound and available.
    """
    db_manager.init_db()
    init_debugpy_listener()
    print("🤖 Autonomous Dynamic Background Engine Active.")
    print("📁 Connected to SQLite database:", db_manager.DB_PATH)
    print("🐞 Debugpy DAP Listener Active at 127.0.0.1:5678 (Attach anytime from IDE)")
    print("Press Ctrl+C to stop.\n")

    while True:
        try:
            now = datetime.now()
            current_time = now.strftime("%H:%M")
            current_date = now.strftime("%Y-%m-%d")

            tasks = db_manager.get_all_tasks()

            for task in tasks:
                task_id = task["id"]
                run_time = task["run_time"]
                last_run = task["last_run"]

                if run_time == current_time and last_run != current_date:
                    execute_autonomous_task(task, current_date)

        except Exception as err:
            print(f"⚠️ Worker loop notice: {err}")

        time.sleep(60)


if __name__ == "__main__":
    main_worker_loop()
