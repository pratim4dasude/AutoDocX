import hashlib
from collections import Counter
from pathlib import Path
from typing import Any

from app.services.code_parser import PythonCodeParser
from app.services.project_analyzer import ProjectAnalyzer


class ProjectScanner:
    """
    Scans and analyzes a local project directory.

    The scanner:
    - ignores unnecessary folders and files
    - ignores generated documentation/workspace output
    - ignores large/binary files that should not go to LLM
    - lists project files
    - counts directories
    - counts file extensions
    - calculates project size
    - calculates SHA-256 file hashes
    - parses Python source files
    - analyzes project-level relationships
    """

    MAX_SCANNED_FILE_SIZE_BYTES = 1_000_000

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
        "workspace",
        "assets",
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

        # Generated/exported docs
        ".html",
        ".htm",

        # Images/screenshots
        ".png",
        ".jpg",
        ".jpeg",
        ".webp",
        ".gif",
        ".svg",
        ".ico",

        # Documents/archives/binaries
        ".pdf",
        ".docx",
        ".pptx",
        ".xlsx",
        ".zip",
        ".tar",
        ".gz",
        ".7z",
        ".rar",
        ".exe",
        ".dll",
        ".bin",
        ".db",
        ".sqlite",
        ".sqlite3",
    }

    def __init__(self) -> None:
        self.code_parser = PythonCodeParser()
        self.project_analyzer = ProjectAnalyzer()

    def scan_project(
        self,
        project_path: str,
    ) -> dict[str, Any]:
        root_path = (
            Path(project_path)
            .expanduser()
            .resolve()
        )

        self._validate_project_path(
            root_path=root_path,
        )

        files: list[str] = []
        file_hashes: dict[str, str] = {}
        file_types: Counter[str] = Counter()

        total_size_bytes = 0
        total_directories = 0
        ignored_items = 0

        for current_path in root_path.rglob("*"):
            relative_path = (
                current_path.relative_to(
                    root_path
                )
            )

            if self._should_ignore(
                relative_path=relative_path,
            ):
                ignored_items += 1
                continue

            if current_path.is_dir():
                total_directories += 1
                continue

            if not current_path.is_file():
                continue

            try:
                file_size = (
                    current_path.stat().st_size
                )

                if (
                    file_size
                    > self.MAX_SCANNED_FILE_SIZE_BYTES
                ):
                    ignored_items += 1
                    continue

                file_hash = self._calculate_file_hash(
                    file_path=current_path,
                )

            except OSError:
                ignored_items += 1
                continue

            relative_path_string = (
                relative_path.as_posix()
            )

            files.append(
                relative_path_string
            )

            file_hashes[
                relative_path_string
            ] = file_hash

            total_size_bytes += file_size

            file_extension = (
                current_path.suffix.lower()
            )

            if file_extension:
                file_types[file_extension] += 1
            else:
                file_types[
                    "[no extension]"
                ] += 1

        files.sort()

        file_hashes = dict(
            sorted(file_hashes.items())
        )

        parsed_files = (
            self._parse_python_files(
                root_path=root_path,
                files=files,
            )
        )

        project_analysis = (
            self.project_analyzer
            .analyze_project(
                project_root=root_path,
                parsed_files=parsed_files,
            )
        )

        return {
            "project_name": root_path.name,
            "project_path": str(root_path),
            "total_files": len(files),
            "total_directories": (
                total_directories
            ),
            "total_size_bytes": (
                total_size_bytes
            ),
            "ignored_items": ignored_items,
            "file_types": dict(
                sorted(file_types.items())
            ),
            "files": files,
            "file_hashes": file_hashes,
            "parsed_files": parsed_files,
            "project_analysis": (
                project_analysis
            ),
        }

    def _parse_python_files(
        self,
        root_path: Path,
        files: list[str],
    ) -> list[dict[str, Any]]:
        parsed_files: list[
            dict[str, Any]
        ] = []

        for relative_file_path in files:
            if not relative_file_path.lower().endswith(
                ".py"
            ):
                continue

            absolute_file_path = (
                root_path
                / relative_file_path
            )

            try:
                file_size = (
                    absolute_file_path
                    .stat()
                    .st_size
                )

            except OSError:
                continue

            if (
                file_size
                > self.MAX_SCANNED_FILE_SIZE_BYTES
            ):
                continue

            parsed_file = (
                self.code_parser.parse_file(
                    project_root=root_path,
                    relative_file_path=(
                        relative_file_path
                    ),
                )
            )

            parsed_files.append(
                parsed_file
            )

        return parsed_files

    def _should_ignore(
        self,
        relative_path: Path,
    ) -> bool:
        path_parts = set(
            relative_path.parts
        )

        if path_parts.intersection(
            self.IGNORED_DIRECTORIES
        ):
            return True

        if (
            relative_path.name
            in self.IGNORED_FILES
        ):
            return True

        if (
            relative_path.suffix.lower()
            in self.IGNORED_EXTENSIONS
        ):
            return True

        return False

    @staticmethod
    def _calculate_file_hash(
        file_path: Path,
    ) -> str:
        sha256_hash = hashlib.sha256()

        with file_path.open("rb") as file_handle:
            while True:
                file_chunk = file_handle.read(
                    1024 * 1024
                )

                if not file_chunk:
                    break

                sha256_hash.update(
                    file_chunk
                )

        return sha256_hash.hexdigest()

    @staticmethod
    def _validate_project_path(
        root_path: Path,
    ) -> None:
        if not root_path.exists():
            raise ValueError(
                "Project path does not exist: "
                f"{root_path}"
            )

        if not root_path.is_dir():
            raise ValueError(
                "Project path is not a directory: "
                f"{root_path}"
            )