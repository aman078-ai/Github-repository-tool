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
