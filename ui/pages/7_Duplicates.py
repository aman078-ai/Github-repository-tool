import sys
from pathlib import Path
import streamlit as st

root_path = Path(__file__).resolve().parent.parent.parent
if str(root_path) not in sys.path:
    sys.path.insert(0, str(root_path))

from database.database import DatabaseManager
from analyzer.duplicate_detector import get_refactoring_recommendation

st.set_page_config(page_title="Duplicates - Intelligence Tool", layout="wide")

db = DatabaseManager()

if "repo_id" in st.session_state and st.session_state["repo_id"]:
    repo_id = st.session_state["repo_id"]
    duplicates = db.get_duplicates_by_repo_id(repo_id)
    
    st.title("👥 Duplicate Code Detection")
    st.write("Discovers blocks of duplicated code across your repository using normalisation hashing and similarity ratios.")
    
    if duplicates:
        st.info(f"Detected {len(duplicates)} matching duplicate code blocks. Worst cases are displayed first.")
        
        for idx, dup in enumerate(duplicates, 1):
            with st.expander(f"Match #{idx} - {round(dup.similarity_ratio * 100, 1)}% Similarity ({dup.matching_lines} matching lines)"):
                st.markdown(f"**File 1:** `{dup.file1_path}` (Lines {dup.start_line1} - {dup.end_line1})")
                st.markdown(f"**File 2:** `{dup.file2_path}` (Lines {dup.start_line2} - {dup.end_line2})")
                
                ref_advice = get_refactoring_recommendation(dup)
                st.warning(f"💡 **Refactoring Recommendation:** {ref_advice}")
                
                st.markdown("**Duplicated Snippet Output:**")
                st.code(dup.code_snippet, language="python")
    else:
        st.success("🎉 **No Code Duplications Detected!** Your files look highly modular and clean.")
else:
    st.warning("Please select or scan a repository on the main dashboard first.")
