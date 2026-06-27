import ast
from pathlib import Path
from typing import Dict, List, Set, Tuple
from analyzer.parser import ParsedFile
from utils.logger import logger

class DeadCodeDetector:
    def __init__(self, root_path: Path, parsed_files: Dict[str, ParsedFile]):
        self.root_path = root_path
        self.parsed_files = parsed_files
        self.local_modules: Set[str] = set()
        for rel_path in parsed_files.keys():
            parts = Path(rel_path).with_suffix("").parts
            module_name = ".".join(parts)
            self.local_modules.add(module_name)
            if Path(rel_path).name == "__init__.py":
                self.local_modules.add(".".join(Path(rel_path).parent.parts))

    def detect_dead_code(self) -> Dict[str, List[str]]:
        """Scans the codebase to detect unused files, classes, functions, imports, and variables."""
        logger.info("Detecting dead code across codebase...")
        
        unused_files: List[str] = []
        unused_classes: List[Tuple[str, str, int]] = []
        unused_functions: List[Tuple[str, str, int]] = []
        unused_imports: List[Tuple[str, str, int]] = []
        unused_variables: List[Tuple[str, str, int]] = []
        
        all_referenced_names: Set[str] = set()
        all_referenced_modules: Set[str] = set()
        
        defined_functions: Dict[str, List[Tuple[str, int]]] = {}
        defined_classes: Dict[str, List[Tuple[str, int]]] = {}
        
        file_references: Dict[str, Set[str]] = {}

        for rel_path, parsed in self.parsed_files.items():
            file_references[rel_path] = set()
            try:
                tree = ast.parse(parsed.raw_content)
                for node in ast.walk(tree):
                    if isinstance(node, ast.Name):
                        if isinstance(node.ctx, ast.Load):
                            all_referenced_names.add(node.id)
                            file_references[rel_path].add(node.id)
                    elif isinstance(node, ast.Attribute):
                        all_referenced_names.add(node.attr)
                        file_references[rel_path].add(node.attr)
                    elif isinstance(node, (ast.Import, ast.ImportFrom)):
                        if isinstance(node, ast.Import):
                            for name in node.names:
                                all_referenced_modules.add(name.name)
                        else:
                            if node.module:
                                all_referenced_modules.add(node.module)
                                for alias in node.names:
                                    all_referenced_modules.add(f"{node.module}.{alias.name}")
            except Exception as e:
                logger.error(f"Error collecting references for {rel_path}: {e}")

            for func in parsed.functions:
                if func.name not in defined_functions:
                    defined_functions[func.name] = []
                defined_functions[func.name].append((rel_path, func.start_line))
                
            for cls in parsed.classes:
                if cls.name not in defined_classes:
                    defined_classes[cls.name] = []
                defined_classes[cls.name].append((rel_path, cls.start_line))

        # Filter out entry points
        entry_points = {"streamlit_app.py", "setup.py", "main.py", "app.py"}
        for rel_path in self.parsed_files:
            if Path(rel_path).name in entry_points:
                continue
                
            parts = Path(rel_path).with_suffix("").parts
            mod_name = ".".join(parts)
            
            is_referenced = False
            for ref_mod in all_referenced_modules:
                if ref_mod == mod_name or ref_mod.startswith(mod_name + "."):
                    is_referenced = True
                    break
                    
            if not is_referenced:
                unused_files.append(rel_path)

        for name, defs in defined_functions.items():
            # Exclude pytest methods and double-under magic methods
            if name.startswith("test_") or (name.startswith("__") and name.endswith("__")):
                continue
            if name not in all_referenced_names:
                for filepath, line in defs:
                    unused_functions.append((filepath, name, line))

        for name, defs in defined_classes.items():
            if name.startswith("Test"):
                continue
            if name not in all_referenced_names:
                for filepath, line in defs:
                    unused_classes.append((filepath, name, line))

        for rel_path, parsed in self.parsed_files.items():
            refs_in_file = file_references.get(rel_path, set())
            for imp in parsed.imports:
                imported_name = imp.alias if imp.alias else imp.name
                if imported_name not in refs_in_file:
                    unused_imports.append((rel_path, imported_name, imp.line_number))

        for rel_path, parsed in self.parsed_files.items():
            refs_in_file = file_references.get(rel_path, set())
            for var in parsed.variables:
                if var.name.startswith("_") or var.name == "__all__":
                    continue
                if var.name not in refs_in_file:
                    if var.name not in all_referenced_names:
                        unused_variables.append((rel_path, var.name, var.line_number))

        report_data: Dict[str, List[str]] = {
            "unused_files": unused_files,
            "unused_classes": [f"{f}:{l} - Class '{n}' is defined but never referenced." for f, n, l in unused_classes],
            "unused_functions": [f"{f}:{l} - Function '{n}' is defined but never referenced." for f, n, l in unused_functions],
            "unused_imports": [f"{f}:{l} - Import '{n}' is declared but never used in the file." for f, n, l in unused_imports],
            "unused_variables": [f"{f}:{l} - Variable '{n}' is assigned but never referenced." for f, n, l in unused_variables]
        }
        
        return report_data
