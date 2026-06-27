import sys
from pathlib import Path
import streamlit as st

root_path = Path(__file__).resolve().parent.parent.parent
if str(root_path) not in sys.path:
    sys.path.insert(0, str(root_path))

from database.database import DatabaseManager
from utils.helpers import format_size
from visualization.charts import create_code_comment_pie

st.set_page_config(page_title="Metrics - Intelligence Tool", layout="wide")

db = DatabaseManager()

if "repo_id" in st.session_state and st.session_state["repo_id"]:
    repo_id = st.session_state["repo_id"]
    metrics = db.get_metrics_by_repo_id(repo_id)
    
    st.title("📊 Detailed Codebase Metrics")
    st.write("Detailed line counts and frequency distributions for the target workspace.")
    
    if metrics:
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Physical Metrics")
            st.markdown(f"""
            - **Total Scanned Files**: `{metrics.total_files}`
            - **Python Files**: `{metrics.python_files}`
            - **Total Lines**: `{metrics.total_lines}`
            - **Blank Lines**: `{metrics.blank_lines}`
            - **Comment Lines**: `{metrics.comment_lines}`
            - **Source Code Lines**: `{metrics.code_lines}`
            """)
            
            st.subheader("Size Statistics")
            st.markdown(f"""
            - **Average File Size**: `{format_size(metrics.average_file_size)}`
            - **Largest File**: `{metrics.largest_file}`
            - **Smallest File**: `{metrics.smallest_file}`
            """)
            
            st.subheader("Frequencies")
            st.markdown(f"""
            - **Average Functions per File**: `{round(metrics.average_functions_per_file, 2)}`
            - **Average Classes per File**: `{round(metrics.average_classes_per_file, 2)}`
            """)

        with col2:
            st.subheader("Line Composition Summary")
            fig = create_code_comment_pie(metrics.code_lines, metrics.comment_lines, metrics.blank_lines)
            st.plotly_chart(fig, use_container_width=True)
else:
    st.warning("Please select or scan a repository on the main dashboard first.")
