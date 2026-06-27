import os
from pathlib import Path
from typing import Any, Dict, List
import yaml

DEFAULT_CONFIG = {
    "scanner": {
        "ignored_folders": ["__pycache__", ".venv", "venv", ".git", "node_modules", "dist", "build", ".pytest_cache"],
        "ignored_files": ["*.pyc", "*.pyo", "*.pyd", "db.sqlite3", "repo_intelligence.db"]
    },
    "complexity": {
        "low_threshold": 5,
        "medium_threshold": 10,
        "high_threshold": 20
    },
    "duplicate_detector": {
        "min_line_length": 4,
        "similarity_threshold": 0.8
    },
    "database": {
        "db_path": "repo_intelligence.db"
    },
    "visualization": {
        "theme": "dark",
        "graphviz_layout": "dot",
        "max_graph_nodes": 100
    },
    "documentation": {
        "min_docstring_length": 10
    }
}

class Config:
    def __init__(self, config_path: str = "config.yaml"):
        self.config_path = Path(config_path)
        self._config = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        if not self.config_path.exists():
            return DEFAULT_CONFIG
        
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                loaded = yaml.safe_load(f)
                if not loaded:
                    return DEFAULT_CONFIG
                return self._merge_dicts(DEFAULT_CONFIG, loaded)
        except Exception:
            return DEFAULT_CONFIG

    def _merge_dicts(self, default: Dict[str, Any], loaded: Dict[str, Any]) -> Dict[str, Any]:
        merged = default.copy()
        for k, v in loaded.items():
            if isinstance(v, dict) and k in merged and isinstance(merged[k], dict):
                merged[k] = self._merge_dicts(merged[k], v)
            else:
                merged[k] = v
        return merged

    def get(self, section: str, key: str, default: Any = None) -> Any:
        return self._config.get(section, {}).get(key, default)

    @property
    def scanner_ignored_folders(self) -> List[str]:
        return self.get("scanner", "ignored_folders", [])

    @property
    def scanner_ignored_files(self) -> List[str]:
        return self.get("scanner", "ignored_files", [])

    @property
    def complexity_low_threshold(self) -> int:
        return self.get("complexity", "low_threshold", 5)

    @property
    def complexity_medium_threshold(self) -> int:
        return self.get("complexity", "medium_threshold", 10)

    @property
    def complexity_high_threshold(self) -> int:
        return self.get("complexity", "high_threshold", 20)

    @property
    def duplicate_min_line_length(self) -> int:
        return self.get("duplicate_detector", "min_line_length", 4)

    @property
    def duplicate_similarity_threshold(self) -> float:
        return self.get("duplicate_detector", "similarity_threshold", 0.8)

    @property
    def database_path(self) -> str:
        return self.get("database", "db_path", "repo_intelligence.db")

    @property
    def visualization_theme(self) -> str:
        return self.get("visualization", "theme", "dark")

    @property
    def visualization_layout(self) -> str:
        return self.get("visualization", "graphviz_layout", "dot")

    @property
    def max_graph_nodes(self) -> int:
        return self.get("visualization", "max_graph_nodes", 100)

    @property
    def min_docstring_length(self) -> int:
        return self.get("documentation", "min_docstring_length", 10)

# Global configuration instance
config = Config()
