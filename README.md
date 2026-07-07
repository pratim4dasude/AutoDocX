# AutoDocX

AutoDocX is a local documentation automation tool for Python projects. It scans a codebase, understands the source structure, detects what changed, and generates clean versioned HTML documentation that stays close to the real implementation.
> The idea is simple: developers should not need to manually rewrite documentation every time the code changes. AutoDocX turns the current project state into readable developer documentation and keeps a history of generated versions.

> It is built as a local FastAPI + Streamlit system where the user provides a project path, triggers a documentation sync, and receives an updated HTML document for the project.

---

## What it can do

| Capability | Behaviour |
|---|---|
| Scan a project | Reads files, folders, file types, sizes, and project metadata |
| Understand Python code | Extracts modules, imports, classes, functions, and main entry points |
| Explain main flows | Describes what important functions do and what they call |
| Detect changes | Compares the latest project state with the previous documented state |
| Update documentation | Regenerates documentation based on current code changes |
| Preserve versions | Saves previous documentation versions instead of overwriting history |
| Provide a UI | Lets users run the documentation sync from a Streamlit interface |
| Expose APIs | Uses FastAPI endpoints for scan and documentation sync workflows |

---

## Why AutoDocX

Most project documentation becomes outdated because code changes faster than docs. This creates problems during handovers, onboarding, debugging, and reviews.

AutoDocX helps solve this by generating documentation directly from the codebase.

It is useful for:

- Understanding an unfamiliar project
- Creating internal developer documentation
- Explaining project flow to teammates or seniors
- Keeping documentation updated as the project changes
- Preparing clean project demos
- Maintaining a version history of generated docs
- Reducing manual documentation effort

---

## Architecture

```text
                              +----------------------+
                              |      Developer       |
                              |  Project path + sync |
                              +----------+-----------+
                                         |
                                         v
+--------------------------------------------------------------------------------+
|                               Interface Layer                                  |
|                                                                                |
|   +------------------+        +------------------+        +------------------+ |
|   |  Streamlit UI    | -----> |  API Client      | -----> |  Status Viewer   | |
|   +------------------+        +------------------+        +------------------+ |
+----------------------------------------+---------------------------------------+
                                         |
                                         v
+--------------------------------------------------------------------------------+
|                                  API Layer                                     |
|                                                                                |
|   +------------------+        +------------------+        +------------------+ |
|   |  FastAPI App     | -----> |  Sync Endpoint   | -----> |  Error Handler   | |
|   +------------------+        +------------------+        +------------------+ |
+----------------------------------------+---------------------------------------+
                                         |
                                         v
+--------------------------------------------------------------------------------+
|                              Sync Orchestration                                |
|                                                                                |
|   +------------------+        +------------------+        +------------------+ |
|   | Path Validator   | -----> | Sync Controller  | -----> | Result Builder   | |
|   +------------------+        +------------------+        +------------------+ |
+----------------------------------------+---------------------------------------+
                                         |
                                         v
+--------------------------------------------------------------------------------+
|                              Code Intelligence                                 |
|                                                                                |
|   +------------------+        +------------------+        +------------------+ |
|   | Project Scanner  | -----> | Python Analyzer  | -----> | Flow Extractor   | |
|   +------------------+        +------------------+        +------------------+ |
|            |                         |                          |              |
|            v                         v                          v              |
|   +------------------+        +------------------+        +------------------+ |
|   | File Metadata    |        | Classes/Functions|        | Main Call Flow   | |
|   +------------------+        +------------------+        +------------------+ |
+----------------------------------------+---------------------------------------+
                                         |
                                         v
+--------------------------------------------------------------------------------+
|                              Change Intelligence                               |
|                                                                                |
|   +------------------+        +------------------+        +------------------+ |
|   | Previous State   | -----> | Change Detector  | -----> | Changed File Set | |
|   +------------------+        +------------------+        +------------------+ |
+----------------------------------------+---------------------------------------+
                                         |
                                         v
+--------------------------------------------------------------------------------+
|                            Documentation Engine                                |
|                                                                                |
|   +------------------+        +------------------+        +----------------+   |
|   | Project Summary  | -----> | Module Docs      | -----> | Function Docs  |   |
|   +------------------+        +------------------+        +----------------+   |
|                                                                  |             |
|                                                                  v             |
|                                                       +------------------+     |
|                                                       | HTML Generator   |     |
|                                                       +------------------+     |
+----------------------------------------+---------------------------------------+
                                         |
                                         v
+--------------------------------------------------------------------------------+
|                              Output Layer                                      |
|                                                                                |
|   +------------------+        +------------------+        +------------------+ |
|   | latest.html      |        | Versioned Docs   |        | project_state    | |
|   +------------------+        +------------------+        +------------------+ |
+--------------------------------------------------------------------------------+
```

## How it works

AutoDocX runs a documentation sync pipeline whenever the user provides a project path.

### 1. Project path input

The developer enters a local project directory in the Streamlit UI.

Example:

```
C:\Users\YourName\PycharmProjects\AutoDocX
```

The UI sends the path to the FastAPI backend.

### 2. Request validation

The backend validates the incoming request before running the sync.

It checks:

- Whether the project path exists
- Whether the path is a directory
- Whether the backend can access the folder
- Whether the request body is valid

This prevents the pipeline from running on invalid input.

### 3. Project scanning

The scanner walks through the project directory and collects basic project metadata.

It reads:

- Project name
- Project path
- Total files
- Total directories
- File extensions
- File sizes
- Source files
- Ignored files and folders

The scanner skips unnecessary folders such as:

```
.venv
venv
__pycache__
.git
node_modules
dist
build
.idea
.vscode
```

This keeps the documentation focused on the actual source code.

### 4. Code analysis

