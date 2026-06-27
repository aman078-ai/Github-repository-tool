import ast
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional
import networkx as nx
from analyzer.parser import ParsedFile
from utils.logger import logger

class DependencyAnalyzer:
    def __init__(self, root_path: Path, parsed_files: Dict[str, ParsedFile]):
        self.root_path = root_path
        self.parsed_files = parsed_files
        self.module_graph = nx.DiGraph()
        self.call_graph = nx.DiGraph()
        
        # Build local module dictionary for import resolution
        self.local_modules: Dict[str, str] = {}
        for rel_path in parsed_files.keys():
            parts = Path(rel_path).with_suffix("").parts
            module_name = ".".join(parts)
            self.local_modules[module_name] = rel_path
            if Path(rel_path).name == "__init__.py":
                package_module = ".".join(Path(rel_path).parent.parts)
                self.local_modules[package_module] = rel_path

    def _resolve_import(self, importing_file: str, imp_name: str, imp_module: Optional[str], is_from: bool) -> Optional[str]:
        """Attempts to resolve an import statement to a local file in the workspace."""
        target_mod = imp_module if is_from else imp_name
        if not target_mod:
            return None

        # Exact match
        if target_mod in self.local_modules:
            return self.local_modules[target_mod]

        # Relative import support
        if is_from and imp_module and imp_module.startswith("."):
            dots_count = 0
            for char in imp_module:
                if char == ".":
                    dots_count += 1
                else:
                    break
            
            sub_mod = imp_module[dots_count:]
            curr_parent = Path(importing_file).parent
            for _ in range(dots_count - 1):
                if curr_parent.parent:
                    curr_parent = curr_parent.parent
            
            rel_parts = list(curr_parent.parts)
            if sub_mod:
                rel_parts.extend(sub_mod.split("."))
            
            resolved_mod = ".".join(rel_parts)
            if resolved_mod in self.local_modules:
                return self.local_modules[resolved_mod]
                
        # Sub-module resolution support
        parts = target_mod.split(".")
        for i in range(len(parts), 0, -1):
            sub_mod = ".".join(parts[:i])
            if sub_mod in self.local_modules:
                return self.local_modules[sub_mod]
                
        return None

    def build_import_graph(self) -> nx.DiGraph:
        """Constructs the module/import dependency graph."""
        self.module_graph.clear()
        
        for rel_path in self.parsed_files:
            self.module_graph.add_node(rel_path)

        for rel_path, parsed in self.parsed_files.items():
            for imp in parsed.imports:
                target_file = self._resolve_import(rel_path, imp.name, imp.module, imp.is_from)
                if target_file and target_file != rel_path:
                    self.module_graph.add_edge(rel_path, target_file)
                    
        return self.module_graph

    def detect_circular_dependencies(self) -> List[List[str]]:
        """Finds loops (cycles) of imports in the module graph."""
        if not self.module_graph.nodes:
            self.build_import_graph()
        return list(nx.simple_cycles(self.module_graph))

    def build_call_graph(self) -> nx.DiGraph:
        """Constructs the function call graph by examining ast.Call nodes."""
        self.call_graph.clear()
        
        func_identifiers: Set[str] = set()
        func_nodes: Dict[str, Tuple[str, Optional[str], str]] = {}
        
        for rel_path, parsed in self.parsed_files.items():
            for func in parsed.functions:
                node_id = f"{rel_path}::{func.class_name + '.' if func.class_name else ''}{func.name}"
                func_identifiers.add(node_id)
                func_nodes[node_id] = (rel_path, func.class_name, func.name)
                self.call_graph.add_node(node_id)

        for rel_path, parsed in self.parsed_files.items():
            try:
                tree = ast.parse(parsed.raw_content)
                for node in ast.walk(tree):
                    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        matching_model = None
                        for f in parsed.functions:
                            if f.name == node.name and f.start_line <= node.lineno <= f.end_line:
                                matching_model = f
                                break
                        
                        if not matching_model:
                            continue
                            
                        caller_id = f"{rel_path}::{matching_model.class_name + '.' if matching_model.class_name else ''}{matching_model.name}"
                        
                        for child in ast.walk(node):
                            if isinstance(child, ast.Call):
                                called_func_name = None
                                if isinstance(child.func, ast.Name):
                                    called_func_name = child.func.id
                                elif isinstance(child.func, ast.Attribute):
                                    called_func_name = child.func.attr
                                    
                                if not called_func_name:
                                    continue
                                    
                                for target_id, (t_file, t_class, t_name) in func_nodes.items():
                                    if t_name == called_func_name:
                                        if caller_id in self.call_graph and target_id in self.call_graph:
                                            self.call_graph.add_edge(caller_id, target_id)
            except Exception as e:
                logger.error(f"Error parsing call graph for {rel_path}: {e}")
                
        return self.call_graph
