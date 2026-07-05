import sys
from pathlib import Path
import pandas as pd
import streamlit as st

root_path = Path(__file__).resolve().parent.parent.parent
if str(root_path) not in sys.path:
    sys.path.insert(0, str(root_path))

from database.database import DatabaseManager
from analyzer.repository import RepositoryScanner
from analyzer.dead_code import DeadCodeDetector

st.set_page_config(page_title="Dead Code - Intelligence Tool", layout="wide")

db = DatabaseManager()

if "repo_id" in st.session_state and st.session_state["repo_id"]:
    repo_id = st.session_state["repo_id"]
    repo = db.get_repository_by_id(repo_id)
    
    st.title("💀 Dead Code & Unused Elements Analyzer")
    st.write("Identifies unused modules, classes, functions, imports, and variables across your codebase to keep your repository clean.")
    st.write(f"Analyzing: `{repo.path}`")
    
    with st.spinner("Analyzing codebase references..."):
        try:
            scanner = RepositoryScanner(repo.path)
            parsed_files = scanner.parse_repository()
            
            detector = DeadCodeDetector(scanner.root_path, parsed_files)
            dead_code = detector.detect_dead_code()
            
            unused_files = dead_code.get("unused_files", [])
            unused_classes = dead_code.get("unused_classes", [])
            unused_functions = dead_code.get("unused_functions", [])
            unused_imports = dead_code.get("unused_imports", [])
            unused_variables = dead_code.get("unused_variables", [])
            
            total_dead_items = len(unused_files) + len(unused_classes) + len(unused_functions) + len(unused_imports) + len(unused_variables)
            
            if total_dead_items == 0:
                st.success("🎉 **Clean Codebase!** No dead code or unused elements were found. Outstanding job!")
            else:
                st.warning(f"⚠️ Found **{total_dead_items}** potentially unused/dead code items in the repository.")
                
                # Metric Cards
                c1, c2, c3, c4, c5 = st.columns(5)
                c1.metric("Unused Files", len(unused_files))
                c2.metric("Unused Classes", len(unused_classes))
                c3.metric("Unused Functions", len(unused_functions))
                c4.metric("Unused Imports", len(unused_imports))
                c5.metric("Unused Variables", len(unused_variables))
                
                st.markdown("---")
                
                tab_files, tab_classes, tab_funcs, tab_imports, tab_vars = st.tabs([
                    "📁 Unused Files",
                    "🏛️ Unused Classes",
                    "⚙️ Unused Functions",
                    "📤 Unused Imports",
                    "📦 Unused Variables"
                ])
                
                with tab_files:
                    st.subheader("Unused Files")
                    st.write("These Python files are never imported or referenced in the workspace entry points. If they are obsolete scripts or tests that are no longer run, consider removing them.")
                    if unused_files:
                        df_files = pd.DataFrame({"File Path": unused_files})
                        st.dataframe(df_files, use_container_width=True)
                    else:
                        st.success("No unused files detected.")
                        
                with tab_classes:
                    st.subheader("Unused Classes")
                    st.write("These classes are defined but never referenced or instantiated. Dead classes add bloat and can be safely deleted if no external tools call them.")
                    if unused_classes:
                        # Parse the custom format "file:line - description"
                        class_rows = []
                        for item in unused_classes:
                            parts = item.split(" - ")
                            file_line = parts[0]
                            desc = parts[1] if len(parts) > 1 else ""
                            class_rows.append({"Location": file_line, "Details": desc})
                        st.dataframe(pd.DataFrame(class_rows), use_container_width=True)
                    else:
                        st.success("No unused classes detected.")
                        
                with tab_funcs:
                    st.subheader("Unused Functions / Methods")
                    st.write("These functions are defined but not called anywhere. Unused functions might indicate dead codepaths or incomplete features.")
                    if unused_functions:
                        func_rows = []
                        for item in unused_functions:
                            parts = item.split(" - ")
                            file_line = parts[0]
                            desc = parts[1] if len(parts) > 1 else ""
                            func_rows.append({"Location": file_line, "Details": desc})
                        st.dataframe(pd.DataFrame(func_rows), use_container_width=True)
                    else:
                        st.success("No unused functions detected.")
                        
                with tab_imports:
                    st.subheader("Unused Imports")
                    st.write("These modules are imported in a file but never used within that same file. Removing unused imports speeds up loading and keeps the imports clean.")
                    if unused_imports:
                        import_rows = []
                        for item in unused_imports:
                            parts = item.split(" - ")
                            file_line = parts[0]
                            desc = parts[1] if len(parts) > 1 else ""
                            import_rows.append({"Location": file_line, "Details": desc})
                        st.dataframe(pd.DataFrame(import_rows), use_container_width=True)
                    else:
                        st.success("No unused imports detected.")
                        
                with tab_vars:
                    st.subheader("Unused Variables")
                    st.write("These variables are assigned a value but never referenced or read. They might represent forgotten calculations or leftover copy-paste code.")
                    if unused_variables:
                        var_rows = []
                        for item in unused_variables:
                            parts = item.split(" - ")
                            file_line = parts[0]
                            desc = parts[1] if len(parts) > 1 else ""
                            var_rows.append({"Location": file_line, "Details": desc})
                        st.dataframe(pd.DataFrame(var_rows), use_container_width=True)
                    else:
                        st.success("No unused variables detected.")
                        
        except Exception as e:
            st.error(f"Error running dead code detection: {e}")
            st.exception(e)
else:
    st.warning("Please select or scan a repository on the main dashboard first.")
