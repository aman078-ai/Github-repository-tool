from pathlib import Path
from typing import Dict, Any
from analyzer.parser import ParsedFile
from utils.logger import logger

def analyze_documentation(
    root_path: Path,
    parsed_files: Dict[str, ParsedFile]
) -> Dict[str, Any]:
    """Calculates repository-wide docstring and readme/license documentation metrics."""
    logger.info("Analyzing documentation coverage...")
    
    total_modules = len(parsed_files)
    modules_with_docstrings = sum(1 for f in parsed_files.values() if f.has_docstring)
    
    total_classes = 0
    classes_with_docstrings = 0
    total_functions = 0
    functions_with_docstrings = 0
    
    for parsed in parsed_files.values():
        total_classes += len(parsed.classes)
        classes_with_docstrings += sum(1 for c in parsed.classes if c.has_docstring)
        
        total_functions += len(parsed.functions)
        functions_with_docstrings += sum(1 for f in parsed.functions if f.has_docstring)
        
    readme_exists = False
    license_exists = False
    
    if root_path.exists() and root_path.is_dir():
        for item in root_path.iterdir():
            if item.is_file():
                name_lower = item.name.lower()
                if name_lower.startswith("readme"):
                    readme_exists = True
                elif name_lower.startswith("license") or name_lower.startswith("copying"):
                    license_exists = True

    total_items = total_modules + total_classes + total_functions
    documented_items = modules_with_docstrings + classes_with_docstrings + functions_with_docstrings
    
    coverage = documented_items / total_items if total_items > 0 else 1.0
    
    score = (coverage * 80.0)
    if readme_exists:
        score += 10.0
    if license_exists:
        score += 10.0
        
    score = round(score, 2)
    
    return {
        "total_modules": total_modules,
        "modules_with_docstrings": modules_with_docstrings,
        "total_classes": total_classes,
        "classes_with_docstrings": classes_with_docstrings,
        "total_functions": total_functions,
        "functions_with_docstrings": functions_with_docstrings,
        "readme_exists": readme_exists,
        "license_exists": license_exists,
        "coverage_ratio": round(coverage, 4),
        "score": score
    }
