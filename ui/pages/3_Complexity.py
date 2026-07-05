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
        
        # Bug Risk Prediction
        st.markdown("---")
        st.subheader("⚠️ Statically Predicted Bug Risks")
        st.write("Statically analyzes the codebase's logical structure using local heuristics to spot high-risk coding practices.")
        
        try:
            from analyzer.repository import RepositoryScanner
            from analyzer.ai_interfaces import LocalBugRiskPredictor
            
            repo = db.get_repository_by_id(repo_id)
            scanner = RepositoryScanner(repo.path)
            parsed_files = scanner.parse_repository()
            
            predictor = LocalBugRiskPredictor()
            all_bug_risks = []
            
            # Map file paths to their complexity to scale the risk
            file_max_complexities = {}
            for file_model, comp_model in db.get_complexity_summaries_by_repo_id(repo_id):
                file_max_complexities[file_model.filepath] = comp_model.max_complexity
                
            for rel_path, parsed in parsed_files.items():
                comp_score = file_max_complexities.get(rel_path, 1)
                risks = predictor.predict_bug_risks(parsed.raw_content, comp_score)
                for risk in risks:
                    all_bug_risks.append({
                        "File Path": rel_path,
                        "Line": risk["line_number"],
                        "Risk Score": risk["risk_score"],
                        "Category": risk["category"],
                        "Description & Recommendations": risk["reason"]
                    })
            
            if all_bug_risks:
                df_risks = pd.DataFrame(all_bug_risks)
                df_risks.sort_values(by="Risk Score", ascending=False, inplace=True)
                st.dataframe(
                    df_risks,
                    use_container_width=True,
                    column_config={
                        "Risk Score": st.column_config.ProgressColumn(
                            "Risk Score",
                            help="Calculated probability / severity of bugs",
                            format="%.2f",
                            min_value=0.0,
                            max_value=1.0,
                        )
                    }
                )
            else:
                st.success("🎉 **No static bug risks predicted!** Code structures look clean and follow standard best practices.")
        except Exception as e:
            st.error(f"Error executing bug risk prediction: {e}")
            
    else:
        st.info("No functions identified to analyze cyclomatic complexity.")
else:
    st.warning("Please select or scan a repository on the main dashboard first.")
