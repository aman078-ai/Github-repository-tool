import sys
from pathlib import Path
import streamlit as st

root_path = Path(__file__).resolve().parent.parent.parent
if str(root_path) not in sys.path:
    sys.path.insert(0, str(root_path))

from database.database import DatabaseManager
from visualization.charts import create_security_risk_chart

st.set_page_config(page_title="Security - Intelligence Tool", layout="wide")

db = DatabaseManager()

if "repo_id" in st.session_state and st.session_state["repo_id"]:
    repo_id = st.session_state["repo_id"]
    issues_data = db.get_security_issues_by_repo_id(repo_id)
    
    st.title("🛡️ Security Risk Scanner")
    st.write("Scans Python code blocks and AST structures to discover credentials leak or unsafe evaluations.")
    
    if issues_data:
        issues_list = [issue for _, issue in issues_data]
        
        col1, col2 = st.columns([1, 1])
        
        with col1:
            st.plotly_chart(create_security_risk_chart(issues_list), use_container_width=True)
            
        with col2:
            st.subheader("Security Severity Guide")
            st.markdown("""
            - **Critical**: Hardcoded keys (AWS Keys, Private Keys). High risk of immediate system exploit. Remove from git history immediately!
            - **High**: Dangerous functions (`eval()`, `exec()`, `os.system()`, subprocess with `shell=True`). High potential for command injection or RCE.
            - **Medium**: Insecure deserialization patterns (`pickle.load()`) or potential credential assignments.
            - **Low**: Non-standard variables or warnings.
            """)
            
        st.markdown("---")
        st.subheader("Identified Security Risks")
        
        for file_model, issue in issues_data:
            severity_color = {
                "Critical": "🔴 Critical",
                "High": "🟠 High",
                "Medium": "🟡 Medium",
                "Low": "🔵 Low"
            }.get(issue.severity, issue.severity)
            
            with st.expander(f"{severity_color} - {issue.issue_type} in {file_model.filepath}:{issue.line_number}"):
                st.markdown(f"**Description:** {issue.description}")
                st.markdown("**Code Snippet:**")
                st.code(issue.code_snippet, language="python")
    else:
        st.success("🎉 **No Security Risks Detected!** Your codebase passed all static credential scans and safe call checks.")
else:
    st.warning("Please select or scan a repository on the main dashboard first.")
