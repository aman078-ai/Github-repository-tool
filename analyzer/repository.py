import fnmatch
import os
import datetime
from pathlib import Path
from typing import List, Dict, Tuple, Optional, Any
from utils.config import config
from utils.logger import logger
from database.models import RepositoryModel, FileModel, FunctionModel, MetricsModel, SecurityIssueModel, ComplexitySummaryModel, ReportModel
from database.database import DatabaseManager
from analyzer.parser import ParsedFile, parse_file
from analyzer.metrics import calculate_metrics
from analyzer.complexity import analyze_complexity, merge_parser_and_complexity
from analyzer.duplicate_detector import find_duplicates
from analyzer.dead_code import DeadCodeDetector
from analyzer.documentation import analyze_documentation
from analyzer.security import scan_security
from analyzer.report_generator import ReportGenerator

class RepositoryScanner:
    def __init__(self, root_path: str):
        self.root_path = Path(root_path).resolve()
        self.ignored_folders = config.scanner_ignored_folders
        self.ignored_files = config.scanner_ignored_files

    def should_ignore_dir(self, path: Path) -> bool:
        """Checks if a directory path matches any ignore patterns."""
        parts = path.relative_to(self.root_path).parts if path.is_relative_to(self.root_path) else path.parts
        for folder in self.ignored_folders:
            if folder in parts or folder in path.parts:
                return True
        return False

    def should_ignore_file(self, path: Path) -> bool:
        """Checks if a file name matches any file ignore patterns."""
        for pattern in self.ignored_files:
            if fnmatch.fnmatch(path.name, pattern):
                return True
        return False

    def scan_files(self) -> List[Path]:
        """Recursively scans the directory for Python files, filtering ignores."""
        python_files: List[Path] = []
        if not self.root_path.exists():
            logger.error(f"Root path does not exist: {self.root_path}")
            return python_files

        for root, dirs, files in os.walk(self.root_path):
            current_dir = Path(root)
            dirs[:] = [d for d in dirs if not self.should_ignore_dir(current_dir / d)]
            for file in files:
                file_path = current_dir / file
                if file_path.suffix == ".py" and not self.should_ignore_file(file_path):
                    python_files.append(file_path)

        return python_files

    def parse_repository(self) -> Dict[str, ParsedFile]:
        """Scans and parses all Python files in the repository."""
        logger.info(f"Scanning repository at: {self.root_path}")
        python_files = self.scan_files()
        logger.info(f"Found {len(python_files)} python files to analyze.")
        
        parsed_results: Dict[str, ParsedFile] = {}
        for file_path in python_files:
            relative_path = file_path.relative_to(self.root_path).as_posix()
            logger.debug(f"Parsing file: {relative_path}")
            parsed = parse_file(file_path)
            if parsed:
                parsed.filepath = relative_path
                parsed_results[relative_path] = parsed
            else:
                logger.warning(f"Failed to parse file: {relative_path}")
                
        return parsed_results

