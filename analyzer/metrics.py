import os
from pathlib import Path
from typing import Dict, List
from database.models import MetricsModel
from analyzer.parser import ParsedFile
from utils.logger import logger

def calculate_metrics(
    root_path: Path,
    parsed_files: Dict[str, ParsedFile]
) -> MetricsModel:
    """Computes codebase-wide metrics based on the parsed Python files and file-system inspection."""
    logger.info("Calculating codebase metrics...")
    
    total_files = 0
    python_files = len(parsed_files)
    total_lines = 0
    blank_lines = 0
    comment_lines = 0
    code_lines = 0
    total_functions = 0
    total_classes = 0
    
    file_sizes: List[int] = []
    largest_file = "N/A"
    largest_size = -1
    smallest_file = "N/A"
    smallest_size = float('inf')
    
    from analyzer.repository import RepositoryScanner
    scanner = RepositoryScanner(str(root_path))
    
    for root, dirs, files in os.walk(root_path):
        current_dir = Path(root)
        dirs[:] = [d for d in dirs if not scanner.should_ignore_dir(current_dir / d)]
        for f in files:
            file_path = current_dir / f
            if not scanner.should_ignore_file(file_path):
                total_files += 1

    for rel_path, parsed in parsed_files.items():
        total_lines += parsed.total_lines
        blank_lines += parsed.blank_lines
        comment_lines += parsed.comment_lines
        code_lines += parsed.code_lines
        total_functions += len(parsed.functions)
        total_classes += len(parsed.classes)
        
        file_path = root_path / rel_path
        if file_path.exists():
            size = file_path.stat().st_size
            file_sizes.append(size)
            if size > largest_size:
                largest_size = size
                largest_file = rel_path
            if size < smallest_size:
                smallest_size = size
                smallest_file = rel_path

    avg_file_size = sum(file_sizes) / len(file_sizes) if file_sizes else 0.0
    if smallest_size == float('inf'):
        smallest_size = 0
        smallest_file = "N/A"
        
    avg_funcs = total_functions / python_files if python_files else 0.0
    avg_classes = total_classes / python_files if python_files else 0.0

    return MetricsModel(
        id=None,
        repository_id=0,
        total_files=total_files,
        python_files=python_files,
        total_lines=total_lines,
        blank_lines=blank_lines,
        comment_lines=comment_lines,
        code_lines=code_lines,
        average_file_size=avg_file_size,
        largest_file=f"{largest_file} ({largest_size} bytes)" if largest_size >= 0 else "N/A",
        smallest_file=f"{smallest_file} ({smallest_size} bytes)" if smallest_size > 0 or python_files > 0 else "N/A",
        average_functions_per_file=avg_funcs,
        average_classes_per_file=avg_classes
    )
