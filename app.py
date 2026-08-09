import os
import streamlit as st
from main import run_agency

# Configure Streamlit page layout and theme
st.set_page_config(
    page_title="MAK AI Business Agency",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for modern dark-mode glassmorphism styling
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&display=swap');

    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }

    .stApp {
        background: linear-gradient(135deg, #0f172a 0%, #1e1b4b 50%, #0f172a 100%);
        color: #f8fafc;
    }

    .main-header {
        background: rgba(30, 41, 59, 0.7);
        backdrop-filter: blur(12px);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 16px;
        padding: 2rem;
        margin-bottom: 2rem;
        box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.3);
    }

    .agency-card {
        background: rgba(15, 23, 42, 0.6);
        border: 1px solid rgba(99, 102, 241, 0.2);
        border-radius: 12px;
        padding: 1rem;
        margin-bottom: 0.8rem;
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
        font-size: 0.75rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }

    .badge-mak { background: rgba(56, 189, 248, 0.2); color: #38bdf8; border: 1px solid #38bdf8; }
    .badge-ba { background: rgba(168, 85, 247, 0.2); color: #c084fc; border: 1px solid #c084fc; }
    .badge-da { background: rgba(34, 197, 94, 0.2); color: #4ade80; border: 1px solid #4ade80; }
    .badge-fa { background: rgba(244, 63, 94, 0.2); color: #fb7185; border: 1px solid #fb7185; }

    .stButton>button {
        background: linear-gradient(135deg, #6366f1 0%, #4f46e5 100%);
        color: white;
        font-weight: 600;
        font-size: 1rem;
        padding: 0.75rem 2rem;
        border-radius: 10px;
        border: none;
        box-shadow: 0 4px 14px rgba(99, 102, 241, 0.4);
        transition: all 0.2s ease;
        width: 100%;
    }

    .stButton>button:hover {
        background: linear-gradient(135deg, #4f46e5 0%, #4338ca 100%);
        box-shadow: 0 6px 20px rgba(99, 102, 241, 0.6);
        transform: translateY(-1px);
    }

    .output-container {
        background: rgba(15, 23, 42, 0.85);
        border: 1px solid rgba(56, 189, 248, 0.3);
        border-radius: 12px;
        padding: 1.75rem;
        margin-top: 1.5rem;
        line-height: 1.6;
    }
</style>
""", unsafe_allow_html=True)

# Header Section
st.markdown("""
<div class="main-header">
    <h1 style="margin:0; font-size:2.5rem; font-weight:700; background: linear-gradient(135deg, #38bdf8, #818cf8); -webkit-background-clip: text; -webkit-text-fill-color: transparent;">
        ⚡ MAK AI Business Agency
    </h1>
    <p style="margin-top:0.5rem; color:#94a3b8; font-size:1.1rem;">
        Multi-agent corporate intelligence: Business Strategy, Quantitative Analytics, Financial Auditing & Operations.
    </p>
</div>
""", unsafe_allow_html=True)

# Sidebar with Agency Team Overview
with st.sidebar:
    st.markdown("### 🏢 Agency Roster")

    st.markdown("""
    <div class="agency-card">
        <span class="role-badge badge-mak">Operations</span>
        <h4 style="margin:0.4rem 0 0.1rem 0; color:#f8fafc;">MAK</h4>
        <p style="margin:0; font-size:0.8rem; color:#94a3b8;">
            Chief of Operations supervising workflow and synthesizing final executive strategy.
        </p>
    </div>

    <div class="agency-card">
        <span class="role-badge badge-ba">Strategy</span>
        <h4 style="margin:0.4rem 0 0.1rem 0; color:#f8fafc;">Business Analyst</h4>
        <p style="margin:0; font-size:0.8rem; color:#94a3b8;">
            Market intelligence, web scraping (ScrapeWebsiteTool), competitor research & positioning.
        </p>
    </div>

    <div class="agency-card">
        <span class="role-badge badge-da">Analytics</span>
        <h4 style="margin:0.4rem 0 0.1rem 0; color:#f8fafc;">Data Analyst</h4>
        <p style="margin:0; font-size:0.8rem; color:#94a3b8;">
            Quantitative parsing, local document auditing (FileReadTool) & statistical benchmarks.
        </p>
    </div>

    <div class="agency-card">
        <span class="role-badge badge-fa">Finance</span>
        <h4 style="margin:0.4rem 0 0.1rem 0; color:#f8fafc;">Financial Assessor</h4>
        <p style="margin:0; font-size:0.8rem; color:#94a3b8;">
            Financial risk auditing, ROI analysis, margins, unit economics & commercial feasibility.
        </p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("💡 **Tip**: Include targets, unit economics, or specific markets in your prompt for maximum depth.")

# Main Input & Execution Section
st.subheader("🎯 Define Business Task / Request")

default_prompt = "Analyze the commercial viability, unit economics, competitor landscape, and risk factors for launching an open-source AI agent SaaS in 2026."

user_request = st.text_area(
    "Enter your prompt or business research request:",
    value=default_prompt,
    height=120,
    help="Describe the research topic, target market, or business strategic task for the agency."
)

col1, col2 = st.columns([1, 4])
with col1:
    deploy_btn = st.button("🚀 Deploy Agency")

if deploy_btn:
    if not user_request.strip():
        st.warning("Please enter a valid request before deploying agents.")
    else:
        with st.spinner("🤖 Agency Agents (BA, DA, Assessor & MAK) are searching, scraping, auditing, and synthesizing report..."):
            try:
                result_text = run_agency(user_request)
                st.success("✅ Multi-Agent Agency Execution Complete!")

                # Display Output Result
                st.markdown("### 📊 Executive Report Output")
                st.markdown(f'<div class="output-container">{result_text}</div>', unsafe_allow_html=True)

                # Option to download persistent output
                output_filepath = os.path.join("output", "agency_report.txt")
                if os.path.exists(output_filepath):
                    with open(output_filepath, "r", encoding="utf-8") as f:
                        file_data = f.read()

                    st.download_button(
                        label="📥 Download Executive Report (.txt)",
                        data=file_data,
                        file_name="agency_report.txt",
                        mime="text/plain"
                    )

            except Exception as e:
                st.error(f"❌ Execution Error: {e}")
