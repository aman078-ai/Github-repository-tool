import sys
from pathlib import Path
import streamlit as st

root_path = Path(__file__).resolve().parent.parent.parent
if str(root_path) not in sys.path:
    sys.path.insert(0, str(root_path))

from database.database import DatabaseManager
from analyzer.repository import RepositoryScanner
from analyzer.dependencies import DependencyAnalyzer
from visualization.dependency_graph import generate_interactive_graph

st.set_page_config(page_title="Dependencies - Intelligence Tool", layout="wide")

db = DatabaseManager()

if "repo_id" in st.session_state and st.session_state["repo_id"]:
    repo_id = st.session_state["repo_id"]
    repo = db.get_repository_by_id(repo_id)
    
    st.title("🔗 Dependency & Call Graph Analyzer")
    st.write(f"Analyzing: `{repo.path}`")
    
    with st.spinner("Generating dependency graph from workspace code..."):
        try:
            scanner = RepositoryScanner(repo.path)
            parsed_files = scanner.parse_repository()
            
            analyzer = DependencyAnalyzer(scanner.root_path, parsed_files)
            import_graph = analyzer.build_import_graph()
            call_graph = analyzer.build_call_graph()
            circular_loops = analyzer.detect_circular_dependencies()
            
            if circular_loops:
                st.error("🚨 **Circular Dependencies Detected!**")
                for idx, loop in enumerate(circular_loops, 1):
                    loop_str = " ➔ ".join(loop) + " ➔ " + loop[0]
                    st.markdown(f"**Cycle {idx}**: `{loop_str}`")
            else:
                st.success("✅ **No Circular Dependencies Detected!** Your module import tree is clean.")
                
            tab_import, tab_call = st.tabs(["Module Import Graph", "Function Call Graph"])
            
            with tab_import:
                st.subheader("Module Graph")
                st.write("Visualizes import relationships between files. Arrow points to the imported file.")
                fig_import = generate_interactive_graph(import_graph, "Workspace Module Import Graph")
                st.plotly_chart(fig_import, use_container_width=True)
                
            with tab_call:
                st.subheader("Function Call Graph")
                st.write("Visualizes static function call hierarchies. Hover over nodes to see connections.")
                fig_call = generate_interactive_graph(call_graph, "Function Call Graph")
                st.plotly_chart(fig_call, use_container_width=True)
                
        except Exception as e:
            st.error(f"Error loading dependencies: {e}")
else:
    st.warning("Please select or scan a repository on the main dashboard first.")
