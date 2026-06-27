from dataclasses import dataclass
from typing import Optional

@dataclass
class RepositoryModel:
    id: Optional[int]
    path: str
    scanned_at: str
    status: str
    health_score: float

@dataclass
class FileModel:
    id: Optional[int]
    repository_id: int
    filepath: str
    size_bytes: int
    total_lines: int
    code_lines: int
    comment_lines: int
    blank_lines: int
    docstring_coverage: float
    health_score: float

@dataclass
class FunctionModel:
    id: Optional[int]
    file_id: int
    name: str
    class_name: Optional[str]
    start_line: int
    end_line: int
    complexity: int
    complexity_category: str
    return_type: Optional[str]
    has_docstring: bool

@dataclass
class MetricsModel:
    id: Optional[int]
    repository_id: int
    total_files: int
    python_files: int
    total_lines: int
    blank_lines: int
    comment_lines: int
    code_lines: int
    average_file_size: float
    largest_file: str
    smallest_file: str
    average_functions_per_file: float
    average_classes_per_file: float

@dataclass
class SecurityIssueModel:
    id: Optional[int]
    file_id: int
    issue_type: str
    severity: str
    line_number: int
    code_snippet: str
    description: str

@dataclass
class ComplexitySummaryModel:
    id: Optional[int]
    file_id: int
    average_complexity: float
    max_complexity: int
    low_count: int
    medium_count: int
    high_count: int
    very_high_count: int

@dataclass
class DuplicateCodeModel:
    id: Optional[int]
    repository_id: int
    file1_path: str
    file2_path: str
    start_line1: int
    end_line1: int
    start_line2: int
    end_line2: int
    matching_lines: int
    similarity_ratio: float
    code_snippet: str

@dataclass
class ReportModel:
    id: Optional[int]
    repository_id: int
    report_type: str
    file_path: str
    generated_at: str
