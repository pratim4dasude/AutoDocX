from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent.parent

WORKSPACE_DIR = BASE_DIR / "workspace"
PROJECTS_DIR = WORKSPACE_DIR / "projects"
SNAPSHOTS_DIR = WORKSPACE_DIR / "snapshots"
GENERATED_DOCS_DIR = WORKSPACE_DIR / "generated_docs"
LOGS_DIR = WORKSPACE_DIR / "logs"


def create_required_directories() -> None:
    directories = [
        WORKSPACE_DIR,
        PROJECTS_DIR,
        SNAPSHOTS_DIR,
        GENERATED_DOCS_DIR,
        LOGS_DIR,
    ]

    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)