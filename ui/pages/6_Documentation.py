import sys
from pathlib import Path
import pandas as pd
import streamlit as st

root_path = Path(__file__).resolve().parent.parent.parent
if str(root_path) not in sys.path:
    sys.path.insert(0, str(root_path))

from database.database import DatabaseManager
from analyzer.repository import RepositoryScanner
from analyzer.documentation import analyze_documentation
from visualization.charts import create_doc_coverage_chart

st.set_page_config(page_title="Documentation - Intelligence Tool", layout="wide")

db = DatabaseManager()

if "repo_id" in st.session_state and st.session_state["repo_id"]:
    repo_id = st.session_state["repo_id"]
    repo = db.get_repository_by_id(repo_id)
    files = db.get_files_by_repo_id(repo_id)
    
    st.title("📚 Documentation Quality Analyzer")
    st.write("Inspects docstring presence and estimates documentation score.")
    
    with st.spinner("Analyzing docstrings..."):
        try:
            scanner = RepositoryScanner(repo.path)
            parsed_files = scanner.parse_repository()
            doc_results = analyze_documentation(scanner.root_path, parsed_files)
            
            col1, col2 = st.columns([1, 1])
            
            with col1:
                st.plotly_chart(create_doc_coverage_chart(doc_results), use_container_width=True)
                
            with col2:
                st.subheader("Documentation Health Details")
                st.markdown(f"**Overall Documentation Quality Score:** `{doc_results['score']}/100`")
                
                readme_status = "✅ Found" if doc_results["readme_exists"] else "❌ Missing"
                license_status = "✅ Found" if doc_results["license_exists"] else "❌ Missing"
                st.markdown(f"- **README File**: {readme_status}")
                st.markdown(f"- **LICENSE File**: {license_status}")
                st.markdown(f"- **Modules Count**: {doc_results['total_modules']} ({doc_results['modules_with_docstrings']} documented)")
                st.markdown(f"- **Classes Count**: {doc_results['total_classes']} ({doc_results['classes_with_docstrings']} documented)")
                st.markdown(f"- **Functions Count**: {doc_results['total_functions']} ({doc_results['functions_with_docstrings']} documented)")
                
            st.markdown("---")
            st.subheader("File Docstring Coverage Details")
            
            rows = []
            for file_model in files:
                rel_path = file_model.filepath
                parsed = parsed_files.get(rel_path)
                
                has_mod_doc = "Yes" if parsed and parsed.has_docstring else "No"
                funcs_count = len(parsed.functions) if parsed else 0
                funcs_doc = sum(1 for f in parsed.functions if f.has_docstring) if parsed else 0
                classes_count = len(parsed.classes) if parsed else 0
                classes_doc = sum(1 for c in parsed.classes if c.has_docstring) if parsed else 0
                
                rows.append({
                    "File Path": rel_path,
                    "Module Docstring": has_mod_doc,
                    "Classes Count": classes_count,
                    "Classes Documented": classes_doc,
                    "Functions Count": funcs_count,
                    "Functions Documented": funcs_doc,
                    "File Coverage": file_model.docstring_coverage
                })
                
            df = pd.DataFrame(rows)
            df.sort_values(by="File Coverage", ascending=True, inplace=True)
            
            st.dataframe(
                df,
                use_container_width=True,
                column_config={
                    "File Coverage": st.column_config.ProgressColumn(
                        "Coverage",
                        help="Documentation coverage ratio",
                        format="%.1f%%",
                        min_value=0,
                        max_value=1.0,
                    ),
                }
            )
        except Exception as e:
            st.error(f"Error analyzing documentation: {e}")
else:
    st.warning("Please select or scan a repository on the main dashboard first.")
