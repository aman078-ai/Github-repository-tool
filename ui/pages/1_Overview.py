import sys
from pathlib import Path
import pandas as pd
import streamlit as st

root_path = Path(__file__).resolve().parent.parent.parent
if str(root_path) not in sys.path:
    sys.path.insert(0, str(root_path))

from database.database import DatabaseManager
from visualization.charts import create_large_files_chart

st.set_page_config(page_title="Overview - Intelligence Tool", layout="wide")

db = DatabaseManager()

if "repo_id" in st.session_state and st.session_state["repo_id"]:
    repo_id = st.session_state["repo_id"]
    repo = db.get_repository_by_id(repo_id)
    files = db.get_files_by_repo_id(repo_id)
    
    st.title("📁 Repository File Overview")
    st.write(f"Analyzing: `{repo.path}`")
    st.write("Below is a detailed breakdown of all Python files analyzed in the repository.")
    
    file_data = []
    for f in files:
        file_data.append({
            "File Path": f.filepath,
            "Total Lines": f.total_lines,
            "Source Code Lines": f.code_lines,
            "Comments": f.comment_lines,
            "Blanks": f.blank_lines,
            "Docstring Coverage": f"{round(f.docstring_coverage * 100, 1)}%",
            "Size": f"{round(f.size_bytes / 1024, 2)} KB",
            "Health Score": f.health_score
        })
        
    df = pd.DataFrame(file_data)
    
    search_query = st.text_input("🔍 Search File Path", "")
    if search_query:
        df = df[df["File Path"].str.contains(search_query, case=False)]
        
    st.dataframe(
        df,
        use_container_width=True,
        column_config={
            "Health Score": st.column_config.ProgressColumn(
                "Health Score",
                help="File quality indicator",
                format="%.1f",
                min_value=0,
                max_value=100,
            ),
        }
    )
    
    st.markdown("---")
    st.plotly_chart(create_large_files_chart(files), use_container_width=True)
else:
    st.warning("Please select or scan a repository on the main dashboard first.")
