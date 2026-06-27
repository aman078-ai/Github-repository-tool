import os
import sqlite3
import pytest
from pathlib import Path
from database.models import RepositoryModel, FileModel, FunctionModel, MetricsModel, SecurityIssueModel, ComplexitySummaryModel, DuplicateCodeModel
from database.database import DatabaseManager
from analyzer.parser import count_lines, parse_file, ParsedFile
from analyzer.metrics import calculate_metrics
from analyzer.complexity import get_complexity_category, analyze_complexity, merge_parser_and_complexity
from analyzer.duplicate_detector import clean_and_normalize_lines, find_duplicates, get_refactoring_recommendation
from analyzer.security import scan_security
from analyzer.documentation import analyze_documentation

@pytest.fixture
def temp_db(tmp_path):
    db_file = tmp_path / "test_repo_intel.db"
    db = DatabaseManager(str(db_file))
    db.init_db()
    return db

def test_line_counter():
    code = "x = 1\n\n# comment\ny = 2"
    total, blank, comment, code_lines = count_lines(code)
    assert total == 4
    assert blank == 1
    assert comment == 1
    assert code_lines == 2

def test_parser_valid(tmp_path):
    file_p = tmp_path / "valid.py"
    code = """
import os

class MyClass:
    def method(self, val: int) -> str:
        '''Docstring details'''
        x = 5
        return "hello"
"""
    file_p.write_text(code, encoding="utf-8")
    parsed = parse_file(file_p)
    assert parsed is not None
    assert len(parsed.imports) == 1
    assert len(parsed.classes) == 1
    assert len(parsed.functions) == 1
    assert parsed.classes[0].name == "MyClass"
    assert parsed.functions[0].name == "method"
    assert parsed.functions[0].return_type == "str"
    assert parsed.functions[0].has_docstring is True

def test_parser_syntax_error(tmp_path):
    file_p = tmp_path / "invalid.py"
    code = "class MyClass"
    file_p.write_text(code, encoding="utf-8")
    parsed = parse_file(file_p)
    assert parsed is None

def test_complexity_calculations():
    assert get_complexity_category(3) == "Low"
    assert get_complexity_category(8) == "Medium"
    assert get_complexity_category(15) == "High"
    assert get_complexity_category(25) == "Very High"
    
    code = """
def simple_func():
    return 1

def complex_func(a, b):
    if a > b:
        if a > 10:
            return a
    return b
"""
    funcs, summary = analyze_complexity("test_file.py", code)
    assert len(funcs) == 2
    assert summary is not None
    assert summary.max_complexity >= 3

def test_duplicate_detector():
    code1 = """
def process_data(data):
    # Some comment
    x = data * 2
    y = x + 10
    z = y / 5
    return z
"""
    code2 = """
def compute_values(data):
    # Another comment here
    x = data * 2
    y = x + 10
    z = y / 5
    return z
"""
    parsed1 = ParsedFile(
        filepath="file1.py",
        raw_content=code1,
        total_lines=7,
        blank_lines=0,
        comment_lines=1,
        code_lines=6
    )
    parsed2 = ParsedFile(
        filepath="file2.py",
        raw_content=code2,
        total_lines=7,
        blank_lines=0,
        comment_lines=1,
        code_lines=6
    )
    
    parsed_files = {"file1.py": parsed1, "file2.py": parsed2}
    dups = find_duplicates(parsed_files)
    assert dups[0].file1_path == "file1.py" and dups[0].file2_path == "file2.py"
    
    advice = get_refactoring_recommendation(dups[0])
    assert any(w in advice.lower() for w in ["helper", "extract", "similarity", "identical", "duplicate"])

def test_security_scanner():
    code = """
import os
import subprocess

AWS_KEY = "AKIA1234567890123456"
eval("x = 1")
subprocess.run("ls", shell=True)
"""
    issues = scan_security("unsafe.py", code)
    issue_types = [issue.issue_type for issue in issues]
    assert "Hardcoded AWS Access Key" in issue_types
    assert "Dangerous Function (eval)" in issue_types
    assert "Subprocess Command Injection (shell=True)" in issue_types

def test_database_manager(temp_db):
    repo = RepositoryModel(None, "test/repo", "2026-06-27T00:00:00", "COMPLETED", 92.5)
    
    file_model = FileModel(None, 0, "file1.py", 1024, 100, 80, 10, 10, 0.9, 90.0)
    func_model = FunctionModel(None, 0, "my_func", None, 10, 20, 3, "Low", "int", True)
    comp_summary = ComplexitySummaryModel(None, 0, 3.0, 3, 1, 0, 0, 0)
    sec_issue = SecurityIssueModel(None, 0, "Danger", "High", 15, "eval()", "eval found")
    
    files_data = [(file_model, [func_model], comp_summary, [sec_issue])]
    
    metrics = MetricsModel(None, 0, 1, 1, 100, 10, 10, 80, 1024.0, "file1.py", "file1.py", 1.0, 0.0)
    
    repo_id = temp_db.save_analysis(repo, files_data, metrics, [])
    assert repo_id > 0
    
    repos = temp_db.get_repositories()
    assert len(repos) == 1
    assert repos[0].path == "test/repo"
    
    temp_db.delete_repository_analysis(repo_id)
    assert len(temp_db.get_repositories()) == 0