def run_repository_analysis(repo_path: str) -> int:
    """Orchestrates the entire static code analysis on the repository.
    
    Calculates metrics, scoring, detects security flaws, dead code,
    persists in SQLite, and writes reports.
    
    Returns:
        The database ID of the created Repository record.
    """
    logger.info(f"Starting repository analysis run for: {repo_path}")
    start_time = datetime.datetime.now()
    
    scanner = RepositoryScanner(repo_path)
    parsed_files = scanner.parse_repository()
    
    if not parsed_files:
        logger.warning("No python files found to analyze.")
        db = DatabaseManager()
        db.init_db()
        repo_model = RepositoryModel(
            id=None,
            path=repo_path,
            scanned_at=start_time.isoformat(),
            status="COMPLETED",
            health_score=100.0
        )
        metrics_model = MetricsModel(
            id=None, repository_id=0, total_files=0, python_files=0, total_lines=0,
            blank_lines=0, comment_lines=0, code_lines=0, average_file_size=0,
            largest_file="N/A", smallest_file="N/A", average_functions_per_file=0,
            average_classes_per_file=0
        )
        repo_id = db.save_analysis(repo_model, [], metrics_model, [])
        return repo_id

    metrics_model = calculate_metrics(scanner.root_path, parsed_files)
    duplicate_records = find_duplicates(parsed_files)
    
    dead_code_detector = DeadCodeDetector(scanner.root_path, parsed_files)
    dead_code_results = dead_code_detector.detect_dead_code()
    
    doc_results = analyze_documentation(scanner.root_path, parsed_files)
    
    files_analysis_data = []
    file_health_scores = []
    
    for rel_path, parsed in parsed_files.items():
        raw = parsed.raw_content
        sec_issues = scan_security(rel_path, raw)
        funcs, comp_summary = analyze_complexity(rel_path, raw)
        merged_funcs = merge_parser_and_complexity(parsed.functions, funcs)
        
        total_items = 1 + len(parsed.classes) + len(parsed.functions)
        doc_items = (1 if parsed.has_docstring else 0) + sum(1 for c in parsed.classes if c.has_docstring) + sum(1 for f in parsed.functions if f.has_docstring)
        file_doc_coverage = doc_items / total_items if total_items > 0 else 1.0
        
        file_abs = scanner.root_path / rel_path
        file_size = file_abs.stat().st_size if file_abs.exists() else 0
        
        file_dups_count = sum(1 for d in duplicate_records if d.file1_path == rel_path or d.file2_path == rel_path)
        
        file_score = 100.0
        
        # A: Complexity deduction
        if comp_summary and comp_summary.max_complexity > 5:
            file_score -= min(25.0, (comp_summary.max_complexity - 5) * 5.0)
            
        # B: Security deduction
        sec_deduct = 0.0
        for issue in sec_issues:
            if issue.severity == "Critical":
                sec_deduct += 15.0
            elif issue.severity == "High":
                sec_deduct += 10.0
            elif issue.severity == "Medium":
                sec_deduct += 5.0
            else:
                sec_deduct += 2.0
        file_score -= min(40.0, sec_deduct)
        
        # C: Documentation deduction
        file_score -= (1.0 - file_doc_coverage) * 20.0
        
        # D: Duplicate deduction
        file_score -= min(15.0, file_dups_count * 5.0)
        
        file_score = round(max(0.0, file_score), 2)
        file_health_scores.append(file_score)
        
        file_model = FileModel(
            id=None,
            repository_id=0,
            filepath=rel_path,
            size_bytes=file_size,
            total_lines=parsed.total_lines,
            code_lines=parsed.code_lines,
            comment_lines=parsed.comment_lines,
            blank_lines=parsed.blank_lines,
            docstring_coverage=file_doc_coverage,
            health_score=file_score
        )
        
        files_analysis_data.append((file_model, merged_funcs, comp_summary, sec_issues))

    avg_file_health = sum(file_health_scores) / len(file_health_scores) if file_health_scores else 100.0
    
    repo_score = avg_file_health
    if doc_results.get("readme_exists", False):
        repo_score += 5.0
    if doc_results.get("license_exists", False):
        repo_score += 5.0
        
    unused_files_count = len(dead_code_results.get("unused_files", []))
    repo_score -= min(10.0, unused_files_count * 2.0)
    
    repo_score = round(min(100.0, max(0.0, repo_score)), 2)
    
    db = DatabaseManager()
    db.init_db()
    
    repo_model = RepositoryModel(
        id=None,
        path=str(scanner.root_path),
        scanned_at=start_time.isoformat(),
        status="COMPLETED",
        health_score=repo_score
    )
    
    repo_id = db.save_analysis(repo_model, files_analysis_data, metrics_model, duplicate_records)
    repo_model.id = repo_id
    
    report_gen = ReportGenerator(
        repo=repo_model,
        files=files_analysis_data,
        metrics=metrics_model,
        duplicates=duplicate_records,
        dead_code=dead_code_results
    )
    
    json_path = report_gen.generate_json_report()
    csv_path = report_gen.generate_csv_summary()
    md_path = report_gen.generate_markdown_report()
    html_path = report_gen.generate_html_report()
    
    db.save_report(ReportModel(None, repo_id, "JSON", str(json_path), datetime.datetime.now().isoformat()))
    db.save_report(ReportModel(None, repo_id, "CSV", str(csv_path), datetime.datetime.now().isoformat()))
    db.save_report(ReportModel(None, repo_id, "MD", str(md_path), datetime.datetime.now().isoformat()))
    db.save_report(ReportModel(None, repo_id, "HTML", str(html_path), datetime.datetime.now().isoformat()))
    
    logger.info(f"Successfully completed analysis run for repository (ID: {repo_id}, Health Score: {repo_score})")
    return repo_id
