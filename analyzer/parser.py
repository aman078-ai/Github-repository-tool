import ast
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Any, Tuple
from utils.logger import logger
from utils.helpers import safe_read_file

@dataclass
class ImportData:
    name: str
    alias: Optional[str]
    is_from: bool
    module: Optional[str]
    line_number: int

@dataclass
class VariableData:
    name: str
    line_number: int
    annotation: Optional[str] = None
    is_class_var: bool = False

@dataclass
class FunctionData:
    name: str
    class_name: Optional[str]
    start_line: int
    end_line: int
    decorators: List[str]
    return_type: Optional[str]
    arguments: List[str]
    docstring: Optional[str]
    has_docstring: bool

@dataclass
class ClassData:
    name: str
    start_line: int
    end_line: int
    bases: List[str]
    decorators: List[str]
    docstring: Optional[str]
    has_docstring: bool

@dataclass
class ParsedFile:
    filepath: str
    imports: List[ImportData] = field(default_factory=list)
    variables: List[VariableData] = field(default_factory=list)
    functions: List[FunctionData] = field(default_factory=list)
    classes: List[ClassData] = field(default_factory=list)
    docstring: Optional[str] = None
    has_docstring: bool = False
    total_lines: int = 0
    blank_lines: int = 0
    comment_lines: int = 0
    code_lines: int = 0
    raw_content: str = ""

class FileASTVisitor(ast.NodeVisitor):
    def __init__(self, raw_content: str):
        self.raw_content = raw_content
        self.imports: List[ImportData] = []
        self.variables: List[VariableData] = []
        self.functions: List[FunctionData] = []
        self.classes: List[ClassData] = []
        self._current_class: Optional[str] = None

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            self.imports.append(ImportData(
                name=alias.name,
                alias=alias.asname,
                is_from=False,
                module=None,
                line_number=node.lineno
            ))
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        module = node.module or ""
        for alias in node.names:
            self.imports.append(ImportData(
                name=alias.name,
                alias=alias.asname,
                is_from=True,
                module=module,
                line_number=node.lineno
            ))
        self.generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        doc = ast.get_docstring(node)
        bases = []
        for base in node.bases:
            if isinstance(base, ast.Name):
                bases.append(base.id)
            elif isinstance(base, ast.Attribute) and isinstance(base.value, ast.Name):
                bases.append(f"{base.value.id}.{base.attr}")
            else:
                bases.append(ast.unparse(base) if hasattr(ast, "unparse") else "Unknown")
        
        decorators = [ast.unparse(dec) if hasattr(ast, "unparse") else "decorator" for dec in node.decorator_list]
        
        self.classes.append(ClassData(
            name=node.name,
            start_line=node.lineno,
            end_line=getattr(node, "end_lineno", node.lineno),
            bases=bases,
            decorators=decorators,
            docstring=doc,
            has_docstring=doc is not None
        ))

        previous_class = self._current_class
        self._current_class = node.name
        self.generic_visit(node)
        self._current_class = previous_class

    def _parse_func(self, node: Any) -> None:
        doc = ast.get_docstring(node)
        decorators = [ast.unparse(dec) if hasattr(ast, "unparse") else "decorator" for dec in node.decorator_list]
        args = [arg.arg for arg in node.args.args]
        
        ret_type = None
        if node.returns:
            ret_type = ast.unparse(node.returns) if hasattr(ast, "unparse") else "annotation"

        self.functions.append(FunctionData(
            name=node.name,
            class_name=self._current_class,
            start_line=node.lineno,
            end_line=getattr(node, "end_lineno", node.lineno),
            decorators=decorators,
            return_type=ret_type,
            arguments=args,
            docstring=doc,
            has_docstring=doc is not None
        ))

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._parse_func(node)
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._parse_func(node)
        self.generic_visit(node)

    def visit_Assign(self, node: ast.Assign) -> None:
        if self._current_class is None:
            for target in node.targets:
                if isinstance(target, ast.Name):
                    self.variables.append(VariableData(
                        name=target.id,
                        line_number=node.lineno,
                        is_class_var=False
                    ))
        self.generic_visit(node)

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
        if self._current_class is None:
            if isinstance(node.target, ast.Name):
                ann = ast.unparse(node.annotation) if hasattr(ast, "unparse") else None
                self.variables.append(VariableData(
                    name=node.target.id,
                    line_number=node.lineno,
                    annotation=ann,
                    is_class_var=False
                ))
        self.generic_visit(node)

def count_lines(content: str) -> Tuple[int, int, int, int]:
    """Calculates total lines, blank lines, comment lines, and code lines."""
    lines = content.splitlines()
    total = len(lines)
    blank = 0
    comment = 0
    code = 0
    
    in_multiline = False
    
    for line in lines:
        stripped = line.strip()
        if not stripped:
            blank += 1
            continue
        
        # Simple line checks
        if stripped.startswith("#"):
            comment += 1
        else:
            # If not blank and not starting with a comment, it is code
            code += 1
            
    return total, blank, comment, code

def parse_file(filepath: Path) -> Optional[ParsedFile]:
    """Parses a Python file using AST and returns metadata."""
    try:
        content = safe_read_file(filepath)
        tree = ast.parse(content, filename=str(filepath))
        
        total, blank, comment, code = count_lines(content)
        module_docstring = ast.get_docstring(tree)
        
        visitor = FileASTVisitor(content)
        visitor.visit(tree)
        
        return ParsedFile(
            filepath=str(filepath),
            imports=visitor.imports,
            variables=visitor.variables,
            functions=visitor.functions,
            classes=visitor.classes,
            docstring=module_docstring,
            has_docstring=module_docstring is not None,
            total_lines=total,
            blank_lines=blank,
            comment_lines=comment,
            code_lines=code,
            raw_content=content
        )
    except SyntaxError as e:
        logger.warning(f"Syntax error parsing {filepath}: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error parsing {filepath}: {e}", exc_info=True)
        return None
