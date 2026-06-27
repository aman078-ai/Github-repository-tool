import sys
from pathlib import Path
import pandas as pd
import streamlit as st

root_path = Path(__file__).resolve().parent.parent.parent
if str(root_path) not in sys.path:
    sys.path.insert(0, str(root_path))

from database.database import DatabaseManager
from visualization.charts import create_complexity_distribution_chart

st.set_page_config(page_title="Complexity - Intelligence Tool", layout="wide")

db = DatabaseManager()

if "repo_id" in st.session_state and st.session_state["repo_id"]:
    repo_id = st.session_state["repo_id"]
    all_funcs = db.get_all_functions_by_repo_id(repo_id)
    
    st.title("⚡ Cyclomatic Complexity Analysis")
    st.write("Measures the code paths in your functions using Radon to highlight worst-offending routines.")
    
    if all_funcs:
        funcs_list = [f_model for _, f_model in all_funcs]
        
        col1, col2 = st.columns([1, 1])
        
        with col1:
            st.plotly_chart(create_complexity_distribution_chart(funcs_list), use_container_width=True)
            
        with col2:
            st.subheader("Complexity Categorization Help")
            st.markdown("""
            - **Low (1 - 5)**: Standard simple code. Low risk.
            - **Medium (6 - 10)**: Moderately complex structure. Moderate risk. Consider splitting.
            - **High (11 - 20)**: Complex code. High risk. Refactoring highly recommended.
            - **Very High (21+)**: Extreme complexity. Very high risk. Prone to bugs and hard to test. Refactor immediately!
            """)
            
        st.markdown("---")
        st.subheader("Functions & Methods Ranking")
        
        rows = []
        for file_model, func_model in all_funcs:
            rows.append({
                "Function Name": func_model.name,
                "Class Name": func_model.class_name or "Global",
                "File Path": file_model.filepath,
                "Complexity": func_model.complexity,
                "Category": func_model.complexity_category,
                "Lines": f"{func_model.start_line} - {func_model.end_line}",
                "Docstring": "Yes" if func_model.has_docstring else "No"
            })
            
        df = pd.DataFrame(rows)
        df.sort_values(by="Complexity", ascending=False, inplace=True)
        
        st.dataframe(
            df,
            use_container_width=True,
            column_config={
                "Complexity": st.column_config.NumberColumn(
                    "Complexity",
                    help="Cyclomatic complexity score",
                    format="%d",
                ),
            }
        )
    else:
        st.info("No functions identified to analyze cyclomatic complexity.")
else:
    st.warning("Please select or scan a repository on the main dashboard first.")
