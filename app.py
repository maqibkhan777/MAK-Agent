import os
import sys
import traceback
import streamlit as st

# Configure Streamlit page layout and theme MUST be the first Streamlit command
st.set_page_config(
    page_title="MAK Enterprise OS",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

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

# Custom CSS for modern dark-mode glassmorphism SaaS command center UI
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }

    .stApp {
        background: linear-gradient(135deg, #0b0f19 0%, #111827 50%, #0b0f19 100%);
        color: #f8fafc;
    }

    .main-header {
        background: rgba(17, 24, 39, 0.75);
        backdrop-filter: blur(16px);
        -webkit-backdrop-filter: blur(16px);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 16px;
        padding: 1.5rem 2rem;
        margin-bottom: 1.5rem;
        box-shadow: 0 10px 30px -5px rgba(0, 0, 0, 0.5);
    }

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

# Sidebar - System Diagnostics & Controls
with st.sidebar:
    st.markdown("## 📊 System Diagnostics")

    col1, col2 = st.columns(2)
    with col1:
        st.metric(label="Active Departments", value="16 Deployed", delta="Operational")
    with col2:
        st.metric(label="Session Tasks", value=f"{st.session_state.session_tasks} Executed")

    st.markdown("---")

    st.markdown("### 🏛️ Department Roster")

    with st.expander("💻 Engineering (Software House)", expanded=True):
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

# Render Chat Message History
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])


# Modern Chat Input & Execution Tracker
if user_request := st.chat_input("Deploy your agency..."):
    # Track task count
    st.session_state.session_tasks += 1

    # Render User Message
    st.session_state.messages.append({"role": "user", "content": user_request})
    with st.chat_message("user"):
        st.markdown(user_request)

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
            # Live Status Tracker Block
            with st.status("Orchestrating Departments...", expanded=True) as status:
                st.write("🔍 Chief of Staff (Triage) inspecting Knowledge Base RAG & routing request...")
                try:
                    st.write("⚡ Fetching cached agency graph & executing mini-crews...")
                    graph = build_agency_graph()
                    initial_state = {
                        "user_request": user_request,
                        "triage_output": "",
                        "selected_departments": [],
                        "raw_department_reports": {},
                        "department_summaries": {},
                        "final_response": "",
                        "final_cfo_decision": ""
                    }
                    final_state = graph.invoke(initial_state)
                    result_output = final_state.get("final_response") or final_state.get("final_cfo_decision", "")
                    status.update(label="Task Completed", state="complete", expanded=False)
                    st.markdown(result_output)
                    st.session_state.messages.append({"role": "assistant", "content": result_output})
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
