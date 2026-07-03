import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from app.core.config import (
    DOCUMENTS_PATH,
)


class DocumentStorage:
    """
    Stores generated HTML documentation files
    and their metadata.
    """

    def __init__(
        self,
        storage_path: str | Path | None = None,
    ) -> None:
        if storage_path is None:
            self.storage_path = DOCUMENTS_PATH
        else:
            self.storage_path = Path(
                storage_path
            )

        self.storage_path.mkdir(
            parents=True,
            exist_ok=True,
        )

    def save_document(
        self,
        project_name: str,
        understanding_id: str,
        scan_id: str,
        html_content: str,
        previous_document_id: str | None = None,
        update_type: str = "initial",
        comparison_summary: (
            dict[str, Any] | None
        ) = None,
    ) -> dict[str, Any]:
        if not project_name.strip():
            raise ValueError(
                "Project name is required."
            )

        if not understanding_id.strip():
            raise ValueError(
                "Understanding ID is required."
            )

        if not scan_id.strip():
            raise ValueError(
                "Scan ID is required."
            )

        if not html_content.strip():
            raise ValueError(
                "HTML content is empty."
            )

        if update_type not in {
            "initial",
            "version_update",
        }:
            raise ValueError(
                "Invalid document update type."
            )

        created_at = datetime.now(
            timezone.utc
        )

        document_id = (
            created_at.strftime(
                "%Y%m%d_%H%M%S"
            )
            + "_"
            + uuid4().hex[:8]
        )

        project_directory = (
            self.storage_path
            / self._sanitize_name(
                project_name
            )
        )

        project_directory.mkdir(
            parents=True,
            exist_ok=True,
        )

        html_file = (
            project_directory
            / f"{document_id}.html"
        )

        metadata_file = (
            project_directory
            / f"{document_id}.json"
        )

        html_temp_file = (
            html_file.with_suffix(
                ".html.tmp"
            )
        )

        metadata_temp_file = (
            metadata_file.with_suffix(
                ".json.tmp"
            )
        )

        metadata: dict[str, Any] = {
            "document_id": document_id,
            "created_at": (
                created_at.isoformat()
            ),
            "project_name": project_name,
            "scan_id": scan_id,
            "understanding_id": (
                understanding_id
            ),
            "document_type": "html",
            "update_type": update_type,
            "previous_document_id": (
                previous_document_id
            ),
            "comparison_summary": (
                comparison_summary
            ),
            "document_file": str(
                html_file
            ),
            "metadata_file": str(
                metadata_file
            ),
        }

        try:
            html_temp_file.write_text(
                html_content,
                encoding="utf-8",
            )

            metadata_temp_file.write_text(
                json.dumps(
                    metadata,
                    indent=2,
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            html_temp_file.replace(
                html_file
            )

            metadata_temp_file.replace(
                metadata_file
            )

        except OSError as error:
            html_temp_file.unlink(
                missing_ok=True
            )

            metadata_temp_file.unlink(
                missing_ok=True
            )

            raise RuntimeError(
                "Failed to save generated "
                "documentation."
            ) from error

        return metadata

    def list_documents(
        self,
        project_name: str,
    ) -> list[dict[str, Any]]:
        project_directory = (
            self.storage_path
            / self._sanitize_name(
                project_name
            )
        )

        if not project_directory.exists():
            return []

        metadata_files = sorted(
            project_directory.glob(
                "*.json"
            ),
            key=lambda file_path: (
                file_path.stat().st_mtime
            ),
            reverse=True,
        )

        documents: list[
            dict[str, Any]
        ] = []

        for metadata_file in metadata_files:
            documents.append(
                self._read_metadata(
                    metadata_file
                )
            )

        return documents

    def get_latest_document_metadata(
        self,
        project_name: str,
    ) -> dict[str, Any]:
        documents = self.list_documents(
            project_name=project_name,
        )

        if not documents:
            raise ValueError(
                "No generated documents found "
                f"for project: {project_name}"
            )

        return documents[0]

    def get_document_metadata(
        self,
        project_name: str,
        document_id: str,
    ) -> dict[str, Any]:
        metadata_file = (
            self.storage_path
            / self._sanitize_name(
                project_name
            )
            / (
                f"{self._sanitize_name(document_id)}"
                ".json"
            )
        )

        if not metadata_file.exists():
            raise ValueError(
                "Document not found: "
                f"{document_id}"
            )

        return self._read_metadata(
            metadata_file
        )

    def get_document_file(
        self,
        project_name: str,
        document_id: str,
    ) -> Path:
        metadata = (
            self.get_document_metadata(
                project_name=project_name,
                document_id=document_id,
            )
        )

        file_path = Path(
            str(
                metadata.get(
                    "document_file",
                    "",
                )
            )
        )

        if not file_path.exists():
            raise ValueError(
                "Generated document file "
                "does not exist."
            )

        return file_path

    @staticmethod
    def _read_metadata(
        metadata_file: Path,
    ) -> dict[str, Any]:
        try:
            data = json.loads(
                metadata_file.read_text(
                    encoding="utf-8"
                )
            )

        except (
            OSError,
            json.JSONDecodeError,
        ) as error:
            raise RuntimeError(
                "Failed to read document metadata."
            ) from error

        if not isinstance(data, dict):
            raise RuntimeError(
                "Document metadata is invalid."
            )

        return data

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