import os
import sys
import io
import datetime
import traceback
import pandas as pd
import streamlit as st
from dotenv import load_dotenv
from gtts import gTTS
import db_manager

# Load environment variables
load_dotenv()

# Initialize SQLite Database for Task Autonomy
db_manager.init_db()

# Create temp_uploads directory for file attachment dropzone
UPLOAD_DIR = os.path.join(os.getcwd(), "temp_uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Configure Streamlit page layout and theme MUST be the first Streamlit command
st.set_page_config(
    page_title="MAK Enterprise OS",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

def inject_custom_css():
    """Injects modern Tailwind-style dark mode glassmorphism CSS into Streamlit UI."""
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

        /* Hide default Streamlit header, main menu, and footer */
        #MainMenu { visibility: hidden; }
        header { visibility: hidden; }
        footer { visibility: hidden; }

        html, body, [class*="css"] {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
        }

        /* Centered chat interface container with max-width (Tailwind max-w-6xl feel) */
        .block-container {
            max-width: 1100px !important;
            padding-top: 1.5rem !important;
            padding-bottom: 3rem !important;
            margin: 0 auto;
        }

        .stApp {
            background: linear-gradient(135deg, #0b0f19 0%, #111827 50%, #0b0f19 100%);
            color: #f8fafc;
        }

        /* Modern Glassmorphism Card Header */
        .main-header {
            background: rgba(17, 24, 39, 0.75);
            backdrop-filter: blur(16px);
            -webkit-backdrop-filter: blur(16px);
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 20px;
            padding: 1.5rem 2rem;
            margin-bottom: 1.5rem;
            box-shadow: 0 10px 30px -5px rgba(0, 0, 0, 0.5);
        }

        /* Modern Tailwind-style chat bubbles */
        [data-testid="stChatMessage"] {
            background: rgba(17, 24, 39, 0.65) !important;
            backdrop-filter: blur(12px) !important;
            border: 1px solid rgba(255, 255, 255, 0.08) !important;
            border-radius: 16px !important;
            padding: 1.2rem 1.5rem !important;
            margin-bottom: 1rem !important;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.25) !important;
            transition: all 0.2s ease-in-out;
        }

        [data-testid="stChatMessage"]:hover {
            border-color: rgba(99, 102, 241, 0.3) !important;
        }

        /* Agency cards in roster */
        .agency-card {
            background: rgba(15, 23, 42, 0.6);
            border: 1px solid rgba(99, 102, 241, 0.2);
            border-radius: 12px;
            padding: 0.75rem;
            margin-bottom: 0.5rem;
            transition: transform 0.2s ease, border-color 0.2s ease;
        }

        .agency-card:hover {
            transform: translateY(-2px);
            border-color: rgba(99, 102, 241, 0.5);
        }

        .role-badge {
            display: inline-block;
            padding: 0.2rem 0.6rem;
            border-radius: 9999px;
            font-size: 0.68rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }

        .badge-cfo { background: rgba(56, 189, 248, 0.2); color: #38bdf8; border: 1px solid #38bdf8; }
        .badge-triage { background: rgba(129, 140, 248, 0.2); color: #818cf8; border: 1px solid #818cf8; }
        .badge-corp { background: rgba(168, 85, 247, 0.2); color: #c084fc; border: 1px solid #c084fc; }
        .badge-risk { background: rgba(244, 63, 94, 0.2); color: #fb7185; border: 1px solid #fb7185; }
        .badge-treasury { background: rgba(34, 197, 94, 0.2); color: #4ade80; border: 1px solid #4ade80; }
        .badge-cap { background: rgba(251, 146, 60, 0.2); color: #fb923c; border: 1px solid #fb923c; }
        .badge-ma { background: rgba(236, 72, 153, 0.2); color: #f472b6; border: 1px solid #f472b6; }
        .badge-ctrl { background: rgba(16, 185, 129, 0.2); color: #34d399; border: 1px solid #34d399; }
        .badge-port { background: rgba(139, 92, 246, 0.2); color: #a78bfa; border: 1px solid #a78bfa; }
        .badge-val { background: rgba(245, 158, 11, 0.2); color: #fbbf24; border: 1px solid #fbbf24; }
        .badge-cred { background: rgba(225, 29, 72, 0.2); color: #fda4af; border: 1px solid #fda4af; }
        .badge-inv { background: rgba(20, 184, 166, 0.2); color: #2dd4bf; border: 1px solid #2dd4bf; }
        .badge-fpa { background: rgba(99, 102, 241, 0.2); color: #818cf8; border: 1px solid #818cf8; }
        .badge-tutor { background: rgba(14, 165, 233, 0.2); color: #38bdf8; border: 1px solid #38bdf8; }
        .badge-cmo { background: rgba(244, 63, 94, 0.2); color: #fb7185; border: 1px solid #fb7185; }
        .badge-seo { background: rgba(6, 182, 212, 0.2); color: #22d3ee; border: 1px solid #22d3ee; }
        .badge-copy { background: rgba(236, 72, 153, 0.2); color: #f472b6; border: 1px solid #f472b6; }
        .badge-social { background: rgba(139, 92, 246, 0.2); color: #a78bfa; border: 1px solid #a78bfa; }
        .badge-vpsales { background: rgba(245, 158, 11, 0.2); color: #fbbf24; border: 1px solid #fbbf24; }
        .badge-sdr { background: rgba(16, 185, 129, 0.2); color: #34d399; border: 1px solid #34d399; }
        .badge-sa { background: rgba(99, 102, 241, 0.2); color: #818cf8; border: 1px solid #818cf8; }
        .badge-cto { background: rgba(59, 130, 246, 0.2); color: #60a5fa; border: 1px solid #60a5fa; }
        .badge-dev { background: rgba(16, 185, 129, 0.2); color: #34d399; border: 1px solid #34d399; }
        .badge-qa { background: rgba(245, 158, 11, 0.2); color: #fbbf24; border: 1px solid #fbbf24; }

        /* Custom scrollbar */
        ::-webkit-scrollbar {
            width: 6px;
            height: 6px;
        }
        ::-webkit-scrollbar-track {
            background: rgba(15, 23, 42, 0.6);
        }
        ::-webkit-scrollbar-thumb {
            background: rgba(99, 102, 241, 0.4);
            border-radius: 4px;
        }
    </style>
    """, unsafe_allow_html=True)

# Inject Tailwind-style CSS facelift right after st.set_page_config
inject_custom_css()

# Configure UTF-8 encoding for Windows compatibility
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")
os.environ["PYTHONIOENCODING"] = "utf-8"

# Safe top-level import to catch SyntaxErrors, ImportErrors, and module crashes for Self-Healing
try:
    from main import run_agency
    from self_healing import trigger_rescue_mission
    load_error = None
except BaseException:
    load_error = traceback.format_exc()
    run_agency = None
    trigger_rescue_mission = None

# Initialize Session State
if "messages" not in st.session_state:
    st.session_state.messages = []
if "session_tasks" not in st.session_state:
    st.session_state.session_tasks = 0

# Helper function: Transcribe audio using Groq Whisper API
def transcribe_audio_groq(audio_bytes) -> str:
    """Transcribes user recorded audio using Groq Whisper API (whisper-large-v3-turbo)."""
    try:
        from groq import Groq
        client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        transcription = client.audio.transcriptions.create(
            file=("voice_prompt.wav", audio_bytes),
            model="whisper-large-v3-turbo",
            response_format="text"
        )
        return str(transcription).strip()
    except Exception as e:
        st.sidebar.error(f"Voice Transcription Notice: {e}")
        return ""

# Helper function: Generate gTTS audio bytes
def generate_tts_audio(text: str):
    """Converts response text to spoken audio bytes using gTTS."""
    try:
        clean_text = text.replace("#", "").replace("*", "").replace("`", "").replace("-", " ")
        if len(clean_text) > 500:
            clean_text = clean_text[:500] + "... Executive briefing output completed."
        tts = gTTS(text=clean_text, lang="en", slow=False)
        audio_buffer = io.BytesIO()
        tts.write_to_fp(audio_buffer)
        audio_buffer.seek(0)
        return audio_buffer.read()
    except Exception as e:
        print(f"gTTS Generation Warning: {e}")
        return None

# Main Dashboard SaaS Header
st.markdown("""
<div class="main-header">
    <div style="display: flex; align-items: center; justify-content: space-between;">
        <div>
            <h1 style="margin:0; font-size:2.2rem; font-weight:800; background: linear-gradient(135deg, #38bdf8 0%, #818cf8 50%, #c084fc 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent;">
                ⚡ MAK Enterprise OS
            </h1>
            <p style="margin-top:0.3rem; color:#94a3b8; font-size:1.05rem; font-weight: 400;">
                Executive Command Center • Autonomous Finance, Engineering, Marketing & Sales Multi-Agent System
            </p>
        </div>
        <div style="text-align: right;">
            <span style="padding: 0.4rem 1rem; border-radius: 9999px; background: rgba(34, 197, 94, 0.15); color: #4ade80; border: 1px solid rgba(34, 197, 94, 0.3); font-size: 0.85rem; font-weight: 600;">
                ● SYSTEM ONLINE
            </span>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# Fetch Scheduled Tasks Count from SQLite
scheduled_tasks_list = db_manager.get_all_tasks()
task_count = len(scheduled_tasks_list)

# Sidebar - System Diagnostics & Voice Input
with st.sidebar:
    st.markdown("## 📊 System Diagnostics")

    col1, col2 = st.columns(2)
    with col1:
        st.metric(label="Active Departments", value="16 Deployed", delta="Operational")
    with col2:
        st.metric(label="Scheduled Tasks", value=f"{task_count} Active", delta=f"{st.session_state.session_tasks} Executed")

    st.markdown("---")
    st.markdown("### 🎙️ Whisper Voice Command")
    voice_audio = st.audio_input("Record Voice Prompt")
    voice_prompt_text = ""
    if voice_audio:
        with st.spinner("Transcribing voice via Groq Whisper..."):
            audio_data = voice_audio.read()
            voice_prompt_text = transcribe_audio_groq(audio_data)
            if voice_prompt_text:
                st.success(f"Transcribed: '{voice_prompt_text}'")

    st.markdown("---")
    st.markdown("### 🏛️ Department Roster")

    with st.expander("💻 Engineering (Software House)", expanded=False):
        st.markdown("""
        <div class="agency-card">
            <span class="role-badge badge-cto">CTO</span>
            <h4 style="margin:0.2rem 0; color:#f8fafc;">Chief Technology Officer</h4>
            <p style="margin:0; font-size:0.75rem; color:#94a3b8;">System architecture & code review.</p>
        </div>
        <div class="agency-card">
            <span class="role-badge badge-dev">Senior Dev</span>
            <h4 style="margin:0.2rem 0; color:#f8fafc;">Senior Software Engineer</h4>
            <p style="margin:0; font-size:0.75rem; color:#94a3b8;">Clean, efficient code implementation.</p>
        </div>
        <div class="agency-card">
            <span class="role-badge badge-qa">QA Lead</span>
            <h4 style="margin:0.2rem 0; color:#f8fafc;">Lead QA Engineer</h4>
            <p style="margin:0; font-size:0.75rem; color:#94a3b8;">Syntax error, edge-case & security audit.</p>
        </div>
        """, unsafe_allow_html=True)

    with st.expander("📈 Sales & Revenue", expanded=False):
        st.markdown("""
        <div class="agency-card">
            <span class="role-badge badge-vpsales">VP Sales</span>
            <h4 style="margin:0.2rem 0; color:#f8fafc;">VP of Sales</h4>
            <p style="margin:0; font-size:0.75rem; color:#94a3b8;">Outreach strategy & conversion optimization.</p>
        </div>
        <div class="agency-card">
            <span class="role-badge badge-sdr">Senior SDR</span>
            <h4 style="margin:0.2rem 0; color:#f8fafc;">Senior SDR</h4>
            <p style="margin:0; font-size:0.75rem; color:#94a3b8;">Cold emails & lead scoring matrix.</p>
        </div>
        <div class="agency-card">
            <span class="role-badge badge-sa">Solutions Architect</span>
            <h4 style="margin:0.2rem 0; color:#f8fafc;">Solutions Architect</h4>
            <p style="margin:0; font-size:0.75rem; color:#94a3b8;">Objection handling & pricing scripts.</p>
        </div>
        """, unsafe_allow_html=True)

    with st.expander("📣 Marketing & Brand", expanded=False):
        st.markdown("""
        <div class="agency-card">
            <span class="role-badge badge-cmo">CMO</span>
            <h4 style="margin:0.2rem 0; color:#f8fafc;">Chief Marketing Officer</h4>
            <p style="margin:0; font-size:0.75rem; color:#94a3b8;">Brand strategy & executive campaign alignment.</p>
        </div>
        <div class="agency-card">
            <span class="role-badge badge-seo">SEO Analyst</span>
            <h4 style="margin:0.2rem 0; color:#f8fafc;">SEO & Trend Analyst</h4>
            <p style="margin:0; font-size:0.75rem; color:#94a3b8;">Keyword research & competitor strategies.</p>
        </div>
        <div class="agency-card">
            <span class="role-badge badge-copy">Lead Copywriter</span>
            <h4 style="margin:0.2rem 0; color:#f8fafc;">Lead Copywriter</h4>
            <p style="margin:0; font-size:0.75rem; color:#94a3b8;">Landing page copy & value propositions.</p>
        </div>
        """, unsafe_allow_html=True)

    with st.expander("💼 Corporate Finance & Risk", expanded=False):
        st.markdown("""
        <div class="agency-card">
            <span class="role-badge badge-cfo">CFO</span>
            <h4 style="margin:0.2rem 0; color:#f8fafc;">Chief Financial Officer</h4>
            <p style="margin:0; font-size:0.75rem; color:#94a3b8;">Capital allocation & board decisions.</p>
        </div>
        <div class="agency-card">
            <span class="role-badge badge-risk">Risk Manager</span>
            <h4 style="margin:0.2rem 0; color:#f8fafc;">Risk Manager</h4>
            <p style="margin:0; font-size:0.75rem; color:#94a3b8;">VaR, stress testing & downside mitigation.</p>
        </div>
        <div class="agency-card">
            <span class="role-badge badge-corp">Corp Finance</span>
            <h4 style="margin:0.2rem 0; color:#f8fafc;">Corp Finance Analyst</h4>
            <p style="margin:0; font-size:0.75rem; color:#94a3b8;">DCF models, NPV & IRR evaluation.</p>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")
    st.caption("🛡️ Central Knowledge Base RAG & Self-Healing Debugger active.")


@st.cache_resource
def build_agency_graph():
    """
    Imports agents and builds the LangGraph workflow.
    Cached with @st.cache_resource so agents and graph structure are compiled once and held in RAM.
    """
    from main import app_graph
    return app_graph

@st.cache_resource
def start_background_worker():
    """
    Auto-starts the background autonomous task manager loop in a daemon thread.
    Cached with @st.cache_resource so only one worker thread is spawned per Streamlit server run.
    """
    import threading
    from autonomous_worker import main_worker_loop
    worker_thread = threading.Thread(target=main_worker_loop, daemon=True)
    worker_thread.start()
    return worker_thread

# Auto-start background autonomous worker daemon thread on Streamlit launch
start_background_worker()

# Setup Control Panel Navigation Tabs
tab1, tab2 = st.tabs(["💬 Command Center", "🤖 Autonomy Engine"])

# =====================================================================
# TAB 1: Live Command Center Interactive Conversational Chat
# =====================================================================
with tab1:
    # Render Chat Message History
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            if message.get("audio_bytes"):
                st.audio(message["audio_bytes"], format="audio/mp3")

    # Attachment Dropzone (File Uploads)
    with st.expander("📎 Attach Files & Media"):
        uploaded_files = st.file_uploader(
            "Drag and drop files for the agents to analyze",
            accept_multiple_files=True
        )

        saved_filenames = []
        if uploaded_files:
            for file in uploaded_files:
                file_path = os.path.join(UPLOAD_DIR, file.name)
                with open(file_path, "wb") as f:
                    f.write(file.getbuffer())
                saved_filenames.append(file.name)
            st.success(f"Uploaded {len(saved_filenames)} file(s) to temp_uploads: {', '.join(saved_filenames)}")

    # Native Chat Input & Voice Trigger
    typed_request = st.chat_input("Deploy your agency...")
    user_request = typed_request or voice_prompt_text

    if user_request:
        # Track task count
        st.session_state.session_tasks += 1

        # Render User Message in UI
        st.session_state.messages.append({"role": "user", "content": user_request})
        with st.chat_message("user"):
            st.markdown(user_request)

        # Inject context for uploaded files into engine request
        engine_request = user_request
        if uploaded_files:
            file_names_str = ", ".join([f.name for f in uploaded_files])
            engine_request += f"\n\n[SYSTEM NOTE: The user has attached files located in the './temp_uploads' directory ({file_names_str}). Use your file reading/vision tools to analyze them to complete this request.]"

        # Render Assistant Execution
        with st.chat_message("assistant"):
            # Handle Startup Import Crashes
            if load_error is not None:
                st.error("⚠️ Startup Import Failure Detected! Triggering Autonomous Self-Healing Rescue Crew...")
                st.code(load_error, language="python")
                with st.spinner("🚑 Doctor and Surgeon are analyzing stack trace and preparing patch..."):
                    try:
                        from self_healing import trigger_rescue_mission
                        rescue_report = trigger_rescue_mission(load_error)
                        response_text = f"**🩺 Self-Healing Rescue Mission Summary:**\n\n{rescue_report}\n\n*Check terminal console to approve/decline code patches.*"
                    except Exception as rescue_err:
                        response_text = f"❌ Self-Healing Rescue Exception: {rescue_err}"
                st.markdown(response_text)
                st.session_state.messages.append({"role": "assistant", "content": response_text})

            else:
                # Live Execution Status Tracker Block
                with st.status("Orchestrating Departments...", expanded=True) as status:
                    st.write("🔍 Chief of Staff (Triage) inspecting Knowledge Base RAG & Pydantic reasoning rules...")
                    try:
                        st.write("⚡ Fetching cached agency graph & executing department mini-crews...")
                        graph = build_agency_graph()
                        initial_state = {
                            "user_request": engine_request,
                            "triage_output": "",
                            "selected_departments": [],
                            "raw_department_reports": {},
                            "department_summaries": {},
                            "final_response": "",
                            "final_cfo_decision": ""
                        }
                        final_state = graph.invoke(initial_state)
                        result_output = final_state.get("final_response") or final_state.get("final_cfo_decision", "")
                        status.update(label="Task Complete", state="complete", expanded=False)
                        st.markdown(result_output)

                        # Generate gTTS Audio Output
                        audio_bytes = generate_tts_audio(result_output)
                        if audio_bytes:
                            st.audio(audio_bytes, format="audio/mp3")

                        st.session_state.messages.append({
                            "role": "assistant",
                            "content": result_output,
                            "audio_bytes": audio_bytes
                        })

                    except Exception as e:
                        error_traceback = traceback.format_exc()
                        status.update(label="System Exception Caught - Deploying Self-Healing Rescue Crew", state="error", expanded=True)
                        st.error("⚠️ System Crash Detected! Deploying Autonomous Self-Healing Rescue Crew...")
                        st.code(error_traceback, language="python")

                        with st.spinner("🚑 Doctor (Diagnostician) and Surgeon (Code Fixer) are analyzing stack trace..."):
                            try:
                                from self_healing import trigger_rescue_mission
                                rescue_report = trigger_rescue_mission(error_traceback)
                                rescue_text = f"**🩺 Self-Healing Rescue Mission Summary:**\n\n{rescue_report}\n\n*Action Required: Check terminal console to approve or decline the Surgeon's proposed code modifications (Human-in-the-Loop Safety).*"
                            except Exception as rescue_err:
                                rescue_text = f"❌ Rescue Mission Exception: {rescue_err}"

                        st.markdown(rescue_text)
                        st.session_state.messages.append({"role": "assistant", "content": rescue_text})


# =====================================================================
# TAB 2: Autonomy Engine Task Scheduler Control Panel (Clean Data UI)
# =====================================================================
with tab2:
    st.markdown("### ⚙️ Autonomous Task Scheduler Control Panel")
    st.caption("Schedule proactive daily background tasks. Tasks are saved persistently in SQLite and monitored continuously by the background worker daemon.")

    # Form to Schedule New Task
    with st.form("schedule_task_form", clear_on_submit=True):
        st.markdown("#### ➕ Schedule New Autonomous Task")
        prompt_input = st.text_area(
            "Autonomous Prompt / Task Instructions",
            placeholder="e.g. Good morning. Check the live internet for top AI & Finance news today. Output a 3-sentence summary and publish a tweet."
        )
        time_input = st.time_input("Execution Time (HH:MM)", value=datetime.time(8, 0))

        submitted = st.form_submit_button("📅 Schedule Autonomous Task")
        if submitted:
            if prompt_input.strip():
                formatted_time = time_input.strftime("%H:%M")
                db_manager.add_task(prompt_input, formatted_time)
                st.success(f"Task scheduled successfully for {formatted_time} daily!")
                st.rerun()
            else:
                st.warning("Please enter a valid prompt before submitting.")

    st.markdown("---")
    st.markdown("#### 📋 Scheduled Autonomous Tasks Database")

    scheduled_tasks = db_manager.get_all_tasks()
    if not scheduled_tasks:
        st.info("No autonomous tasks scheduled yet. Use the form above to add your first daily job!")
    else:
        # Format Dataframe for Clean Display
        df_display = pd.DataFrame(scheduled_tasks)
        df_display.rename(columns={
            "id": "Task ID",
            "run_time": "Scheduled Time",
            "last_run": "Last Execution Date",
            "prompt": "Task Prompt Instructions"
        }, inplace=True)

        st.dataframe(
            df_display,
            column_config={
                "Task ID": st.column_config.NumberColumn("ID", width="small"),
                "Scheduled Time": st.column_config.TextColumn("Run Time (HH:MM)", width="small"),
                "Last Execution Date": st.column_config.TextColumn("Last Executed", width="medium"),
                "Task Prompt Instructions": st.column_config.TextColumn("Prompt", width="large"),
            },
            use_container_width=True,
            hide_index=True
        )

        st.markdown("#### 🗑️ Delete Scheduled Task")
        with st.expander("Manage / Delete Individual Tasks"):
            for task in scheduled_tasks:
                t_id = task["id"]
                t_prompt = task["prompt"]
                t_time = task["run_time"]

                col_info, col_del = st.columns([5, 1])
                with col_info:
                    st.write(f"**Task #{t_id}** (`{t_time}`): {t_prompt}")
                with col_del:
                    if st.button("Delete", key=f"del_task_{t_id}"):
                        db_manager.delete_task(t_id)
                        st.toast(f"Task #{t_id} deleted successfully!")
                        st.rerun()
