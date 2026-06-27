import datetime
import os
import sys
from pathlib import Path
import streamlit as st

# Add root folder to python path
root_path = Path(__file__).resolve().parent.parent
if str(root_path) not in sys.path:
    sys.path.insert(0, str(root_path))

from database.database import DatabaseManager
from analyzer.repository import run_repository_analysis
from utils.logger import logger

st.set_page_config(
    page_title="GitHub Repository Intelligence Tool",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Dark styling
st.markdown("""
<style>
    .main-title {
        background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
        padding: 30px;
        border-radius: 12px;
        color: white;
        text-align: center;
        margin-bottom: 25px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.3);
        border: 1px solid #334155;
    }
    .metric-card {
        background: #0f172a;
        border-left: 5px solid #2563eb;
        padding: 20px;
        border-radius: 8px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.2);
        text-align: center;
        border: 1px solid #1e293b;
    }
    .metric-value {
        font-size: 2.2rem;
        font-weight: bold;
        color: #38bdf8;
    }
    .metric-label {
        font-size: 0.9rem;
        color: #94a3b8;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    .health-value {
        font-size: 4rem;
        font-weight: bold;
        color: #10b981;
        text-shadow: 0 0 10px rgba(16,185,129,0.3);
    }
</style>
""", unsafe_allow_html=True)

db = DatabaseManager()
db.init_db()

# Session State Initialization
if "repo_id" not in st.session_state:
    st.session_state["repo_id"] = None
if "repo_path" not in st.session_state:
    st.session_state["repo_path"] = ""

st.markdown('<div class="main-title"><h1>🔍 GitHub Repository Intelligence Tool</h1><p>Static Code Analysis Dashboard for Python Repositories</p></div>', unsafe_allow_html=True)

st.sidebar.title("Configuration & History")

# Scan Form
st.sidebar.subheader("Scan New Repository")
scan_path = st.sidebar.text_input("Local Repository Path", placeholder="C:/path/to/my-python-project")
scan_button = st.sidebar.button("Run Intelligence Scan", type="primary")

if scan_button:
    clean_path = scan_path.strip().strip('"').strip("'")
    if not clean_path:
        st.sidebar.error("Please enter a valid path.")
    elif not os.path.exists(clean_path) or not os.path.isdir(clean_path):
        st.sidebar.error(f"Path does not exist or is not a directory: {clean_path}")
    else:
        with st.spinner("Analyzing repository (running parser, duplicate scanner, security and complexity checks)..."):
            try:
                repo_id = run_repository_analysis(clean_path)
                st.session_state["repo_id"] = repo_id
                st.session_state["repo_path"] = clean_path
                st.sidebar.success(f"Analysis completed successfully!")
            except Exception as e:
                st.sidebar.error(f"Analysis failed: {e}")
                logger.error("Scan failed", exc_info=True)

# Selector Form
st.sidebar.subheader("Select Past Analysis")
past_repos = db.get_repositories()
if past_repos:
    repo_options = {f"{r.path} (Score: {r.health_score} | {r.scanned_at.split('T')[0]})": r.id for r in past_repos}
    selected_option = st.sidebar.selectbox("Scanned Repositories", list(repo_options.keys()))
    if selected_option:
        st.session_state["repo_id"] = repo_options[selected_option]
        repo_obj = db.get_repository_by_id(st.session_state["repo_id"])
        if repo_obj:
            st.session_state["repo_path"] = repo_obj.path
else:
    st.sidebar.info("No scan history found. Run a new scan above.")

# Main Dashboard Frame
if st.session_state["repo_id"]:
    repo_id = st.session_state["repo_id"]
    repo = db.get_repository_by_id(repo_id)
    metrics = db.get_metrics_by_repo_id(repo_id)
    
    if repo and metrics:
        st.subheader("Repository Overview")
        
        col_health, col_stats = st.columns([1, 2])
        
        with col_health:
            st.markdown(f"""
            <div class="metric-card" style="padding: 30px;">
                <div class="metric-label">Overall Health Score</div>
                <div class="health-value">{repo.health_score}</div>
                <div class="metric-label" style="margin-top:10px;">Status: {repo.status}</div>
            </div>
            """, unsafe_allow_html=True)
            
        with col_stats:
            c1, c2, c3 = st.columns(3)
            with c1:
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-label">Total Files</div>
                    <div class="metric-value">{metrics.total_files}</div>
                </div>
                """, unsafe_allow_html=True)
            with c2:
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-label">Python Files</div>
                    <div class="metric-value">{metrics.python_files}</div>
                </div>
                """, unsafe_allow_html=True)
            with c3:
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-label">Total Lines</div>
                    <div class="metric-value">{metrics.total_lines}</div>
                </div>
                """, unsafe_allow_html=True)
                
            st.markdown(f"""
            <div style="margin-top: 20px; padding: 15px; background: #0f172a; border-radius: 8px; border: 1px solid #1e293b;">
                <p><b>Target Path:</b> <code>{repo.path}</code></p>
                <p><b>Scanned At:</b> {repo.scanned_at}</p>
            </div>
            """, unsafe_allow_html=True)
            
        st.markdown("---")
        
        st.subheader("Summary Breakdown")
        
        from visualization.charts import create_code_comment_pie
        fig = create_code_comment_pie(metrics.code_lines, metrics.comment_lines, metrics.blank_lines)
        st.plotly_chart(fig, use_container_width=True)

        st.info("💡 Navigation Tip: Use the pages in the sidebar to drill down into detailed Metrics, Complexity, Dependencies, Security, Documentation, Duplicates, and Reports.")
else:
    st.info("👈 Please enter a local Python repository path and click **Run Intelligence Scan** or select a past analysis from the sidebar to begin.")
