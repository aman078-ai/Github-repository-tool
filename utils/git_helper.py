import subprocess
from pathlib import Path
from typing import List, Dict, Any
from collections import Counter
from utils.logger import logger

def is_git_repository(repo_path: Path) -> bool:
    """Checks if the given directory path has a .git folder."""
    return (repo_path / ".git").exists()

def run_git_command(repo_path: Path, args: List[str]) -> str:
    """Runs a git command in the target directory and returns the stdout."""
    try:
        result = subprocess.run(
            ["git"] + args,
            cwd=str(repo_path),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True,
            encoding="utf-8",
            errors="ignore"
        )
        return result.stdout
    except Exception as e:
        logger.error(f"Git command failed in {repo_path} with args {args}: {e}")
        return ""

def get_top_contributors(repo_path: Path, max_authors: int = 5) -> List[Dict[str, Any]]:
    """Gathers git commit frequencies per author."""
    if not is_git_repository(repo_path):
        return []
    
    # Get all commit authors
    output = run_git_command(repo_path, ["log", "--pretty=format:%an"])
    if not output:
        return []
        
    authors = [line.strip() for line in output.splitlines() if line.strip()]
    counter = Counter(authors)
    
    total_commits = len(authors)
    results = []
    for author, count in counter.most_common(max_authors):
        percentage = round((count / total_commits) * 100, 1) if total_commits > 0 else 0
        results.append({
            "Author": author,
            "Commits": count,
            "Percentage": percentage
        })
        
    return results

def get_file_hotspots(repo_path: Path, max_files: int = 10) -> List[Dict[str, Any]]:
    """Counts frequency of changes per file in git history (hotspots)."""
    if not is_git_repository(repo_path):
        return []
        
    # Get names of modified files across all commits
    output = run_git_command(repo_path, ["log", "--pretty=format:", "--name-only"])
    if not output:
        return []
        
    files = []
    for line in output.splitlines():
        line = line.strip().replace("\\", "/") # Normalize paths
        # Focus on python files that exist in the directory
        if line and line.endswith(".py") and (repo_path / line).exists():
            files.append(line)
            
    counter = Counter(files)
    total_changes = len(files)
    
    results = []
    for filepath, count in counter.most_common(max_files):
        results.append({
            "File Path": filepath,
            "Changes Count": count,
            "Score": round((count / max(1, total_changes)) * 100, 1)
        })
        
    return results
