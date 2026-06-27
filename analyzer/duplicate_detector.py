import difflib
import hashlib
from typing import Dict, List, Tuple
from database.models import DuplicateCodeModel
from analyzer.parser import ParsedFile
from utils.config import config
from utils.logger import logger

def clean_and_normalize_lines(content: str) -> List[Tuple[int, str]]:
    """Trims whitespace and excludes comment/empty lines, tracking 1-indexed line numbers."""
    lines = content.splitlines()
    normalized = []
    for idx, line in enumerate(lines, 1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        normalized_str = "".join(stripped.split())
        normalized.append((idx, normalized_str))
    return normalized

def find_duplicates(
    parsed_files: Dict[str, ParsedFile]
) -> List[DuplicateCodeModel]:
    """Finds duplicate code blocks across scanned files and estimates similarity ratios."""
    min_lines = config.duplicate_min_line_length
    threshold = config.duplicate_similarity_threshold
    
    logger.info("Detecting duplicate code blocks...")
    
    # Map from line block hash -> list of occurrences (filepath, start, end, chunk)
    block_map: Dict[str, List[Tuple[str, int, int, List[str]]]] = {}
    
    for rel_path, parsed in parsed_files.items():
        norm_lines = clean_and_normalize_lines(parsed.raw_content)
        raw_lines = parsed.raw_content.splitlines()
        
        if len(norm_lines) < min_lines:
            continue
            
        for i in range(len(norm_lines) - min_lines + 1):
            window = norm_lines[i : i + min_lines]
            start_line_orig = window[0][0]
            end_line_orig = window[-1][0]
            
            combined_norm = "\n".join([w[1] for w in window])
            h = hashlib.md5(combined_norm.encode("utf-8")).hexdigest()
            raw_chunk = raw_lines[start_line_orig - 1 : end_line_orig]
            
            if h not in block_map:
                block_map[h] = []
            block_map[h].append((rel_path, start_line_orig, end_line_orig, raw_chunk))
            
    matches: List[DuplicateCodeModel] = []
    raw_matches: Dict[Tuple[str, str], List[Tuple[int, int, int, int]]] = {}
    
    for h, occurrences in block_map.items():
        if len(occurrences) < 2:
            continue
            
        for idx1 in range(len(occurrences)):
            for idx2 in range(idx1 + 1, len(occurrences)):
                occ1 = occurrences[idx1]
                occ2 = occurrences[idx2]
                
                if occ1[0] <= occ2[0]:
                    f1, s1, e1, _ = occ1
                    f2, s2, e2, _ = occ2
                else:
                    f1, s1, e1, _ = occ2
                    f2, s2, e2, _ = occ1
                
                if f1 == f2 and s1 == s2:
                    continue
                    
                pair = (f1, f2)
                if pair not in raw_matches:
                    raw_matches[pair] = []
                raw_matches[pair].append((s1, e1, s2, e2))
                
    for (f1, f2), blocks in raw_matches.items():
        blocks.sort(key=lambda x: (x[0], x[2]))
        
        merged: List[Tuple[int, int, int, int]] = []
        for b in blocks:
            if not merged:
                merged.append(b)
                continue
            
            last = merged[-1]
            s1_last, e1_last, s2_last, e2_last = last
            s1_curr, e1_curr, s2_curr, e2_curr = b
            
            shift1 = s1_curr - s1_last
            shift2 = s2_curr - s2_last
            
            if 0 <= shift1 <= 15 and 0 <= shift2 <= 15 and (shift1 == shift2 or abs(shift1 - shift2) <= 1):
                merged[-1] = (s1_last, max(e1_last, e1_curr), s2_last, max(e2_last, e2_curr))
            else:
                merged.append(b)
                
        for s1, e1, s2, e2 in merged:
            matching_lines = max(e1 - s1 + 1, e2 - s2 + 1)
            raw_lines1 = parsed_files[f1].raw_content.splitlines()
            raw_lines2 = parsed_files[f2].raw_content.splitlines()
            
            chunk1 = "\n".join(raw_lines1[s1 - 1 : e1])
            chunk2 = "\n".join(raw_lines2[s2 - 1 : e2])
            
            sm = difflib.SequenceMatcher(None, chunk1, chunk2)
            ratio = sm.ratio()
            
            if ratio >= threshold and matching_lines >= min_lines:
                snippet = f"--- {f1} (Lines {s1}-{e1}) ---\n"
                snippet += "\n".join(raw_lines1[s1 - 1 : min(s1 + 5, e1)])
                if e1 - s1 > 5:
                    snippet += "\n..."
                snippet += f"\n\n--- {f2} (Lines {s2}-{e2}) ---\n"
                snippet += "\n".join(raw_lines2[s2 - 1 : min(s2 + 5, e2)])
                if e2 - s2 > 5:
                    snippet += "\n..."
                
                matches.append(DuplicateCodeModel(
                    id=None,
                    repository_id=0,
                    file1_path=f1,
                    file2_path=f2,
                    start_line1=s1,
                    end_line1=e1,
                    start_line2=s2,
                    end_line2=e2,
                    matching_lines=matching_lines,
                    similarity_ratio=ratio,
                    code_snippet=snippet
                ))
                
    matches.sort(key=lambda x: (x.similarity_ratio, x.matching_lines), reverse=True)
    return matches

def get_refactoring_recommendation(dup: DuplicateCodeModel) -> str:
    """Generates refactoring advice based on duplication metrics."""
    if dup.similarity_ratio >= 0.95:
        if dup.file1_path == dup.file2_path:
            return f"Exact duplicate blocks in same file ({dup.file1_path}). Extract to a reusable function or class method."
        else:
            return f"Near-identical files/methods between {dup.file1_path} and {dup.file2_path}. Extract code blocks into a shared helper module/utility function."
    elif dup.similarity_ratio >= 0.8:
        return f"High similarity code detected between {dup.file1_path} and {dup.file2_path}. Standardize block parameterization and extract to common utilities."
    else:
        return "Low similarity code duplication. Optional refactoring: align function naming and abstractions."
