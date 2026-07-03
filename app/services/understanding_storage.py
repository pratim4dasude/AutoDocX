import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from app.core.config import (
    UNDERSTANDINGS_PATH,
)


class UnderstandingStorage:
    """
    Stores and retrieves generated project
    understanding results.

    Files are saved under:

        workspace/understandings/
        <project_name>/<understanding_id>.json
    """

    def __init__(
        self,
        storage_path: str | Path | None = None,
    ) -> None:
        if storage_path is None:
            self.storage_path = (
                UNDERSTANDINGS_PATH
            )
        else:
            self.storage_path = Path(
                storage_path
            )

        self.storage_path.mkdir(
            parents=True,
            exist_ok=True,
        )

    def save_understanding(
        self,
        understanding_result: dict[str, Any],
    ) -> dict[str, str]:
        project_name = understanding_result.get(
            "project_name"
        )

        scan_id = understanding_result.get(
            "scan_id"
        )

        if not project_name:
            raise ValueError(
                "Understanding result does not "
                "contain a project name."
            )

        if not scan_id:
            raise ValueError(
                "Understanding result does not "
                "contain a scan ID."
            )

        created_at = datetime.now(
            timezone.utc
        )

        understanding_id = (
            created_at.strftime(
                "%Y%m%d_%H%M%S"
            )
            + "_"
            + uuid4().hex[:8]
        )

        project_directory = (
            self.storage_path
            / self._sanitize_name(
                str(project_name)
            )
        )

        project_directory.mkdir(
            parents=True,
            exist_ok=True,
        )

        understanding_file = (
            project_directory
            / f"{understanding_id}.json"
        )

        stored_data = {
            "understanding_id": (
                understanding_id
            ),
            "created_at": (
                created_at.isoformat()
            ),
            "project_name": project_name,
            "scan_id": scan_id,
            "provider": (
                understanding_result.get(
                    "provider"
                )
            ),
            "model": understanding_result.get(
                "model"
            ),
            "understanding": (
                understanding_result.get(
                    "understanding",
                    {},
                )
            ),
        }

        temporary_file = (
            understanding_file.with_suffix(
                ".tmp"
            )
        )

        try:
            temporary_file.write_text(
                json.dumps(
                    stored_data,
                    indent=2,
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            temporary_file.replace(
                understanding_file
            )

        except OSError as error:
            if temporary_file.exists():
                temporary_file.unlink(
                    missing_ok=True
                )

            raise RuntimeError(
                "Failed to save project "
                "understanding."
            ) from error

        return {
            "understanding_id": (
                understanding_id
            ),
            "created_at": (
                created_at.isoformat()
            ),
            "understanding_file": str(
                understanding_file
            ),
        }

    def get_understanding(
        self,
        project_name: str,
        understanding_id: str,
    ) -> dict[str, Any]:
        understanding_file = (
            self._build_file_path(
                project_name=project_name,
                understanding_id=(
                    understanding_id
                ),
            )
        )

        if not understanding_file.exists():
            raise ValueError(
                "Understanding not found: "
                f"{understanding_id}"
            )

        return self._read_file(
            file_path=understanding_file,
        )

    def get_latest_understanding(
        self,
        project_name: str,
    ) -> dict[str, Any]:
        files = self._get_project_files(
            project_name=project_name,
        )

        if not files:
            raise ValueError(
                "No saved understandings found "
                f"for project: {project_name}"
            )

        return self._read_file(
            file_path=files[0],
        )

    def list_understandings(
        self,
        project_name: str,
    ) -> list[dict[str, Any]]:
        files = self._get_project_files(
            project_name=project_name,
        )

        summaries: list[
            dict[str, Any]
        ] = []

        for file_path in files:
            stored_data = self._read_file(
                file_path=file_path,
            )

            summaries.append(
                {
                    "understanding_id": (
                        stored_data.get(
                            "understanding_id"
                        )
                    ),
                    "created_at": (
                        stored_data.get(
                            "created_at"
                        )
                    ),
                    "project_name": (
                        stored_data.get(
                            "project_name"
                        )
                    ),
                    "scan_id": (
                        stored_data.get(
                            "scan_id"
                        )
                    ),
                    "provider": (
                        stored_data.get(
                            "provider"
                        )
                    ),
                    "model": stored_data.get(
                        "model"
                    ),
                }
            )

        return summaries

    def _get_project_files(
        self,
        project_name: str,
    ) -> list[Path]:
        project_directory = (
            self.storage_path
            / self._sanitize_name(
                project_name
            )
        )

        if not project_directory.exists():
            return []

        return sorted(
            project_directory.glob(
                "*.json"
            ),
            key=lambda file_path: (
                file_path.stat().st_mtime
            ),
            reverse=True,
        )

    def _build_file_path(
        self,
        project_name: str,
        understanding_id: str,
    ) -> Path:
        sanitized_project = (
            self._sanitize_name(
                project_name
            )
        )

        sanitized_id = self._sanitize_name(
            understanding_id
        )

        return (
            self.storage_path
            / sanitized_project
            / f"{sanitized_id}.json"
        )

    @staticmethod
    def _read_file(
        file_path: Path,
    ) -> dict[str, Any]:
        try:
            stored_data = json.loads(
                file_path.read_text(
                    encoding="utf-8"
                )
            )

        except (
            OSError,
            json.JSONDecodeError,
        ) as error:
            raise RuntimeError(
                "Failed to read saved project "
                "understanding."
            ) from error

        if not isinstance(
            stored_data,
            dict,
        ):
            raise RuntimeError(
                "Saved understanding file "
                "contains invalid data."
            )

        return stored_data

    @staticmethod
    def _sanitize_name(
        value: str,
    ) -> str:
        cleaned_value = re.sub(
            r"[^a-zA-Z0-9_.-]+",
            "_",
            value.strip(),
        )

        cleaned_value = (
            cleaned_value.strip("._")
        )

        if not cleaned_value:
            raise ValueError(
                "Invalid storage name."
            )

        return cleaned_value