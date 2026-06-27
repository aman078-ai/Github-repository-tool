import sqlite3
from pathlib import Path
from typing import List, Optional, Tuple, Dict, Any
from utils.config import config
from utils.logger import logger
from database.models import (
    RepositoryModel, FileModel, FunctionModel, MetricsModel,
    SecurityIssueModel, ComplexitySummaryModel, DuplicateCodeModel, ReportModel
)

class DatabaseManager:
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or config.database_path

    def get_connection(self) -> sqlite3.Connection:
        """Returns a sqlite3 connection with foreign keys enabled."""
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self) -> None:
        """Initializes the database schema."""
        logger.info(f"Initializing SQLite database at: {self.db_path}")
        with self.get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS repositories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    path TEXT UNIQUE NOT NULL,
                    scanned_at TEXT NOT NULL,
                    status TEXT NOT NULL,
                    health_score REAL NOT NULL
                );
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS files (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    repository_id INTEGER NOT NULL,
                    filepath TEXT NOT NULL,
                    size_bytes INTEGER NOT NULL,
                    total_lines INTEGER NOT NULL,
                    code_lines INTEGER NOT NULL,
                    comment_lines INTEGER NOT NULL,
                    blank_lines INTEGER NOT NULL,
                    docstring_coverage REAL NOT NULL,
                    health_score REAL NOT NULL,
                    FOREIGN KEY (repository_id) REFERENCES repositories(id) ON DELETE CASCADE
                );
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS functions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    file_id INTEGER NOT NULL,
                    name TEXT NOT NULL,
                    class_name TEXT,
                    start_line INTEGER NOT NULL,
                    end_line INTEGER NOT NULL,
                    complexity INTEGER NOT NULL,
                    complexity_category TEXT NOT NULL,
                    return_type TEXT,
                    has_docstring INTEGER NOT NULL,
                    FOREIGN KEY (file_id) REFERENCES files(id) ON DELETE CASCADE
                );
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    repository_id INTEGER UNIQUE NOT NULL,
                    total_files INTEGER NOT NULL,
                    python_files INTEGER NOT NULL,
                    total_lines INTEGER NOT NULL,
                    blank_lines INTEGER NOT NULL,
                    comment_lines INTEGER NOT NULL,
                    code_lines INTEGER NOT NULL,
                    average_file_size REAL NOT NULL,
                    largest_file TEXT NOT NULL,
                    smallest_file TEXT NOT NULL,
                    average_functions_per_file REAL NOT NULL,
                    average_classes_per_file REAL NOT NULL,
                    FOREIGN KEY (repository_id) REFERENCES repositories(id) ON DELETE CASCADE
                );
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS security_issues (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    file_id INTEGER NOT NULL,
                    issue_type TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    line_number INTEGER NOT NULL,
                    code_snippet TEXT NOT NULL,
                    description TEXT NOT NULL,
                    FOREIGN KEY (file_id) REFERENCES files(id) ON DELETE CASCADE
                );
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS complexity_summaries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    file_id INTEGER UNIQUE NOT NULL,
                    average_complexity REAL NOT NULL,
                    max_complexity INTEGER NOT NULL,
                    low_count INTEGER NOT NULL,
                    medium_count INTEGER NOT NULL,
                    high_count INTEGER NOT NULL,
                    very_high_count INTEGER NOT NULL,
                    FOREIGN KEY (file_id) REFERENCES files(id) ON DELETE CASCADE
                );
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS duplicate_code (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    repository_id INTEGER NOT NULL,
                    file1_path TEXT NOT NULL,
                    file2_path TEXT NOT NULL,
                    start_line1 INTEGER NOT NULL,
                    end_line1 INTEGER NOT NULL,
                    start_line2 INTEGER NOT NULL,
                    end_line2 INTEGER NOT NULL,
                    matching_lines INTEGER NOT NULL,
                    similarity_ratio REAL NOT NULL,
                    code_snippet TEXT NOT NULL,
                    FOREIGN KEY (repository_id) REFERENCES repositories(id) ON DELETE CASCADE
                );
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS reports (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    repository_id INTEGER NOT NULL,
                    report_type TEXT NOT NULL,
                    file_path TEXT NOT NULL,
                    generated_at TEXT NOT NULL,
                    FOREIGN KEY (repository_id) REFERENCES repositories(id) ON DELETE CASCADE
                );
            """)
            conn.commit()

    def get_repository_by_path(self, path: str) -> Optional[RepositoryModel]:
        with self.get_connection() as conn:
            cursor = conn.execute(
                "SELECT id, path, scanned_at, status, health_score FROM repositories WHERE path = ?;",
                (path,)
            )
            row = cursor.fetchone()
            if row:
                return RepositoryModel(
                    id=row["id"],
                    path=row["path"],
                    scanned_at=row["scanned_at"],
                    status=row["status"],
                    health_score=row["health_score"]
                )
        return None

    def delete_repository_analysis(self, repo_id: int) -> None:
        """Deletes repository analysis run. Cascade deletes associated entries."""
        with self.get_connection() as conn:
            conn.execute("DELETE FROM repositories WHERE id = ?;", (repo_id,))
            conn.commit()

    def save_analysis(
        self,
        repo: RepositoryModel,
        files: List[Tuple[FileModel, List[FunctionModel], Optional[ComplexitySummaryModel], List[SecurityIssueModel]]],
        metrics: MetricsModel,
        duplicates: List[DuplicateCodeModel]
    ) -> int:
        """Saves a complete scan transaction, replacing any previous records for the same path."""
        with self.get_connection() as conn:
            # Check if repo path exists, delete if so to allow re-analysis
            cursor = conn.execute("SELECT id FROM repositories WHERE path = ?;", (repo.path,))
            existing = cursor.fetchone()
            if existing:
                conn.execute("DELETE FROM repositories WHERE id = ?;", (existing["id"],))
            
            # Insert repository
            cursor = conn.execute(
                "INSERT INTO repositories (path, scanned_at, status, health_score) VALUES (?, ?, ?, ?);",
                (repo.path, repo.scanned_at, repo.status, repo.health_score)
            )
            repo_id = cursor.lastrowid
            
            # Insert metrics
            conn.execute(
                """INSERT INTO metrics (
                    repository_id, total_files, python_files, total_lines, blank_lines,
                    comment_lines, code_lines, average_file_size, largest_file,
                    smallest_file, average_functions_per_file, average_classes_per_file
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);""",
                (
                    repo_id, metrics.total_files, metrics.python_files, metrics.total_lines,
                    metrics.blank_lines, metrics.comment_lines, metrics.code_lines,
                    metrics.average_file_size, metrics.largest_file, metrics.smallest_file,
                    metrics.average_functions_per_file, metrics.average_classes_per_file
                )
            )
            
            # Insert duplicates
            for dup in duplicates:
                conn.execute(
                    """INSERT INTO duplicate_code (
                        repository_id, file1_path, file2_path, start_line1, end_line1,
                        start_line2, end_line2, matching_lines, similarity_ratio, code_snippet
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);""",
                    (
                        repo_id, dup.file1_path, dup.file2_path, dup.start_line1, dup.end_line1,
                        dup.start_line2, dup.end_line2, dup.matching_lines, dup.similarity_ratio,
                        dup.code_snippet
                    )
                )

            # Insert files and related sub-tables
            for file_model, functions, comp_summary, sec_issues in files:
                cursor = conn.execute(
                    """INSERT INTO files (
                        repository_id, filepath, size_bytes, total_lines, code_lines,
                        comment_lines, blank_lines, docstring_coverage, health_score
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);""",
                    (
                        repo_id, file_model.filepath, file_model.size_bytes, file_model.total_lines,
                        file_model.code_lines, file_model.comment_lines, file_model.blank_lines,
                        file_model.docstring_coverage, file_model.health_score
                    )
                )
                file_id = cursor.lastrowid
                
                # Insert functions
                for func in functions:
                    conn.execute(
                        """INSERT INTO functions (
                            file_id, name, class_name, start_line, end_line,
                            complexity, complexity_category, return_type, has_docstring
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);""",
                        (
                            file_id, func.name, func.class_name, func.start_line, func.end_line,
                            func.complexity, func.complexity_category, func.return_type,
                            1 if func.has_docstring else 0
                        )
                    )
                
                # Insert complexity summary if present
                if comp_summary:
                    conn.execute(
                        """INSERT INTO complexity_summaries (
                            file_id, average_complexity, max_complexity,
                            low_count, medium_count, high_count, very_high_count
                        ) VALUES (?, ?, ?, ?, ?, ?, ?);""",
                        (
                            file_id, comp_summary.average_complexity, comp_summary.max_complexity,
                            comp_summary.low_count, comp_summary.medium_count,
                            comp_summary.high_count, comp_summary.very_high_count
                        )
                    )
                
                # Insert security issues
                for issue in sec_issues:
                    conn.execute(
                        """INSERT INTO security_issues (
                            file_id, issue_type, severity, line_number, code_snippet, description
                        ) VALUES (?, ?, ?, ?, ?, ?);""",
                        (
                            file_id, issue.issue_type, issue.severity, issue.line_number,
                            issue.code_snippet, issue.description
                        )
                    )
                    
            conn.commit()
            return repo_id

    def save_report(self, report: ReportModel) -> None:
        with self.get_connection() as conn:
            conn.execute(
                "INSERT INTO reports (repository_id, report_type, file_path, generated_at) VALUES (?, ?, ?, ?);",
                (report.repository_id, report.report_type, report.file_path, report.generated_at)
            )
            conn.commit()

    def get_repositories(self) -> List[RepositoryModel]:
        with self.get_connection() as conn:
            cursor = conn.execute("SELECT id, path, scanned_at, status, health_score FROM repositories ORDER BY scanned_at DESC;")
            return [
                RepositoryModel(
                    id=row["id"], path=row["path"], scanned_at=row["scanned_at"],
                    status=row["status"], health_score=row["health_score"]
                )
                for row in cursor.fetchall()
            ]

    def get_repository_by_id(self, repo_id: int) -> Optional[RepositoryModel]:
        with self.get_connection() as conn:
            cursor = conn.execute("SELECT id, path, scanned_at, status, health_score FROM repositories WHERE id = ?;", (repo_id,))
            row = cursor.fetchone()
            if row:
                return RepositoryModel(
                    id=row["id"], path=row["path"], scanned_at=row["scanned_at"],
                    status=row["status"], health_score=row["health_score"]
                )
        return None

    def get_metrics_by_repo_id(self, repo_id: int) -> Optional[MetricsModel]:
        with self.get_connection() as conn:
            cursor = conn.execute("SELECT * FROM metrics WHERE repository_id = ?;", (repo_id,))
            row = cursor.fetchone()
            if row:
                return MetricsModel(
                    id=row["id"], repository_id=row["repository_id"], total_files=row["total_files"],
                    python_files=row["python_files"], total_lines=row["total_lines"],
                    blank_lines=row["blank_lines"], comment_lines=row["comment_lines"],
                    code_lines=row["code_lines"], average_file_size=row["average_file_size"],
                    largest_file=row["largest_file"], smallest_file=row["smallest_file"],
                    average_functions_per_file=row["average_functions_per_file"],
                    average_classes_per_file=row["average_classes_per_file"]
                )
        return None

    def get_files_by_repo_id(self, repo_id: int) -> List[FileModel]:
        with self.get_connection() as conn:
            cursor = conn.execute("SELECT * FROM files WHERE repository_id = ? ORDER BY filepath ASC;", (repo_id,))
            return [
                FileModel(
                    id=row["id"], repository_id=row["repository_id"], filepath=row["filepath"],
                    size_bytes=row["size_bytes"], total_lines=row["total_lines"], code_lines=row["code_lines"],
                    comment_lines=row["comment_lines"], blank_lines=row["blank_lines"],
                    docstring_coverage=row["docstring_coverage"], health_score=row["health_score"]
                )
                for row in cursor.fetchall()
            ]

    def get_functions_by_file_id(self, file_id: int) -> List[FunctionModel]:
        with self.get_connection() as conn:
            cursor = conn.execute("SELECT * FROM functions WHERE file_id = ? ORDER BY start_line ASC;", (file_id,))
            return [
                FunctionModel(
                    id=row["id"], file_id=row["file_id"], name=row["name"], class_name=row["class_name"],
                    start_line=row["start_line"], end_line=row["end_line"], complexity=row["complexity"],
                    complexity_category=row["complexity_category"], return_type=row["return_type"],
                    has_docstring=bool(row["has_docstring"])
                )
                for row in cursor.fetchall()
            ]

    def get_all_functions_by_repo_id(self, repo_id: int) -> List[Tuple[FileModel, FunctionModel]]:
        with self.get_connection() as conn:
            cursor = conn.execute(
                """SELECT f.*, func.id as func_id, func.name, func.class_name, func.start_line,
                          func.end_line, func.complexity, func.complexity_category, func.return_type,
                          func.has_docstring
                   FROM files f
                   JOIN functions func ON f.id = func.file_id
                   WHERE f.repository_id = ?
                   ORDER BY f.filepath ASC, func.start_line ASC;""",
                (repo_id,)
            )
            results = []
            for row in cursor.fetchall():
                file_model = FileModel(
                    id=row["id"], repository_id=row["repository_id"], filepath=row["filepath"],
                    size_bytes=row["size_bytes"], total_lines=row["total_lines"], code_lines=row["code_lines"],
                    comment_lines=row["comment_lines"], blank_lines=row["blank_lines"],
                    docstring_coverage=row["docstring_coverage"], health_score=row["health_score"]
                )
                func_model = FunctionModel(
                    id=row["func_id"], file_id=row["id"], name=row["name"], class_name=row["class_name"],
                    start_line=row["start_line"], end_line=row["end_line"], complexity=row["complexity"],
                    complexity_category=row["complexity_category"], return_type=row["return_type"],
                    has_docstring=bool(row["has_docstring"])
                )
                results.append((file_model, func_model))
            return results

    def get_complexity_summaries_by_repo_id(self, repo_id: int) -> List[Tuple[FileModel, ComplexitySummaryModel]]:
        with self.get_connection() as conn:
            cursor = conn.execute(
                """SELECT f.*, c.id as comp_id, c.average_complexity, c.max_complexity,
                          c.low_count, c.medium_count, c.high_count, c.very_high_count
                   FROM files f
                   JOIN complexity_summaries c ON f.id = c.file_id
                   WHERE f.repository_id = ?;""",
                (repo_id,)
            )
            results = []
            for row in cursor.fetchall():
                file_model = FileModel(
                    id=row["id"], repository_id=row["repository_id"], filepath=row["filepath"],
                    size_bytes=row["size_bytes"], total_lines=row["total_lines"], code_lines=row["code_lines"],
                    comment_lines=row["comment_lines"], blank_lines=row["blank_lines"],
                    docstring_coverage=row["docstring_coverage"], health_score=row["health_score"]
                )
                comp_model = ComplexitySummaryModel(
                    id=row["comp_id"], file_id=row["id"], average_complexity=row["average_complexity"],
                    max_complexity=row["max_complexity"], low_count=row["low_count"],
                    medium_count=row["medium_count"], high_count=row["high_count"],
                    very_high_count=row["very_high_count"]
                )
                results.append((file_model, comp_model))
            return results

    def get_security_issues_by_repo_id(self, repo_id: int) -> List[Tuple[FileModel, SecurityIssueModel]]:
        with self.get_connection() as conn:
            cursor = conn.execute(
                """SELECT f.*, s.id as issue_id, s.issue_type, s.severity, s.line_number, s.code_snippet, s.description
                   FROM files f
                   JOIN security_issues s ON f.id = s.file_id
                   WHERE f.repository_id = ?
                   ORDER BY s.severity DESC, f.filepath ASC;""",
                (repo_id,)
            )
            results = []
            for row in cursor.fetchall():
                file_model = FileModel(
                    id=row["id"], repository_id=row["repository_id"], filepath=row["filepath"],
                    size_bytes=row["size_bytes"], total_lines=row["total_lines"], code_lines=row["code_lines"],
                    comment_lines=row["comment_lines"], blank_lines=row["blank_lines"],
                    docstring_coverage=row["docstring_coverage"], health_score=row["health_score"]
                )
                issue_model = SecurityIssueModel(
                    id=row["issue_id"], file_id=row["id"], issue_type=row["issue_type"],
                    severity=row["severity"], line_number=row["line_number"],
                    code_snippet=row["code_snippet"], description=row["description"]
                )
                results.append((file_model, issue_model))
            return results

    def get_duplicates_by_repo_id(self, repo_id: int) -> List[DuplicateCodeModel]:
        with self.get_connection() as conn:
            cursor = conn.execute("SELECT * FROM duplicate_code WHERE repository_id = ? ORDER BY similarity_ratio DESC;", (repo_id,))
            return [
                DuplicateCodeModel(
                    id=row["id"], repository_id=row["repository_id"], file1_path=row["file1_path"],
                    file2_path=row["file2_path"], start_line1=row["start_line1"], end_line1=row["end_line1"],
                    start_line2=row["start_line2"], end_line2=row["end_line2"], matching_lines=row["matching_lines"],
                    similarity_ratio=row["similarity_ratio"], code_snippet=row["code_snippet"]
                )
                for row in cursor.fetchall()
            ]

    def get_reports_by_repo_id(self, repo_id: int) -> List[ReportModel]:
        with self.get_connection() as conn:
            cursor = conn.execute("SELECT * FROM reports WHERE repository_id = ? ORDER BY generated_at DESC;", (repo_id,))
            return [
                ReportModel(
                    id=row["id"], repository_id=row["repository_id"], report_type=row["report_type"],
                    file_path=row["file_path"], generated_at=row["generated_at"]
                )
                for row in cursor.fetchall()
            ]
