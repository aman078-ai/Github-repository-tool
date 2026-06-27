import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from typing import List, Dict, Any
from database.models import FunctionModel, FileModel, SecurityIssueModel

def create_complexity_distribution_chart(functions: List[FunctionModel]) -> go.Figure:
    """Creates a bar chart of function cyclomatic complexity categories."""
    categories = ["Low", "Medium", "High", "Very High"]
    counts = {cat: 0 for cat in categories}
    for func in functions:
        counts[func.complexity_category] = counts.get(func.complexity_category, 0) + 1
        
    df = pd.DataFrame({
        "Complexity Category": list(counts.keys()),
        "Function Count": list(counts.values())
    })
    
    colors = {
        "Low": "#28a745",
        "Medium": "#ffc107",
        "High": "#fd7e14",
        "Very High": "#dc3545"
    }
    
    fig = px.bar(
        df,
        x="Complexity Category",
        y="Function Count",
        color="Complexity Category",
        color_discrete_map=colors,
        title="Cyclomatic Complexity Distribution",
        category_orders={"Complexity Category": categories}
    )
    
    fig.update_layout(
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#ccc'),
        xaxis=dict(gridcolor='#333', title=None),
        yaxis=dict(gridcolor='#333', title="Count"),
        showlegend=False
    )
    return fig

def create_doc_coverage_chart(doc_results: Dict[str, Any]) -> go.Figure:
    """Creates a pie chart showing documented vs undocumented items."""
    documented = (
        doc_results.get("modules_with_docstrings", 0) +
        doc_results.get("classes_with_docstrings", 0) +
        doc_results.get("functions_with_docstrings", 0)
    )
    total = (
        doc_results.get("total_modules", 0) +
        doc_results.get("total_classes", 0) +
        doc_results.get("total_functions", 0)
    )
    undocumented = max(0, total - documented)
    
    df = pd.DataFrame({
        "Status": ["Documented", "Undocumented"],
        "Count": [documented, undocumented]
    })
    
    fig = px.pie(
        df,
        names="Status",
        values="Count",
        color="Status",
        color_discrete_map={"Documented": "#17a2b8", "Undocumented": "#4f5b66"},
        title="Documentation Coverage Breakdown"
    )
    
    fig.update_layout(
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#ccc'),
        legend=dict(font=dict(color='#ccc'))
    )
    return fig

def create_security_risk_chart(issues: List[SecurityIssueModel]) -> go.Figure:
    """Creates a bar chart showing security issues grouped by severity."""
    severities = ["Low", "Medium", "High", "Critical"]
    counts = {sev: 0 for sev in severities}
    for issue in issues:
        counts[issue.severity] = counts.get(issue.severity, 0) + 1
        
    df = pd.DataFrame({
        "Severity": list(counts.keys()),
        "Issue Count": list(counts.values())
    })
    
    colors = {
        "Low": "#17a2b8",
        "Medium": "#ffc107",
        "High": "#fd7e14",
        "Critical": "#dc3545"
    }
    
    fig = px.bar(
        df,
        x="Severity",
        y="Issue Count",
        color="Severity",
        color_discrete_map=colors,
        title="Security Issues by Severity",
        category_orders={"Severity": severities}
    )
    
    fig.update_layout(
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#ccc'),
        xaxis=dict(gridcolor='#333', title=None),
        yaxis=dict(gridcolor='#333', title="Count"),
        showlegend=False
    )
    return fig

def create_large_files_chart(files: List[FileModel]) -> go.Figure:
    """Creates a horizontal bar chart showing the top 10 largest files by line count."""
    sorted_files = sorted(files, key=lambda f: f.total_lines, reverse=True)[:10]
    
    df = pd.DataFrame({
        "File Path": [f.filepath for f in sorted_files],
        "Total Lines": [f.total_lines for f in sorted_files],
        "Code Lines": [f.code_lines for f in sorted_files]
    })
    
    fig = px.bar(
        df,
        y="File Path",
        x=["Code Lines", "Total Lines"],
        barmode="group",
        orientation="h",
        title="Top 10 Largest Files (Lines)",
        color_discrete_sequence=["#1e3c72", "#2a5298"]
    )
    
    fig.update_layout(
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#ccc'),
        xaxis=dict(gridcolor='#333', title="Lines Count"),
        yaxis=dict(gridcolor='#333', autorange="reversed", title=None),
        legend=dict(title=None, font=dict(color='#ccc'))
    )
    return fig

def create_code_comment_pie(code_lines: int, comment_lines: int, blank_lines: int) -> go.Figure:
    """Creates a pie chart showing the breakdown of code, comment, and blank lines."""
    df = pd.DataFrame({
        "Line Type": ["Source Code", "Comments", "Blank Lines"],
        "Lines": [code_lines, comment_lines, blank_lines]
    })
    
    fig = px.pie(
        df,
        names="Line Type",
        values="Lines",
        color="Line Type",
        color_discrete_map={
            "Source Code": "#2f5c8f",
            "Comments": "#28a745",
            "Blank Lines": "#4f5b66"
        },
        title="Line Composition"
    )
    
    fig.update_layout(
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#ccc'),
        legend=dict(font=dict(color='#ccc'))
    )
    return fig