The analyzer reads Python files and extracts code-level structure.

It identifies:

- Modules
- Imports
- Classes
- Functions
- Main functions
- Function signatures
- Module responsibilities
- Function-level purpose
- Function call relationships where available

This is the layer that turns raw files into useful developer information.

### 5. Project knowledge building

The project knowledge builder converts scan and analysis results into structured documentation-ready context.

It prepares:

- Project overview
- Module summaries
- Important functions
- Main execution flow explanations
- Developer-readable descriptions
- Code responsibility mapping

This step makes the output more useful than a simple file listing.

### 6. Change detection

AutoDocX stores the previous project state and compares it with the latest scan.

It detects:

- Added files
- Modified files
- Deleted files
- Unchanged files

This allows AutoDocX to understand what changed between documentation runs.

### 7. Documentation generation

The documentation builder creates the final HTML documentation.

The generated documentation can include:

- Project summary
- Project statistics
- Module descriptions
- Function explanations
- Main flow details
- Changed files summary
- Version information
- Developer notes

### 8. Versioned output

AutoDocX saves the latest documentation while also preserving previous versions.

This makes it possible to track how documentation changes as the project evolves.

Example:

```
docs_output/
├── latest.html
├── versions/
│   ├── AutoDocX_v1.html
│   ├── AutoDocX_v2.html
│   └── AutoDocX_v3.html
└── metadata/
    └── project_state.json
```

---

## Technology

| Tool | Role |
|---|---|
| Python | Core programming language |
| FastAPI | Backend API layer |
| Streamlit | Local user interface |
| Uvicorn | ASGI server for running FastAPI |
| Python AST | Source code parsing and analysis |
| HTML | Final documentation output format |
| JSON | Project state and metadata storage |
| Local file system | Documentation output and version storage |

---

## Getting started

### Prerequisites

Make sure you have:

- Python 3.10+
- pip
- Git
- PowerShell, Command Prompt, or terminal
- A browser for Streamlit and generated HTML docs

### 1. Clone the repository

```bash
git clone <your-repository-url>
cd AutoDocX
```

### 2. Create a virtual environment

**Windows PowerShell**

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

**macOS / Linux**

```bash
python3 -m venv .venv
source .venv/bin/activate
```

After activation, your terminal should show the virtual environment name.

Example:

```
(.venv) PS C:\Users\YourName\PycharmProjects\AutoDocX>
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Start the FastAPI backend

Run this from the project root:

```bash
uvicorn app.main:app --reload
```

Backend URL:

```
http://127.0.0.1:8000
```

Swagger API docs:

```
http://127.0.0.1:8000/docs
```

### 5. Start the Streamlit UI

Open a second terminal, activate the virtual environment again, and run:

```bash
streamlit run ui/streamlit_app.py
```

Streamlit usually opens at:

```
http://localhost:8501
```

---

## API usage

### Sync project documentation

```
POST /api/projects/documentation/sync
```

This endpoint scans the given project path, analyzes the code, detects changes, and generates or updates documentation.

**Request body**

```json
{
  "project_path": "C:\\Users\\YourName\\PycharmProjects\\AutoDocX"
}
```

**Example success response**

```json
{
  "status": "success",
  "message": "Documentation synced successfully.",
  "project_name": "AutoDocX",
  "documentation_path": "docs_output/latest.html",
  "changed_files": 2,
  "version": "v4"
}
```

**Example error response**

```json
{
  "status": "error",
  "message": "Invalid project path. The provided directory does not exist."
}
```

---

## Running a complete demo

Use this flow when presenting the project:

1. Start the FastAPI backend.
2. Start the Streamlit UI.
3. Enter the AutoDocX project path.
4. Run documentation sync.
5. Open the generated `latest.html`.
6. Show the project overview and module explanations.
7. Modify one Python file.
8. Run sync again.
9. Show that AutoDocX detects the changed file.
10. Open the latest documentation.
11. Show that older versions are still preserved.

---

## Example workflow

```
Developer enters project path
        ↓
AutoDocX scans files and folders
        ↓
Python files are analyzed
        ↓
Functions, classes, imports, and entry points are extracted
        ↓
Current project state is compared with previous state
        ↓
Changed files are identified
        ↓
HTML documentation is generated
        ↓
Latest documentation and version history are saved
```

---

## Output

AutoDocX generates local HTML documentation.

Typical output:

```
docs_output/
├── latest.html
├── versions/
│   ├── AutoDocX_v1.html
│   ├── AutoDocX_v2.html
│   └── AutoDocX_v3.html
└── metadata/
    └── project_state.json
```

### Output files

| File | Purpose |
|---|---|
| `latest.html` | Most recent generated documentation |
| `versions/` | Previous documentation versions |
| `project_state.json` | Saved project snapshot used for change detection |
| `metadata/` | Supporting sync and version metadata |

---

## Current status

AutoDocX currently supports the core local documentation workflow.

**Completed:**

- Local project scanning
- Python code analysis
- Function and class extraction
- Main function explanation
- Documentation sync API
- Streamlit UI
- HTML documentation generation
- Changed-file detection
- Documentation versioning

**Planned:**

- Unit tests for core modules
- Better function call graph generation
- Markdown export
- PDF export
- Git-based change detection
- Docker support
- CI/CD documentation generation
- Multi-project dashboard
- LLM-based explanation refinement

---

## Engineering approach

AutoDocX is designed as a modular pipeline. Each layer has a focused responsibility:

- The UI handles user interaction.
- The API handles requests and responses.
- The scanner handles file discovery.
- The analyzer handles code understanding.
- The sync engine coordinates the pipeline.
- The documentation builder creates the final output.
- The state store handles change tracking and versioning.

This separation makes the project easier to debug, extend, and test.
