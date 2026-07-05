import ast
import re
from typing import List
from database.models import SecurityIssueModel
from utils.logger import logger

PRIVATE_KEY_REGEX = re.compile(r"-----BEGIN\s+[A-Z ]*PRIVATE\s+KEY-----", re.IGNORECASE)
AWS_KEY_REGEX = re.compile(r"([^A-Z0-9]|^)(AKIA[A-Z0-9]{16})([^A-Z0-9]|$)")
SECRET_KEYWORDS = {"password", "secret", "api_key", "apikey", "token", "passwd", "aws_secret"}

def scan_security(
    filepath: str,
    raw_content: str
) -> List[SecurityIssueModel]:
    """Analyzes a Python file for hardcoded secrets and dangerous function executions."""
    issues: List[SecurityIssueModel] = []
    lines = raw_content.splitlines()
    
    # 1. Regex line scan
    for idx, line in enumerate(lines, 1):
        if PRIVATE_KEY_REGEX.search(line):
            issues.append(SecurityIssueModel(
                id=None,
                file_id=0,
                issue_type="Hardcoded Private Key",
                severity="Critical",
                line_number=idx,
                code_snippet=line.strip(),
                description="Found a private key block header. Private keys must never be committed to source code."
            ))
            
        aws_match = AWS_KEY_REGEX.search(line)
        if aws_match:
            issues.append(SecurityIssueModel(
                id=None,
                file_id=0,
                issue_type="Hardcoded AWS Access Key",
                severity="Critical",
                line_number=idx,
                code_snippet=line.strip(),
                description="Found a potential AWS Access Key ID (AKIA...). Hardcoded credentials present a severe exploit risk."
            ))

    # 2. AST scan
    try:
        tree = ast.parse(raw_content)
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and isinstance(node.value, ast.Constant):
                        val = node.value.value
                        if isinstance(val, str) and len(val) > 4:
                            name_lower = target.id.lower()
                            if any(kw in name_lower for kw in SECRET_KEYWORDS):
                                placeholders = {"your_", "insert_", "dummy", "test", "placeholder", "todo", "<", ">", "env"}
                                if not any(p in val.lower() for p in placeholders):
                                    issues.append(SecurityIssueModel(
                                        id=None,
                                        file_id=0,
                                        issue_type="Hardcoded Secret Assignment",
                                        severity="High",
                                        line_number=node.lineno,
                                        code_snippet=f"{target.id} = '{val[:4]}...'",
                                        description=f"Variable '{target.id}' appears to be assigned a hardcoded secret token/password."
                                    ))
            
            elif isinstance(node, ast.Call):
                func = node.func
                if isinstance(func, ast.Name) and func.id == "eval":
                    issues.append(SecurityIssueModel(
                        id=None,
                        file_id=0,
                        issue_type="Dangerous Function (eval)",
                        severity="High",
                        line_number=node.lineno,
                        code_snippet=ast.unparse(node)[:100] if hasattr(ast, "unparse") else "eval(...)",
                        description="Found 'eval()'. eval() dynamically executes strings, posing a Remote Code Execution (RCE) vulnerability if input is untrusted."
                    ))
                elif isinstance(func, ast.Name) and func.id == "exec":
                    issues.append(SecurityIssueModel(
                        id=None,
                        file_id=0,
                        issue_type="Dangerous Function (exec)",
                        severity="High",
                        line_number=node.lineno,
                        code_snippet=ast.unparse(node)[:100] if hasattr(ast, "unparse") else "exec(...)",
                        description="Found 'exec()'. exec() dynamically runs Python statements, posing a critical security risk."
                    ))
                elif isinstance(func, ast.Attribute) and func.attr == "load" and isinstance(func.value, ast.Name) and func.value.id == "pickle":
                    issues.append(SecurityIssueModel(
                        id=None,
                        file_id=0,
                        issue_type="Insecure Deserialization (pickle.load)",
                        severity="Medium",
                        line_number=node.lineno,
                        code_snippet=ast.unparse(node)[:100] if hasattr(ast, "unparse") else "pickle.load(...)",
                        description="Found 'pickle.load()'. Deserializing untrusted data with pickle can execute arbitrary code."
                    ))
                elif isinstance(func, ast.Attribute) and func.attr == "system" and isinstance(func.value, ast.Name) and func.value.id == "os":
                    issues.append(SecurityIssueModel(
                        id=None,
                        file_id=0,
                        issue_type="Command Injection Risk (os.system)",
                        severity="High",
                        line_number=node.lineno,
                        code_snippet=ast.unparse(node)[:100] if hasattr(ast, "unparse") else "os.system(...)",
                        description="Found 'os.system()'. It spawns a subshell, making command injection very simple. Use 'subprocess' with structured args instead."
                    ))
                elif (
                    (isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name) and func.value.id == "subprocess") or
                    (isinstance(func, ast.Name) and func.id in {"run", "Popen", "call", "check_output", "check_call"})
                ):
                    for kw in node.keywords:
                        if kw.arg == "shell" and isinstance(kw.value, ast.Constant) and kw.value.value is True:
                            issues.append(SecurityIssueModel(
                                id=None,
                                file_id=0,
                                issue_type="Subprocess Command Injection (shell=True)",
                                severity="High",
                                line_number=node.lineno,
                                code_snippet=ast.unparse(node)[:100] if hasattr(ast, "unparse") else "subprocess.run(..., shell=True)",
                                description="Found subprocess execution with 'shell=True'. Spawning shells can trigger command injection vulnerabilities."
                            ))
                
                # SQL Injection detection
                elif isinstance(func, ast.Attribute) and func.attr in {"execute", "executemany"}:
                    if node.args:
                        first_arg = node.args[0]
                        is_dynamic = False
                        if isinstance(first_arg, ast.JoinedStr):
                            is_dynamic = True
                        elif isinstance(first_arg, ast.BinOp) and isinstance(first_arg.op, ast.Mod):
                            is_dynamic = True
                        elif (
                            isinstance(first_arg, ast.Call) and 
                            isinstance(first_arg.func, ast.Attribute) and 
                            first_arg.func.attr == "format"
                        ):
                            is_dynamic = True
                        
                        if is_dynamic:
                            issues.append(SecurityIssueModel(
                                id=None,
                                file_id=0,
                                issue_type="SQL Injection Risk",
                                severity="High",
                                line_number=node.lineno,
                                code_snippet=ast.unparse(node)[:100] if hasattr(ast, "unparse") else "execute(...)",
                                description="Found dynamic string formatting inside database execute() call. This can lead to SQL Injection. Use parameterized queries instead."
                            ))
                
                # Weak cryptographic hashing
                elif (
                    isinstance(func, ast.Attribute) and 
                    func.attr in {"md5", "sha1"} and 
                    isinstance(func.value, ast.Name) and 
                    func.value.id == "hashlib"
                ):
                    issues.append(SecurityIssueModel(
                        id=None,
                        file_id=0,
                        issue_type="Weak Cryptographic Hash (MD5/SHA1)",
                        severity="Medium",
                        line_number=node.lineno,
                        code_snippet=ast.unparse(node)[:100] if hasattr(ast, "unparse") else "hashlib.md5/sha1(...)",
                        description="MD5 and SHA1 are cryptographically broken algorithms vulnerable to collision attacks. Use SHA-256 (hashlib.sha256) or SHA-3 instead."
                    ))
                elif isinstance(func, ast.Name) and func.id in {"md5", "sha1"}:
                    issues.append(SecurityIssueModel(
                        id=None,
                        file_id=0,
                        issue_type="Weak Cryptographic Hash (MD5/SHA1)",
                        severity="Medium",
                        line_number=node.lineno,
                        code_snippet=ast.unparse(node)[:100] if hasattr(ast, "unparse") else f"{func.id}(...)",
                        description="MD5 and SHA1 are cryptographically broken algorithms. Use SHA-256 or SHA-3 instead."
                    ))
            
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name in {"xml.etree.ElementTree", "xml.dom.minidom"}:
                        issues.append(SecurityIssueModel(
                            id=None,
                            file_id=0,
                            issue_type="Insecure XML Parser",
                            severity="Medium",
                            line_number=node.lineno,
                            code_snippet=f"import {alias.name}",
                            description=f"Using insecure standard XML parser '{alias.name}'. Standard XML parsers are vulnerable to XML External Entity (XXE) and XML Entity Expansion attacks. Use 'defusedxml' instead."
                        ))
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    is_insecure = False
                    if node.module in {"xml.etree.ElementTree", "xml.dom.minidom"}:
                        is_insecure = True
                    elif node.module == "xml.etree" and any(n.name == "ElementTree" for n in node.names):
                        is_insecure = True
                    elif node.module == "xml.dom" and any(n.name == "minidom" for n in node.names):
                        is_insecure = True
                    
                    if is_insecure:
                        issues.append(SecurityIssueModel(
                            id=None,
                            file_id=0,
                            issue_type="Insecure XML Parser",
                            severity="Medium",
                            line_number=node.lineno,
                            code_snippet=f"from {node.module} import ...",
                            description="Using insecure standard XML parser. Standard XML parsers are vulnerable to XML External Entity (XXE) and XML Entity Expansion attacks. Use 'defusedxml' instead."
                        ))
    except Exception as e:
        logger.error(f"Error parsing AST security for {filepath}: {e}")

    return issues
