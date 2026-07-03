import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4


class ScanStorage:
    """
    Stores and retrieves AutoDocX project scan results.

    Scans are saved under:

        workspace/scans/<project_name>/<scan_id>.json
    """

    def __init__(
        self,
        workspace_path: str | Path = "workspace",
    ) -> None:
        self.workspace_path = Path(
            workspace_path
        ).expanduser().resolve()

        self.scans_directory = (
            self.workspace_path / "scans"
        )

        self.scans_directory.mkdir(
            parents=True,
            exist_ok=True,
        )

    def save_scan(
        self,
        scan_result: dict[str, Any],
    ) -> dict[str, str]:
        project_name = scan_result.get(
            "project_name"
        )

        if not isinstance(project_name, str):
            raise ValueError(
                "Scan result does not contain "
                "a valid project name."
            )

        safe_project_name = self._sanitize_name(
            project_name
        )

        project_directory = (
            self.scans_directory
            / safe_project_name
        )

        project_directory.mkdir(
            parents=True,
            exist_ok=True,
        )

        current_time = datetime.now(
            timezone.utc
        )

        created_at = current_time.isoformat()

        timestamp = current_time.strftime(
            "%Y%m%d_%H%M%S"
        )

        scan_id = (
            f"{timestamp}_{uuid4().hex[:8]}"
        )

        scan_file_path = (
            project_directory
            / f"{scan_id}.json"
        )

        stored_scan = {
            "scan_id": scan_id,
            "created_at": created_at,
            "project_name": project_name,
            "project_path": scan_result.get(
                "project_path"
            ),
            "scan_result": scan_result,
        }

        try:
            scan_file_path.write_text(
                json.dumps(
                    stored_scan,
                    indent=2,
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

        except OSError as error:
            raise RuntimeError(
                "Unable to save project scan: "
                f"{error}"
            ) from error

        return {
            "scan_id": scan_id,
            "created_at": created_at,
            "scan_file": str(
                scan_file_path
            ),
        }

    def get_scan(
        self,
        project_name: str,
        scan_id: str,
    ) -> dict[str, Any]:
        scan_file_path = (
            self._build_scan_file_path(
                project_name=project_name,
                scan_id=scan_id,
            )
        )

        if not scan_file_path.exists():
            raise ValueError(
                f"Scan not found: {scan_id}"
            )

        return self._read_scan_file(
            scan_file_path=scan_file_path,
        )

    def get_latest_scan(
        self,
        project_name: str,
    ) -> dict[str, Any]:
        scan_files = self._get_project_scan_files(
            project_name=project_name,
        )

        if not scan_files:
            raise ValueError(
                "No saved scans found for project: "
                f"{project_name}"
            )

        latest_scan_file = max(
            scan_files,
            key=lambda file_path: (
                file_path.stat().st_mtime
            ),
        )

        return self._read_scan_file(
            scan_file_path=latest_scan_file,
        )

    def list_scans(
        self,
        project_name: str,
    ) -> list[dict[str, Any]]:
        scan_files = self._get_project_scan_files(
            project_name=project_name,
        )

        scan_summaries: list[
            dict[str, Any]
        ] = []

        sorted_scan_files = sorted(
            scan_files,
            key=lambda file_path: (
                file_path.stat().st_mtime
            ),
            reverse=True,
        )

        for scan_file_path in sorted_scan_files:
            stored_scan = self._read_scan_file(
                scan_file_path=scan_file_path,
            )

            scan_result = stored_scan.get(
                "scan_result",
                {},
            )

            scan_summaries.append(
                {
                    "scan_id": stored_scan.get(
                        "scan_id"
                    ),
                    "created_at": stored_scan.get(
                        "created_at"
                    ),
                    "project_name": (
                        stored_scan.get(
                            "project_name"
                        )
                    ),
                    "project_path": (
                        stored_scan.get(
                            "project_path"
                        )
                    ),
                    "total_files": (
                        scan_result.get(
                            "total_files",
                            0,
                        )
                    ),
                    "total_directories": (
                        scan_result.get(
                            "total_directories",
                            0,
                        )
                    ),
                    "total_size_bytes": (
                        scan_result.get(
                            "total_size_bytes",
                            0,
                        )
                    ),
                    "parsed_python_files": (
                        scan_result.get(
                            "project_analysis",
                            {},
                        )
                        .get(
                            "statistics",
                            {},
                        )
                        .get(
                            "parsed_python_files",
                            0,
                        )
                    ),
                }
            )

        return scan_summaries

    def _get_project_scan_files(
        self,
        project_name: str,
    ) -> list[Path]:
        safe_project_name = self._sanitize_name(
            project_name
        )

        project_directory = (
            self.scans_directory
            / safe_project_name
        )

        if not project_directory.exists():
            return []

        return list(
            project_directory.glob("*.json")
        )

    def _build_scan_file_path(
        self,
        project_name: str,
        scan_id: str,
    ) -> Path:
        safe_project_name = self._sanitize_name(
            project_name
        )

        safe_scan_id = self._sanitize_name(
            scan_id
        )

        return (
            self.scans_directory
            / safe_project_name
            / f"{safe_scan_id}.json"
        )

    @staticmethod
    def _read_scan_file(
        scan_file_path: Path,
    ) -> dict[str, Any]:
        try:
            file_content = (
                scan_file_path.read_text(
                    encoding="utf-8"
                )
            )

            stored_scan = json.loads(
                file_content
            )

        except OSError as error:
            raise RuntimeError(
                "Unable to read scan file: "
                f"{error}"
            ) from error

        except json.JSONDecodeError as error:
            raise RuntimeError(
                "Invalid scan JSON file: "
                f"{error}"
            ) from error

        if not isinstance(
            stored_scan,
            dict,
        ):
            raise RuntimeError(
                "Stored scan must be "
                "a JSON object."
            )

        return stored_scan

    @staticmethod
    def _sanitize_name(
        value: str,
    ) -> str:
        sanitized_value = re.sub(
            pattern=r"[^a-zA-Z0-9_-]",
            repl="_",
            string=value,
        )

        sanitized_value = re.sub(
            pattern=r"_+",
            repl="_",
            string=sanitized_value,
        )

        sanitized_value = (
            sanitized_value.strip("_")
        )

        return sanitized_value or "unknown"