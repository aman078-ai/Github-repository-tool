import os
import sys
from pathlib import Path
import streamlit as st

root_path = Path(__file__).resolve().parent.parent.parent
if str(root_path) not in sys.path:
    sys.path.insert(0, str(root_path))

from database.database import DatabaseManager

st.set_page_config(page_title="Reports - Intelligence Tool", layout="wide")

db = DatabaseManager()

if "repo_id" in st.session_state and st.session_state["repo_id"]:
    repo_id = st.session_state["repo_id"]
    reports = db.get_reports_by_repo_id(repo_id)
    
    st.title("📁 Exported Reports & Summaries")
    st.write("Retrieve and download previously generated code analysis reports in HTML, Markdown, JSON, and CSV format.")
    
    if reports:
        st.success(f"Found {len(reports)} generated files for this analysis run.")
        
        for rep in reports:
            file_p = Path(rep.file_path)
            if not file_p.exists():
                st.warning(f"File {file_p.name} not found on server disk. It might have been deleted.")
                continue
                
            col_info, col_action = st.columns([3, 1])
            with col_info:
                st.markdown(f"📄 **{rep.report_type} Report** ({file_p.name})")
                st.caption(f"Generated at: {rep.generated_at}")
            
            with col_action:
                try:
                    with open(file_p, "rb") as f:
                        btn_data = f.read()
                        
                    mime_types = {
                        "HTML": "text/html",
                        "MD": "text/markdown",
                        "JSON": "application/json",
                        "CSV": "text/csv"
                    }
                    st.download_button(
                        label=f"Download {rep.report_type}",
                        data=btn_data,
                        file_name=file_p.name,
                        mime=mime_types.get(rep.report_type, "text/plain"),
                        key=f"dl_{rep.id}"
                    )
                except Exception as e:
                    st.error(f"Download failed: {e}")
            st.markdown("---")
    else:
        st.info("No report logs exist for the current repository scan.")
else:
    st.warning("Please select or scan a repository on the main dashboard first.")
