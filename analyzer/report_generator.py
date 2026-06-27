import csv
import json
from pathlib import Path
from typing import Dict, Any, List, Tuple
from database.models import RepositoryModel, FileModel, FunctionModel, MetricsModel, SecurityIssueModel, DuplicateCodeModel
from utils.logger import logger

REPORTS_DIR = Path("reports")
REPORTS_DIR.mkdir(exist_ok=True)

class ReportGenerator:
    def __init__(
        self,
        repo: RepositoryModel,
        files: List[Tuple[FileModel, List[FunctionModel], Any, List[SecurityIssueModel]]],
        metrics: MetricsModel,
        duplicates: List[DuplicateCodeModel],
        dead_code: Dict[str, List[str]]
    ):
        self.repo = repo
        self.files = files
        self.metrics = metrics
        self.duplicates = duplicates
        self.dead_code = dead_code

    def generate_json_report(self) -> Path:
        """Generates a comprehensive JSON analysis report."""
        report_path = REPORTS_DIR / f"report_{self.repo.id or 'temp'}.json"
        
        data = {
            "repository": {
                "path": self.repo.path,
                "scanned_at": self.repo.scanned_at,
                "health_score": self.repo.health_score,
                "status": self.repo.status
            },
            "metrics": {
                "total_files": self.metrics.total_files,
                "python_files": self.metrics.python_files,
                "total_lines": self.metrics.total_lines,
                "blank_lines": self.metrics.blank_lines,
                "comment_lines": self.metrics.comment_lines,
                "code_lines": self.metrics.code_lines,
                "average_file_size": self.metrics.average_file_size,
                "largest_file": self.metrics.largest_file,
                "smallest_file": self.metrics.smallest_file,
                "average_functions_per_file": self.metrics.average_functions_per_file,
                "average_classes_per_file": self.metrics.average_classes_per_file
            },
            "files": [
                {
                    "filepath": f_model.filepath,
                    "size_bytes": f_model.size_bytes,
                    "total_lines": f_model.total_lines,
                    "code_lines": f_model.code_lines,
                    "comment_lines": f_model.comment_lines,
                    "blank_lines": f_model.blank_lines,
                    "docstring_coverage": f_model.docstring_coverage,
                    "health_score": f_model.health_score,
                    "functions": [
                        {
                            "name": func.name,
                            "class_name": func.class_name,
                            "start_line": func.start_line,
                            "end_line": func.end_line,
                            "complexity": func.complexity,
                            "complexity_category": func.complexity_category,
                            "return_type": func.return_type,
                            "has_docstring": func.has_docstring
                        } for func in funcs
                    ],
                    "security_issues": [
                        {
                            "issue_type": issue.issue_type,
                            "severity": issue.severity,
                            "line_number": issue.line_number,
                            "code_snippet": issue.code_snippet,
                            "description": issue.description
                        } for issue in sec_issues
                    ]
                } for f_model, funcs, _, sec_issues in self.files
            ],
            "duplicates": [
                {
                    "file1": dup.file1_path,
                    "file2": dup.file2_path,
                    "matching_lines": dup.matching_lines,
                    "similarity_ratio": dup.similarity_ratio,
                    "code_snippet": dup.code_snippet
                } for dup in self.duplicates
            ],
            "dead_code": self.dead_code
        }
        
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
            
        logger.info(f"JSON Report written to: {report_path}")
        return report_path

    def generate_csv_summary(self) -> Path:
        """Generates a flat CSV file summarizing individual file metrics."""
        report_path = REPORTS_DIR / f"summary_{self.repo.id or 'temp'}.csv"
        
        with open(report_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                "File Path", "Size (bytes)", "Total Lines", "Code Lines",
                "Comment Lines", "Blank Lines", "Docstring Coverage (%)",
                "Functions Count", "Security Issues Count", "Health Score"
            ])
            
            for f_model, funcs, _, sec_issues in self.files:
                writer.writerow([
                    f_model.filepath, f_model.size_bytes, f_model.total_lines, f_model.code_lines,
                    f_model.comment_lines, f_model.blank_lines, round(f_model.docstring_coverage * 100, 2),
                    len(funcs), len(sec_issues), f_model.health_score
                ])
                
        logger.info(f"CSV Summary written to: {report_path}")
        return report_path

    def generate_markdown_report(self) -> Path:
        """Generates a clean Markdown summary report."""
        report_path = REPORTS_DIR / f"report_{self.repo.id or 'temp'}.md"
        
        lines = []
        lines.append(f"# Repository Analysis Report: {self.repo.path}")
        lines.append(f"Scanned at: `{self.repo.scanned_at}`")
        lines.append(f"Overall Code Quality Health Score: **{self.repo.health_score}/100**\n")
        
        lines.append("## Codebase Metrics")
        lines.append(f"- **Total Files**: {self.metrics.total_files}")
        lines.append(f"- **Python Files**: {self.metrics.python_files}")
        lines.append(f"- **Total Lines**: {self.metrics.total_lines}")
        lines.append(f"- **Blank Lines**: {self.metrics.blank_lines}")
        lines.append(f"- **Comment Lines**: {self.metrics.comment_lines}")
        lines.append(f"- **Code Lines**: {self.metrics.code_lines}")
        lines.append(f"- **Average File Size**: {round(self.metrics.average_file_size / 1024, 2)} KB")
        lines.append(f"- **Largest File**: {self.metrics.largest_file}")
        lines.append(f"- **Smallest File**: {self.metrics.smallest_file}")
        lines.append(f"- **Average Functions per File**: {round(self.metrics.average_functions_per_file, 2)}")
        lines.append(f"- **Average Classes per File**: {round(self.metrics.average_classes_per_file, 2)}\n")
        
        lines.append("## Security Risks")
        critical_sec = []
        for f_model, _, _, sec_issues in self.files:
            for issue in sec_issues:
                critical_sec.append(f"| {f_model.filepath} | {issue.line_number} | {issue.issue_type} | {issue.severity} | {issue.description} |")
                
        if critical_sec:
            lines.append("| File | Line | Issue | Severity | Description |")
            lines.append("| --- | --- | --- | --- | --- |")
            lines.extend(critical_sec)
        else:
            lines.append("*No security issues flagged!*\n")
        lines.append("")
        
        lines.append("## Duplication Matches")
        if self.duplicates:
            lines.append("| File 1 | File 2 | Matching Lines | Similarity |")
            lines.append("| --- | --- | --- | --- |")
            for dup in self.duplicates[:10]:
                lines.append(f"| {dup.file1_path} | {dup.file2_path} | {dup.matching_lines} | {round(dup.similarity_ratio * 100, 1)}% |")
        else:
            lines.append("*No significant duplications detected.*\n")
        lines.append("")
            
        lines.append("## Dead Code Summary")
        lines.append(f"- **Unused Files**: {len(self.dead_code.get('unused_files', []))}")
        lines.append(f"- **Unused Classes**: {len(self.dead_code.get('unused_classes', []))}")
        lines.append(f"- **Unused Functions**: {len(self.dead_code.get('unused_functions', []))}")
        lines.append(f"- **Unused Imports**: {len(self.dead_code.get('unused_imports', []))}")
        lines.append(f"- **Unused Variables**: {len(self.dead_code.get('unused_variables', []))}\n")
        
        with open(report_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
            
        logger.info(f"Markdown Report written to: {report_path}")
        return report_path

    def generate_html_report(self) -> Path:
        """Generates a beautiful self-contained HTML report with a dashboard design."""
        report_path = REPORTS_DIR / f"report_{self.repo.id or 'temp'}.html"
        
        sec_rows = ""
        for f_model, _, _, sec_issues in self.files:
            for issue in sec_issues:
                badge_class = f"badge-{issue.severity.lower()}"
                sec_rows += f"""
                <tr>
                    <td>{f_model.filepath}</td>
                    <td>{issue.line_number}</td>
                    <td>{issue.issue_type}</td>
                    <td><span class="badge {badge_class}">{issue.severity}</span></td>
                    <td>{issue.description}</td>
                </tr>
                """
        if not sec_rows:
            sec_rows = "<tr><td colspan='5' class='text-center'>No security issues identified!</td></tr>"
            
        dup_rows = ""
        for dup in self.duplicates[:15]:
            dup_rows += f"""
            <tr>
                <td>{dup.file1_path}</td>
                <td>{dup.file2_path}</td>
                <td>{dup.matching_lines}</td>
                <td><strong>{round(dup.similarity_ratio * 100, 1)}%</strong></td>
            </tr>
            """
        if not dup_rows:
            dup_rows = "<tr><td colspan='4' class='text-center'>No duplicates detected.</td></tr>"

        file_rows = ""
        for f_model, funcs, _, sec_issues in self.files:
            file_rows += f"""
            <tr>
                <td>{f_model.filepath}</td>
                <td>{round(f_model.size_bytes/1024, 1)} KB</td>
                <td>{f_model.total_lines}</td>
                <td>{f_model.code_lines}</td>
                <td>{round(f_model.docstring_coverage*100, 1)}%</td>
                <td>{len(sec_issues)}</td>
                <td><strong>{f_model.health_score}</strong></td>
            </tr>
            """
            
        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Repository Intelligence Report: {self.repo.path}</title>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background-color: #f4f6f9;
            color: #333;
            margin: 0;
            padding: 20px;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
        }}
        .header {{
            background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
            color: white;
            padding: 30px;
            border-radius: 8px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            margin-bottom: 25px;
        }}
        .header h1 {{ margin: 0 0 10px 0; font-size: 2.2rem; }}
        .header p {{ margin: 0; opacity: 0.9; font-size: 1.1rem; }}
        .dashboard-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            gap: 20px;
            margin-bottom: 25px;
        }}
        .card {{
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05);
            text-align: center;
        }}
        .card h3 {{ margin: 0 0 10px 0; color: #666; font-size: 0.9rem; text-transform: uppercase; letter-spacing: 1px; }}
        .card .value {{ font-size: 1.8rem; font-weight: bold; color: #1e3c72; }}
        .section {{
            background: white;
            padding: 25px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05);
            margin-bottom: 25px;
        }}
        .section h2 {{ margin-top: 0; border-bottom: 2px solid #eee; padding-bottom: 10px; color: #1e3c72; }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 15px;
        }}
        th, td {{
            padding: 12px 15px;
            text-align: left;
            border-bottom: 1px solid #eee;
        }}
        th {{ background-color: #f8f9fa; color: #555; }}
        tr:hover {{ background-color: #fdfdfd; }}
        .badge {{
            padding: 5px 10px;
            border-radius: 4px;
            font-size: 0.8rem;
            font-weight: bold;
            display: inline-block;
        }}
        .badge-critical {{ background-color: #dc3545; color: white; }}
        .badge-high {{ background-color: #fd7e14; color: white; }}
        .badge-medium {{ background-color: #ffc107; color: #333; }}
        .badge-low {{ background-color: #17a2b8; color: white; }}
        .text-center {{ text-align: center; }}
        .health-gauge {{
            font-size: 4rem;
            font-weight: bold;
            color: #28a745;
            margin: 15px 0;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Repository Analysis: {self.repo.path}</h1>
            <p>Scanned at: {self.repo.scanned_at} | Status: <strong>{self.repo.status}</strong></p>
        </div>

        <div class="dashboard-grid">
            <div class="card">
                <h3>Overall Health</h3>
                <div class="health-gauge">{self.repo.health_score}</div>
            </div>
            <div class="card">
                <h3>Total Lines</h3>
                <div class="value">{self.metrics.total_lines}</div>
            </div>
            <div class="card">
                <h3>Python Files</h3>
                <div class="value">{self.metrics.python_files}</div>
            </div>
            <div class="card">
                <h3>Average File Size</h3>
                <div class="value">{round(self.metrics.average_file_size / 1024, 1)} KB</div>
            </div>
        </div>

        <div class="section">
            <h2>Detailed Metrics</h2>
            <table>
                <tr><th>Metric</th><th>Value</th></tr>
                <tr><td>Total Files Scanned</td><td>{self.metrics.total_files}</td></tr>
                <tr><td>Python Files</td><td>{self.metrics.python_files}</td></tr>
                <tr><td>Blank Lines</td><td>{self.metrics.blank_lines}</td></tr>
                <tr><td>Comment Lines</td><td>{self.metrics.comment_lines}</td></tr>
                <tr><td>Source Code Lines</td><td>{self.metrics.code_lines}</td></tr>
                <tr><td>Largest File</td><td>{self.metrics.largest_file}</td></tr>
                <tr><td>Smallest File</td><td>{self.metrics.smallest_file}</td></tr>
                <tr><td>Average Functions/File</td><td>{round(self.metrics.average_functions_per_file, 2)}</td></tr>
                <tr><td>Average Classes/File</td><td>{round(self.metrics.average_classes_per_file, 2)}</td></tr>
            </table>
        </div>

        <div class="section">
            <h2>Security Vulnerabilities and Risks</h2>
            <table>
                <thead>
                    <tr>
                        <th>File</th>
                        <th>Line</th>
                        <th>Risk Category</th>
                        <th>Severity</th>
                        <th>Description</th>
                    </tr>
                </thead>
                <tbody>
                    {sec_rows}
                </tbody>
            </table>
        </div>

        <div class="section">
            <h2>Code Duplication Matches</h2>
            <table>
                <thead>
                    <tr>
                        <th>File 1</th>
                        <th>File 2</th>
                        <th>Matching Lines</th>
                        <th>Similarity Ratio</th>
                    </tr>
                </thead>
                <tbody>
                    {dup_rows}
                </tbody>
            </table>
        </div>

        <div class="section">
            <h2>Individual File Analysis</h2>
            <table>
                <thead>
                    <tr>
                        <th>File Path</th>
                        <th>Size</th>
                        <th>Total Lines</th>
                        <th>Code Lines</th>
                        <th>Docstrings</th>
                        <th>Security Issues</th>
                        <th>Health Score</th>
                    </tr>
                </thead>
                <tbody>
                    {file_rows}
                </tbody>
            </table>
        </div>
    </div>
</body>
</html>
"""
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(html_content)
            
        logger.info(f"HTML Report written to: {report_path}")
        return report_path
