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

    # Git Version Control Insights
    from utils import git_helper
    repo_path = Path(repo.path)
    if git_helper.is_git_repository(repo_path):
        st.markdown("---")
        st.subheader("📊 Git Version Control Insights")
        st.write("Commit frequencies, hotspots, and active authors extracted from local Git logs.")
        
        col_contributors, col_hotspots = st.columns(2)
        
        with col_contributors:
            st.markdown("### 👥 Top Contributors")
            top_authors = git_helper.get_top_contributors(repo_path, max_authors=5)
            if top_authors:
                df_authors = pd.DataFrame(top_authors)
                st.dataframe(
                    df_authors,
                    use_container_width=True,
                    column_config={
                        "Percentage": st.column_config.ProgressColumn(
                            "Share of Commits",
                            help="Commit share per developer",
                            format="%.1f%%",
                            min_value=0.0,
                            max_value=100.0,
                        )
                    }
                )
            else:
                st.info("No commit history found.")
                
        with col_hotspots:
            st.markdown("### 🔥 Change Hotspots")
            st.write("Files that are modified most frequently. High-frequency modification targets are prime candidates for bugs.")
            hotspots = git_helper.get_file_hotspots(repo_path, max_files=5)
            if hotspots:
                df_hotspots = pd.DataFrame(hotspots)
                st.dataframe(
                    df_hotspots,
                    use_container_width=True,
                    column_config={
                        "Score": st.column_config.ProgressColumn(
                            "Activity Score",
                            help="Percentage of total python changes in this file",
                            format="%.1f%%",
                            min_value=0.0,
                            max_value=100.0,
                        )
                    }
                )
            else:
                st.info("No hotspot files identified.")
else:
    st.warning("Please select or scan a repository on the main dashboard first.")