def test_documentation_analyzer(tmp_path):
    file_p = tmp_path / "doc_test.py"
    code = """
'''Module Doc'''
class A:
    '''Class Doc'''
    def f(self):
        return 1
"""
    file_p.write_text(code, encoding="utf-8")
    readme = tmp_path / "README.md"
    readme.write_text("Hello README", encoding="utf-8")
    
    parsed = parse_file(file_p)
    assert parsed is not None
    
    results = analyze_documentation(tmp_path, {"doc_test.py": parsed})
    assert results["readme_exists"] is True
    assert results["license_exists"] is False
    assert results["score"] > 50

def test_full_analysis_workflow(tmp_path):
    repo_dir = tmp_path / "mock_repo"
    repo_dir.mkdir()
    
    main_py = repo_dir / "main.py"
    main_py.write_text("""
import os
from helper import get_value

def run_app():
    val = get_value()
    eval("print(val)")
    return val

if __name__ == "__main__":
    run_app()
""", encoding="utf-8")

    helper_py = repo_dir / "helper.py"
    helper_py.write_text("""
def get_value():
    x = 10
    return x

def unused_func():
    return 42
""", encoding="utf-8")

    readme = repo_dir / "README.md"
    readme.write_text("Mock Project", encoding="utf-8")
    
    license_f = repo_dir / "LICENSE"
    license_f.write_text("MIT", encoding="utf-8")
    
    from utils.config import config
    old_db = config._config["database"]["db_path"]
    temp_db_path = tmp_path / "temp_run.db"
    config._config["database"]["db_path"] = str(temp_db_path)
    
    from analyzer.repository import run_repository_analysis
    repo_id = run_repository_analysis(str(repo_dir))
    
    assert repo_id > 0
    
    db = DatabaseManager(str(temp_db_path))
    repo = db.get_repository_by_id(repo_id)
    assert repo is not None
    assert repo.health_score > 0
    
    reports = db.get_reports_by_repo_id(repo_id)
    assert len(reports) == 4
    for rep in reports:
        assert Path(rep.file_path).exists()
        try:
            os.remove(rep.file_path)
        except Exception:
            pass
        
    config._config["database"]["db_path"] = old_db

def test_dependency_visualization(tmp_path):
    repo_dir = tmp_path / "mock_repo"
    repo_dir.mkdir(exist_ok=True)
    
    a_py = repo_dir / "a.py"
    a_py.write_text("import b\ndef f_a():\n    b.f_b()", encoding="utf-8")
    b_py = repo_dir / "b.py"
    b_py.write_text("def f_b():\n    pass", encoding="utf-8")
    
    from analyzer.repository import RepositoryScanner
    scanner = RepositoryScanner(str(repo_dir))
    parsed = scanner.parse_repository()
    
    from analyzer.dependencies import DependencyAnalyzer
    analyzer = DependencyAnalyzer(scanner.root_path, parsed)
    import_graph = analyzer.build_import_graph()
    call_graph = analyzer.build_call_graph()
    circular = analyzer.detect_circular_dependencies()
    
    assert len(import_graph.nodes) == 2
    assert len(call_graph.nodes) == 2
    assert len(circular) == 0
    
    from visualization.dependency_graph import generate_interactive_graph
    fig1 = generate_interactive_graph(import_graph, "Imports")
    fig2 = generate_interactive_graph(call_graph, "Calls")
    assert fig1 is not None
    assert fig2 is not None

def test_plotly_charts():
    from visualization.charts import (
        create_complexity_distribution_chart,
        create_doc_coverage_chart,
        create_security_risk_chart,
        create_large_files_chart,
        create_code_comment_pie
    )
    
    funcs = [
        FunctionModel(None, 1, "f1", None, 1, 10, 3, "Low", None, False),
        FunctionModel(None, 1, "f2", None, 11, 20, 12, "High", None, True)
    ]
    fig1 = create_complexity_distribution_chart(funcs)
    assert fig1 is not None
    
    doc_res = {
        "modules_with_docstrings": 1, "total_modules": 2,
        "classes_with_docstrings": 0, "total_classes": 1,
        "functions_with_docstrings": 1, "total_functions": 3
    }
    fig2 = create_doc_coverage_chart(doc_res)
    assert fig2 is not None
    
    issues = [SecurityIssueModel(None, 1, "eval", "High", 5, "eval(x)", "danger")]
    fig3 = create_security_risk_chart(issues)
    assert fig3 is not None
    
    files = [FileModel(None, 1, "f.py", 100, 50, 40, 5, 5, 0.8, 95.0)]
    fig4 = create_large_files_chart(files)
    assert fig4 is not None
    
    fig5 = create_code_comment_pie(100, 20, 10)
    assert fig5 is not None
