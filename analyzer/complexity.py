from typing import List, Tuple, Optional, Any
from radon.visitors import ComplexityVisitor
from utils.config import config
from utils.logger import logger
from database.models import FunctionModel, ComplexitySummaryModel

def get_complexity_category(score: int) -> str:
    """Categorizes cyclomatic complexity based on config thresholds."""
    if score <= config.complexity_low_threshold:
        return "Low"
    elif score <= config.complexity_medium_threshold:
        return "Medium"
    elif score <= config.complexity_high_threshold:
        return "High"
    else:
        return "Very High"

def analyze_complexity(
    filepath: str,
    raw_content: str
) -> Tuple[List[FunctionModel], Optional[ComplexitySummaryModel]]:
    """Analyzes a Python file's code using Radon ComplexityVisitor."""
    try:
        visitor = ComplexityVisitor.from_code(raw_content)
        functions_list: List[FunctionModel] = []
        complexity_scores: List[int] = []
        low_c = 0
        med_c = 0
        high_c = 0
        vhigh_c = 0
        
        for block in visitor.blocks:
            # We want to measure complexity at the function and method level, not class container level
            if block.letter == 'C':
                continue
            
            class_name = getattr(block, "classname", None)
            complexity = block.complexity
            complexity_scores.append(complexity)
            
            category = get_complexity_category(complexity)
            if category == "Low":
                low_c += 1
            elif category == "Medium":
                med_c += 1
            elif category == "High":
                high_c += 1
            else:
                vhigh_c += 1
                
            functions_list.append(FunctionModel(
                id=None,
                file_id=0,
                name=block.name,
                class_name=class_name,
                start_line=block.lineno,
                end_line=block.endline,
                complexity=complexity,
                complexity_category=category,
                return_type=None,
                has_docstring=False
            ))
            
        if not complexity_scores:
            return [], None
            
        avg_complexity = sum(complexity_scores) / len(complexity_scores)
        max_complexity = max(complexity_scores)
        
        summary = ComplexitySummaryModel(
            id=None,
            file_id=0,
            average_complexity=avg_complexity,
            max_complexity=max_complexity,
            low_count=low_c,
            medium_count=med_c,
            high_count=high_c,
            very_high_count=vhigh_c
        )
        
        return functions_list, summary
        
    except Exception as e:
        logger.error(f"Error calculating complexity for {filepath}: {e}")
        return [], None

def merge_parser_and_complexity(
    parser_functions: List[Any],
    complexity_functions: List[FunctionModel]
) -> List[FunctionModel]:
    """Merges AST parsing metadata (types, docstrings) with Radon complexity metrics."""
    matched_funcs: List[FunctionModel] = []
    
    # Index parser functions by (class_name, name)
    parser_map = {}
    for pf in parser_functions:
        key = (pf.class_name, pf.name)
        parser_map[key] = pf

    for cf in complexity_functions:
        key = (cf.class_name, cf.name)
        if key in parser_map:
            pf = parser_map[key]
            cf.return_type = pf.return_type
            cf.has_docstring = pf.has_docstring
            cf.start_line = pf.start_line
            cf.end_line = pf.end_line
        matched_funcs.append(cf)
        
    return matched_funcs
