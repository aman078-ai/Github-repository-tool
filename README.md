# GitHub Repository Intelligence Tool

An enterprise-grade static code analysis platform for Python repositories. This tool scans directory paths recursively, parses structures with Python Abstract Syntax Trees (AST), aggregates size metrics, analyzes cyclomatic complexity, maps import-level & function-level dependencies, flags credentials/RCE security concerns, measures docstring coverage ratios, detects duplications, and exports HTML, Markdown, JSON, and CSV reports.

---

## 🔍 Features

1. **AST AST-Based Parsing**: Inspects modules dynamically to extract classes, methods, functions, variables, decorators, inheritance trees, line numbers, and return annotations.
2. **Metrics Aggregation**: Computes physical metrics (Lines of Code, comments, blanks, file count, sizes) and frequencies.
3. **Cyclomatic Complexity**: Measures function and method code paths using Radon and categorizes risk thresholds.
4. **Dependency & Call Graphing**: Maps imports and function call hierarchies using NetworkX, with built-in circular import cycle detection.
5. **Security Scanning**: Audits assignments for hardcoded secrets, private keys, and detects command injection/Remote Code Execution (RCE) flaws like `eval()`, `exec()`, `os.system()`, and `subprocess` shells.
6. **Documentation Audit**: Analyzes docstring coverage across modules, classes, and functions, auditing README and LICENSE files.
7. **Duplication Indexing**: normalizes space and comments, hashes sliding-windows of blocks, merges consecutive sequences, and computes difflib similarity percentages.
8. **Structured Reporting**: Automatically exports JSON dump structures, CSV files, MD summaries, and a responsive HTML dashboard.
9. **SQLite Storage**: Cascades database transaction models for repository scan iterations to allow historical records querying and re-analysis.
10. **Interactive Dashboard**: Modern Streamlit web application with sidebar history loaders and Plotly visualization charts.

---

## 🛠️ Tech Stack
- **Core**: Python 3.12, SQLite, AST, difflib, hashlib
- **UI**: Streamlit
- **Visuals**: Plotly, NetworkX, Matplotlib
- **Metrics**: Radon, Pandas
- **Infrastructure**: Docker, Docker Compose, GitHub Actions, Rich Logging, PyYAML

---

## 🏗️ Architecture

```
analyzer/
    parser.py              # AST-based node visitor
    repository.py          # Filesystem walker & run coordinator
    metrics.py             # Base line count metrics aggregator
    complexity.py          # Radon cyclomatic complexity grader
    dependencies.py        # Import/call graphing & circular cycles checker
    duplicate_detector.py  # Sliding window hash code matcher
    dead_code.py           # Cross-file reference compiler
    documentation.py       # Docstring checker
    security.py            # Hardcoded keys & dangerous call auditor
    report_generator.py    # HTML, MD, JSON, CSV file builders
    ai_interfaces.py       # Future LLM extensions abstract classes
visualization/
    dependency_graph.py    # Plotly/NetworkX scatter graph layouts
    charts.py              # Resuable Plotly express figures
database/
    database.py            # raw SQLite query routines
    models.py              # Dataclasses schemas mapping
ui/
    streamlit_app.py       # Main dashboard entrypoint
    pages/                 # Specific metrics panels
utils/
    helpers.py             # Size/duration formatters & timer
    logger.py              # Rich logging configurations
    config.py              # YAML settings parser
```

---

## 🚀 Installation & Usage

### Option 1: Local Virtual Environment
1. Ensure Python 3.12 is installed on your system.
2. Clone the repository and navigate to the directory:
   ```bash
   git clone <repository_url>
   cd github-repository-tool
   ```
3. Create and activate a virtual environment:
   ```bash
   python -m venv .venv
   # Windows:
   .venv\Scripts\activate
   # Linux/macOS:
   source .venv/bin/activate
   ```
4. Install package dependencies:
   ```bash
   pip install -r requirements.txt
   ```
5. Run the Streamlit Dashboard:
   ```bash
   streamlit run ui/streamlit_app.py
   ```

### Option 2: Docker Compose (One Command Startup)
1. Ensure Docker and Docker Compose are installed.
2. Build and start the container service:
   ```bash
   docker-compose up --build
   ```
3. Open `http://localhost:8501` in your browser.

---

## 🧪 Testing
Unit tests are written using `pytest`. Run tests and print coverage stats:
```bash
pytest --cov=analyzer --cov=database --cov=utils --cov-report=term-missing tests/
```

---

## 🔮 Future AI Extensions (Design Phase)
This repository includes abstract interfaces inside `analyzer/ai_interfaces.py` specifying method contracts to integrate large language models for:
- Repository Architectural Summaries
- Bug Risk Prediction
- Automated Refactoring and Improvements
- Natural Language Code Search

---

## 📝 License
Distributed under the MIT License. See [LICENSE](LICENSE) for more information.
