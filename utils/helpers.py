import time
from contextlib import contextmanager
from pathlib import Path
from typing import Generator, Union
from utils.logger import logger

def format_size(size_bytes: int) -> str:
    """Formats raw bytes size into a human-readable string (KB, MB, GB, etc.)."""
    if size_bytes < 0:
        return "0.00 B"
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if size_bytes < 1024.0:
            # Format to 2 decimal places, strip trailing zeros if whole number
            val = f"{size_bytes:.2f}"
            return f"{val} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} PB"

def format_duration(seconds: float) -> str:
    """Formats duration in seconds to a human-readable duration string."""
    if seconds < 1.0:
        return f"{seconds * 1000:.2f} ms"
    elif seconds < 60.0:
        return f"{seconds:.2f} s"
    else:
        minutes = int(seconds // 60)
        rem_sec = seconds % 60
        return f"{minutes}m {rem_sec:.2f}s"

@contextmanager
def timer(activity_name: str) -> Generator[None, None, None]:
    """Context manager to measure and log the duration of an execution block."""
    start_time = time.perf_counter()
    logger.info(f"Starting activity: {activity_name}")
    try:
        yield
    finally:
        elapsed = time.perf_counter() - start_time
        logger.info(f"Finished activity: {activity_name} in {format_duration(elapsed)}")

def safe_read_file(path: Union[str, Path]) -> str:
    """Reads a file's content, attempting common encodings to avoid crash."""
    filepath = Path(path)
    encodings = ["utf-8", "latin-1", "utf-16", "cp1252"]
    for encoding in encodings:
        try:
            with open(filepath, "r", encoding=encoding) as f:
                return f.read()
        except UnicodeDecodeError:
            continue
    raise UnicodeDecodeError("utf-8", b"", 0, 0, f"Unable to decode file: {filepath}")
