import os
import sys
import time
from datetime import datetime
from gtts import gTTS
import db_manager

# Configure UTF-8 encoding for Windows compatibility
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")
os.environ["PYTHONIOENCODING"] = "utf-8"

# Import LangGraph orchestrator graph from main module
from main import app_graph

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

def execute_autonomous_task(task: dict, current_date: str):
    """
    Executes a dynamic task fetched from SQLite database, converts final text
    to spoken voice audio via gTTS, and updates last_run date in SQLite.
    """
    task_id = task["id"]
    prompt = task["prompt"]
    run_time = task["run_time"]

    print("\n" + "=" * 60)
    print(f"⏰ [Autonomous Worker] Executing Task #{task_id} scheduled for {run_time}...")
    print(f"📌 Prompt: {prompt}")
    print("=" * 60 + "\n")

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
    """
    db_manager.init_db()
    print("🤖 Autonomous Dynamic Background Engine Active.")
    print("📁 Connected to SQLite database:", db_manager.DB_PATH)
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
