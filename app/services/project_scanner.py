from collections import Counter
from pathlib import Path
from typing import Any

from app.services.code_parser import PythonCodeParser


class ProjectScanner:
    """
    Scans a local project directory.

    The scanner:
    - ignores unnecessary folders and files
    - lists project files
    - counts directories
    - counts file extensions
    - calculates project size
    - parses Python source files
    """

    IGNORED_DIRECTORIES = {
        ".git",
        ".idea",
        ".vscode",
        ".venv",
        "venv",
        "env",
        "__pycache__",
        ".pytest_cache",
        ".mypy_cache",
        ".ruff_cache",
        "node_modules",
        "dist",
        "build",
        "coverage",
        "htmlcov",
        ".tox",
        ".next",
    }

    IGNORED_FILES = {
        ".DS_Store",
        "Thumbs.db",
    }

    IGNORED_EXTENSIONS = {
        ".pyc",
        ".pyo",
        ".pyd",
        ".log",
        ".tmp",
        ".temp",
        ".swp",
        ".swo",
    }

    def __init__(self) -> None:
        self.code_parser = PythonCodeParser()

    def scan_project(
        self,
        project_path: str,
    ) -> dict[str, Any]:
        root_path = Path(project_path).expanduser().resolve()

        self._validate_project_path(root_path)

        files: list[str] = []
        file_types: Counter[str] = Counter()

        total_size_bytes = 0
        total_directories = 0
        ignored_items = 0

        for current_path in root_path.rglob("*"):
            relative_path = current_path.relative_to(root_path)

            if self._should_ignore(relative_path):
                ignored_items += 1
                continue

            if current_path.is_dir():
                total_directories += 1
                continue

            if not current_path.is_file():
                continue

            try:
                file_size = current_path.stat().st_size
            except OSError:
                ignored_items += 1
                continue

            relative_path_string = relative_path.as_posix()

            files.append(relative_path_string)
            total_size_bytes += file_size

            file_extension = current_path.suffix.lower()

            if file_extension:
                file_types[file_extension] += 1
            else:
                file_types["[no extension]"] += 1

        files.sort()

        parsed_files = self._parse_python_files(
            root_path=root_path,
            files=files,
        )

        return {
            "project_name": root_path.name,
            "project_path": str(root_path),
            "total_files": len(files),
            "total_directories": total_directories,
            "total_size_bytes": total_size_bytes,
            "ignored_items": ignored_items,
            "file_types": dict(
                sorted(file_types.items())
            ),
            "files": files,
            "parsed_files": parsed_files,
        }

    def _parse_python_files(
        self,
        root_path: Path,
        files: list[str],
    ) -> list[dict[str, Any]]:
        parsed_files: list[dict[str, Any]] = []

        for relative_file_path in files:
            if not relative_file_path.lower().endswith(".py"):
                continue

            parsed_file = self.code_parser.parse_file(
                project_root=root_path,
                relative_file_path=relative_file_path,
            )

            parsed_files.append(parsed_file)

        return parsed_files

    def _should_ignore(
        self,
        relative_path: Path,
    ) -> bool:
        path_parts = set(relative_path.parts)

        if path_parts.intersection(
            self.IGNORED_DIRECTORIES
        ):
            return True

        if relative_path.name in self.IGNORED_FILES:
            return True

        if (
            relative_path.suffix.lower()
            in self.IGNORED_EXTENSIONS
        ):
            return True

        return False

    @staticmethod
    def _validate_project_path(
        root_path: Path,
    ) -> None:
        if not root_path.exists():
            raise ValueError(
                f"Project path does not exist: {root_path}"
            )

        if not root_path.is_dir():
            raise ValueError(
                f"Project path is not a directory: {root_path}"
            )