import ast
from abc import ABC, abstractmethod
from typing import List, Dict, Any

class RepositorySummarizerInterface(ABC):
    """Abstract interface for generating AI-powered natural language summaries of a repository."""

    @abstractmethod
    def summarize_repository(self, repo_path: str, file_summaries: Dict[str, str]) -> str:
        """Generates a high-level architectural and behavioral description of the repository.
        
        Args:
            repo_path: The local path to the repository.
            file_summaries: A dictionary mapping filepaths to their individual summaries.
            
        Returns:
            A string containing the summary report.
        """
        pass

class BugRiskPredictorInterface(ABC):
    """Abstract interface for predicting code segments that have a high probability of containing bugs."""

    @abstractmethod
    def predict_bug_risks(self, file_content: str, complexity_score: int) -> List[Dict[str, Any]]:
        """Statically analyzes code structures to identify bug-prone lines.
        
        Args:
            file_content: Raw source code string.
            complexity_score: Cyclomatic complexity score of the file/function.
            
        Returns:
            A list of risk dictionaries containing:
            - 'line_number': int
            - 'risk_score': float (0.0 to 1.0)
            - 'category': str (e.g., 'State mutation', 'Resource leak')
            - 'reason': str
        """
        pass

class CodeRecommenderInterface(ABC):
    """Abstract interface for providing automated code improvements and refactoring suggestions."""

    @abstractmethod
    def recommend_improvements(self, file_content: str, issues: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Generates optimized code snippets based on style, complexity, or security issues.
        
        Args:
            file_content: Raw source code string.
            issues: Existing diagnostic reports for this file.
            
        Returns:
            A list of recommendation dictionaries containing:
            - 'line_range': Tuple[int, int]
            - 'original_code': str
            - 'recommended_code': str
            - 'explanation': str
        """
        pass

class NaturalLanguageSearchInterface(ABC):
    """Abstract interface for conducting semantic search queries over the parsed codebase."""

    @abstractmethod
    def semantic_search(self, query: str, code_embeddings: Dict[str, List[float]]) -> List[Dict[str, Any]]:
        """Performs a vector search matching user natural language queries with code semantic contents.
        
        Args:
            query: Natural language search string (e.g., 'where do we handle db write?').
            code_embeddings: A pre-computed dictionary of file/function identifiers to floating point embeddings.
            
        Returns:
            A sorted list of results containing:
            - 'identifier': str (file or function reference)
            - 'similarity_score': float (0.0 to 1.0)
            - 'snippet': str
        """
        pass


class LocalBugRiskPredictor(BugRiskPredictorInterface):
    """Local rule-based bug risk predictor using AST static code analysis."""

    def predict_bug_risks(self, file_content: str, complexity_score: int) -> List[Dict[str, Any]]:
        risks = []
        try:
            tree = ast.parse(file_content)
            for node in ast.walk(tree):
                # 1. Mutable default arguments
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    # Check defaults
                    for default in node.args.defaults:
                        if isinstance(default, (ast.List, ast.Dict, ast.Set)):
                            risks.append({
                                "line_number": default.lineno,
                                "risk_score": round(min(0.5 + complexity_score * 0.05, 0.9), 2),
                                "category": "State mutation",
                                "reason": f"Function '{node.name}' uses a mutable default argument ({type(default).__name__.lower()}). This can lead to shared state bugs across multiple function calls."
                            })
                    for kw_default in node.args.kw_defaults:
                        if kw_default and isinstance(kw_default, (ast.List, ast.Dict, ast.Set)):
                            risks.append({
                                "line_number": kw_default.lineno,
                                "risk_score": round(min(0.5 + complexity_score * 0.05, 0.9), 2),
                                "category": "State mutation",
                                "reason": f"Function '{node.name}' uses a mutable default keyword argument. This can lead to shared state bugs."
                            })

                # 2. Comparison with literals using 'is' or 'is not'
                elif isinstance(node, ast.Compare):
                    for op in node.ops:
                        if isinstance(op, (ast.Is, ast.IsNot)):
                            for comparator in node.comparators:
                                if isinstance(comparator, ast.Constant) and type(comparator.value) in {int, float, str, bytes}:
                                    op_name = "is" if isinstance(op, ast.Is) else "is not"
                                    risks.append({
                                        "line_number": node.lineno,
                                        "risk_score": round(min(0.6 + complexity_score * 0.05, 0.95), 2),
                                        "category": "Identity comparison",
                                        "reason": f"Using identity operator '{op_name}' to compare with literal constant ({repr(comparator.value)}). Use equality operator ('==' or '!=') instead, as 'is' checks object identity, not value equality."
                                    })

                # 3. Bare except clauses
                elif isinstance(node, ast.ExceptHandler):
                    if node.type is None:
                        risks.append({
                            "line_number": node.lineno,
                            "risk_score": round(min(0.4 + complexity_score * 0.05, 0.8), 2),
                            "category": "Error handling",
                            "reason": "Found bare 'except:' clause. This catches all exceptions, including SystemExit, KeyboardInterrupt, and MemoryError, which makes debugging extremely difficult and can mask bugs."
                        })
        except Exception as e:
            pass
        return risks
