import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4
import base64
import binascii

from app.core.config import (
    DOCUMENTS_PATH,
)


class DocumentStorage:
    """
    Stores generated HTML documentation files,
    document metadata, and optional runtime
    context assets such as uploaded screenshots.
    """

    ALLOWED_SCREENSHOT_EXTENSIONS = {
        ".png",
        ".jpg",
        ".jpeg",
        ".webp",
    }

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
        comparison_summary: dict[str, Any] | None = None,
        runtime_context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Save one generated HTML document and its
        metadata.

        runtime_context is optional and is used for
        extra project information that is not visible
        from code alone, such as Docker, Temporal,
        Cortex, ServiceNow, screenshots, dashboards,
        or deployment notes.
        """

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

        document_id = self.create_document_id(
            created_at=created_at,
        )

        project_directory = (
            self.get_project_directory(
                project_name=project_name,
            )
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

        normalized_runtime_context = (
            self._normalize_runtime_context(
                runtime_context=runtime_context,
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
            "runtime_context": (
                normalized_runtime_context
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

    def prepare_runtime_assets(
        self,
        project_name: str,
        files: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """
        Save uploaded screenshot files under the
        project document assets directory.

        Expected file item format:

        {
            "filename": "docker.png",
            "content_type": "image/png",
            "file_path": Path("temporary_upload.png")
        }

        This method is intentionally framework-neutral.
        FastAPI routes can first save UploadFile objects
        to temporary files, then pass those paths here.
        """

        project_directory = (
            self.get_project_directory(
                project_name=project_name,
            )
        )

        asset_batch_id = self.create_asset_batch_id()

        asset_directory = (
            project_directory
            / "assets"
            / asset_batch_id
        )

        asset_directory.mkdir(
            parents=True,
            exist_ok=True,
        )

        screenshots: list[dict[str, Any]] = []

        for index, file_item in enumerate(
            files or [],
            start=1,
        ):
            if not isinstance(file_item, dict):
                continue

            original_filename = str(
                file_item.get(
                    "filename",
                    "",
                )
            ).strip()

            content_type = str(
                file_item.get(
                    "content_type",
                    "",
                )
            ).strip()

            raw_file_path = file_item.get(
                "file_path"
            )

            if not original_filename:
                continue

            if raw_file_path is None:
                continue

            source_file_path = Path(
                raw_file_path
            )

            if not source_file_path.exists():
                continue

            extension = (
                source_file_path.suffix.lower()
                or Path(original_filename).suffix.lower()
            )

            if (
                extension
                not in self.ALLOWED_SCREENSHOT_EXTENSIONS
            ):
                continue

            screenshot_filename = (
                f"screenshot_{index:03d}"
                f"{extension}"
            )

            saved_file = (
                asset_directory
                / screenshot_filename
            )

            try:
                shutil.copyfile(
                    source_file_path,
                    saved_file,
                )

            except OSError as error:
                raise RuntimeError(
                    "Failed to save uploaded "
                    "screenshot asset."
                ) from error

            relative_path = (
                saved_file.relative_to(
                    project_directory
                )
            )

            screenshots.append(
                {
                    "screenshot_id": (
                        f"screenshot_{index:03d}"
                    ),
                    "original_filename": (
                        original_filename
                    ),
                    "filename": screenshot_filename,
                    "content_type": (
                        content_type or None
                    ),
                    "asset_file": str(saved_file),
                    "relative_path": (
                        relative_path.as_posix()
                    ),
                    "html_src": (
                        relative_path.as_posix()
                    ),
                    "description": None,
                }
            )

        return {
            "asset_batch_id": asset_batch_id,
            "asset_directory": str(
                asset_directory
            ),
            "screenshots": screenshots,
        }

    def get_project_directory(
        self,
        project_name: str,
    ) -> Path:
        """
        Return and create the storage directory for
        one project.
        """

        if not project_name.strip():
            raise ValueError(
                "Project name is required."
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

        return project_directory

    def create_document_id(
        self,
        created_at: datetime | None = None,
    ) -> str:
        """
        Create a stable document ID format used by
        saved HTML and JSON metadata files.
        """

        if created_at is None:
            created_at = datetime.now(
                timezone.utc
            )

        return (
            created_at.strftime(
                "%Y%m%d_%H%M%S"
            )
            + "_"
            + uuid4().hex[:8]
        )

    def create_asset_batch_id(
        self,
    ) -> str:
        """
        Create a unique ID for one screenshot upload
        batch.
        """

        created_at = datetime.now(
            timezone.utc
        )

        return (
            "assets_"
            + created_at.strftime(
                "%Y%m%d_%H%M%S"
            )
            + "_"
            + uuid4().hex[:8]
        )

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

    def recover_missing_runtime_assets_from_html(
            self,
            project_name: str,
            document_metadata: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Recover missing screenshot asset files from the
        standalone generated HTML document.

        Why this exists:
        - Shared HTML files can contain screenshots as
          base64 data:image/... values.
        - A new developer may not have the original
          workspace/assets folder.
        - Before reusing old runtime_context for LLM
          analysis, we recreate missing image files from
          the embedded base64 images.

        This method returns updated document metadata.
        It also writes the repaired metadata back to disk
        when metadata_file exists.
        """

        if not isinstance(document_metadata, dict):
            return document_metadata

        runtime_context = document_metadata.get(
            "runtime_context"
        )

        if not isinstance(runtime_context, dict):
            return document_metadata

        screenshots = runtime_context.get(
            "screenshots",
            [],
        )

        if not isinstance(screenshots, list):
            return document_metadata

        has_missing_assets = any(
            self._screenshot_asset_is_missing(
                screenshot=screenshot,
            )
            for screenshot in screenshots
            if isinstance(screenshot, dict)
        )

        if not has_missing_assets:
            return document_metadata

        html_file = Path(
            str(
                document_metadata.get(
                    "document_file",
                    "",
                )
                or ""
            )
        )

        if not html_file.exists():
            return document_metadata

        embedded_images = (
            self._extract_base64_screenshots_from_html(
                html_file=html_file,
            )
        )

        if not embedded_images:
            return document_metadata

        project_directory = (
            self.get_project_directory(
                project_name=project_name,
            )
        )

        recovery_batch_id = (
            self.create_recovered_asset_batch_id()
        )

        recovery_directory = (
            project_directory
            / "assets"
            / recovery_batch_id
        )

        updated_screenshots: list[
            dict[str, Any]
        ] = []

        recovered_by_key: dict[
            str,
            dict[str, Any]
        ] = {}

        changed = False

        for index, screenshot in enumerate(
                screenshots,
                start=1,
        ):
            if not isinstance(screenshot, dict):
                continue

            updated_screenshot = dict(
                screenshot
            )

            if self._screenshot_asset_is_missing(
                    screenshot=updated_screenshot,
            ):
                embedded_image_index = index - 1

                if embedded_image_index < len(
                        embedded_images
                ):
                    recovered_info = (
                        self._save_recovered_screenshot(
                            project_directory=(
                                project_directory
                            ),
                            recovery_directory=(
                                recovery_directory
                            ),
                            data_uri=embedded_images[
                                embedded_image_index
                            ],
                            index=index,
                            original_filename=str(
                                updated_screenshot.get(
                                    "original_filename",
                                    "",
                                )
                                or updated_screenshot.get(
                                    "filename",
                                    "",
                                )
                                or f"screenshot_{index:03d}"
                            ),
                        )
                    )

                    if recovered_info:
                        old_key = self._screenshot_match_key(
                            screenshot=updated_screenshot,
                        )

                        updated_screenshot.update(
                            recovered_info
                        )

                        new_key = self._screenshot_match_key(
                            screenshot=updated_screenshot,
                        )

                        if old_key:
                            recovered_by_key[old_key] = (
                                updated_screenshot
                            )

                        if new_key:
                            recovered_by_key[new_key] = (
                                updated_screenshot
                            )

                        changed = True

            updated_screenshots.append(
                updated_screenshot
            )

        if not changed:
            return document_metadata

        updated_runtime_context = dict(
            runtime_context
        )

        updated_runtime_context[
            "screenshots"
        ] = updated_screenshots

        updated_runtime_context[
            "asset_batch_id"
        ] = recovery_batch_id

        updated_runtime_context[
            "asset_directory"
        ] = str(
            recovery_directory
        )

        updated_runtime_context[
            "context_blocks"
        ] = self._repair_context_block_screenshots(
            context_blocks=runtime_context.get(
                "context_blocks",
                [],
            ),
            recovered_screenshots=(
                updated_screenshots
            ),
            recovered_by_key=recovered_by_key,
        )

        updated_document_metadata = dict(
            document_metadata
        )

        updated_document_metadata[
            "runtime_context"
        ] = updated_runtime_context

        self._write_repaired_metadata_if_possible(
            document_metadata=updated_document_metadata,
        )

        return updated_document_metadata

    def create_recovered_asset_batch_id(
            self,
    ) -> str:
        """
        Create a unique ID for recovered screenshot assets.
        """

        created_at = datetime.now(
            timezone.utc
        )

        return (
            "recovered_"
            + created_at.strftime(
                "%Y%m%d_%H%M%S"
            )
            + "_"
            + uuid4().hex[:8]
        )

    @staticmethod
    def _screenshot_asset_is_missing(
            screenshot: dict[str, Any],
    ) -> bool:
        """
        Return True when a screenshot has no usable
        asset_file on disk.
        """

        if not isinstance(screenshot, dict):
            return False

        asset_file = str(
            screenshot.get(
                "asset_file",
                "",
            )
            or ""
        ).strip()

        if not asset_file:
            return True

        return not Path(
            asset_file
        ).exists()

    @staticmethod
    def _extract_base64_screenshots_from_html(
            html_file: Path,
    ) -> list[str]:
        """
        Extract embedded screenshot data URIs from the
        Supporting screenshots section.

        Prefer screenshot-card images so we do not
        accidentally extract unrelated embedded icons.
        """

        try:
            html_content = html_file.read_text(
                encoding="utf-8"
            )

        except OSError:
            return []

        screenshot_card_pattern = re.compile(
            r'<article\s+class="screenshot-card"'
            r'[\s\S]*?'
            r'<img[^>]+src=["\']'
            r'(data:image/[^"\']+)'
            r'["\']',
            flags=re.IGNORECASE,
        )

        matches = screenshot_card_pattern.findall(
            html_content
        )

        if matches:
            return [
                match.strip()
                for match in matches
                if match.strip()
            ]

        fallback_pattern = re.compile(
            r'src=["\']'
            r'(data:image/[^"\']+)'
            r'["\']',
            flags=re.IGNORECASE,
        )

        return [
            match.strip()
            for match in fallback_pattern.findall(
                html_content
            )
            if match.strip()
        ]

    def _save_recovered_screenshot(
            self,
            project_directory: Path,
            recovery_directory: Path,
            data_uri: str,
            index: int,
            original_filename: str,
    ) -> dict[str, Any] | None:
        """
        Decode one base64 data URI and save it as a
        recovered screenshot file.
        """

        parsed_image = self._parse_image_data_uri(
            data_uri=data_uri,
        )

        if parsed_image is None:
            return None

        content_type = parsed_image[
            "content_type"
        ]

        image_bytes = parsed_image[
            "image_bytes"
        ]

        extension = self._extension_from_content_type(
            content_type=content_type,
        )

        recovery_directory.mkdir(
            parents=True,
            exist_ok=True,
        )

        screenshot_filename = (
            f"recovered_screenshot_{index:03d}"
            f"{extension}"
        )

        recovered_file = (
            recovery_directory
            / screenshot_filename
        )

        try:
            recovered_file.write_bytes(
                image_bytes
            )

        except OSError as error:
            raise RuntimeError(
                "Failed to save recovered "
                "screenshot asset."
            ) from error

        relative_path = recovered_file.relative_to(
            project_directory
        )

        return {
            "screenshot_id": (
                f"screenshot_{index:03d}"
            ),
            "original_filename": (
                original_filename
            ),
            "filename": screenshot_filename,
            "content_type": content_type,
            "asset_file": str(
                recovered_file
            ),
            "relative_path": (
                relative_path.as_posix()
            ),
            "html_src": (
                relative_path.as_posix()
            ),
            "description": None,
            "recovered_from_html": True,
        }

    @staticmethod
    def _parse_image_data_uri(
            data_uri: str,
    ) -> dict[str, Any] | None:
        """
        Parse a data:image/...;base64,... URI.
        """

        cleaned_data_uri = data_uri.strip()

        match = re.match(
            r"^data:(image/[a-zA-Z0-9.+-]+);"
            r"base64,(.+)$",
            cleaned_data_uri,
            flags=re.DOTALL,
        )

        if not match:
            return None

        content_type = match.group(1).strip()
        encoded_data = match.group(2).strip()

        encoded_data = re.sub(
            r"\s+",
            "",
            encoded_data,
        )

        try:
            image_bytes = base64.b64decode(
                encoded_data,
                validate=True,
            )

        except (
            binascii.Error,
            ValueError,
        ):
            return None

        if not image_bytes:
            return None

        if not content_type.startswith(
                "image/"
        ):
            return None

        return {
            "content_type": content_type,
            "image_bytes": image_bytes,
        }

    @staticmethod
    def _extension_from_content_type(
            content_type: str,
    ) -> str:
        """
        Return a safe image extension for a MIME type.
        """

        normalized_content_type = (
            content_type.strip().lower()
        )

        if normalized_content_type in {
            "image/jpeg",
            "image/jpg",
        }:
            return ".jpg"

        if normalized_content_type == "image/webp":
            return ".webp"

        return ".png"

    def _repair_context_block_screenshots(
            self,
            context_blocks: Any,
            recovered_screenshots: list[dict[str, Any]],
            recovered_by_key: dict[str, dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """
        Update screenshots stored inside context blocks so
        they point to recovered asset files too.
        """

        if not isinstance(context_blocks, list):
            return []

        repaired_blocks: list[
            dict[str, Any]
        ] = []

        for block in context_blocks:
            if not isinstance(block, dict):
                continue

            repaired_block = dict(
                block
            )

            screenshot = repaired_block.get(
                "screenshot"
            )

            if isinstance(screenshot, dict):
                screenshot_key = (
                    self._screenshot_match_key(
                        screenshot=screenshot,
                    )
                )

                replacement = None

                if screenshot_key:
                    replacement = recovered_by_key.get(
                        screenshot_key
                    )

                if replacement is None:
                    replacement = (
                        self._find_matching_screenshot(
                            screenshot=screenshot,
                            screenshots=(
                                recovered_screenshots
                            ),
                        )
                    )

                if replacement is not None:
                    repaired_block[
                        "screenshot"
                    ] = replacement

            repaired_blocks.append(
                repaired_block
            )

        return repaired_blocks

    @staticmethod
    def _find_matching_screenshot(
            screenshot: dict[str, Any],
            screenshots: list[dict[str, Any]],
    ) -> dict[str, Any] | None:
        """
        Find a recovered screenshot matching the block
        screenshot reference.
        """

        screenshot_id = str(
            screenshot.get(
                "screenshot_id",
                "",
            )
            or ""
        ).strip()

        filename = str(
            screenshot.get(
                "filename",
                "",
            )
            or ""
        ).strip()

        original_filename = str(
            screenshot.get(
                "original_filename",
                "",
            )
            or ""
        ).strip()

        for candidate in screenshots:
            if not isinstance(candidate, dict):
                continue

            if screenshot_id and screenshot_id == str(
                candidate.get(
                    "screenshot_id",
                    "",
                )
                or ""
            ).strip():
                return candidate

            if filename and filename == str(
                candidate.get(
                    "filename",
                    "",
                )
                or ""
            ).strip():
                return candidate

            if original_filename and original_filename == str(
                candidate.get(
                    "original_filename",
                    "",
                )
                or ""
            ).strip():
                return candidate

        return None

    @staticmethod
    def _screenshot_match_key(
            screenshot: dict[str, Any],
    ) -> str:
        """
        Create a matching key for screenshot metadata.
        """

        if not isinstance(screenshot, dict):
            return ""

        return "|".join(
            [
                str(
                    screenshot.get(
                        "screenshot_id",
                        "",
                    )
                    or ""
                ).strip(),
                str(
                    screenshot.get(
                        "filename",
                        "",
                    )
                    or ""
                ).strip(),
                str(
                    screenshot.get(
                        "original_filename",
                        "",
                    )
                    or ""
                ).strip(),
            ]
        ).lower()

    @staticmethod
    def _write_repaired_metadata_if_possible(
            document_metadata: dict[str, Any],
    ) -> None:
        """
        Persist repaired metadata when metadata_file is
        available.
        """

        metadata_file = Path(
            str(
                document_metadata.get(
                    "metadata_file",
                    "",
                )
                or ""
            )
        )

        if not metadata_file.exists():
            return

        metadata_temp_file = metadata_file.with_suffix(
            ".json.tmp"
        )

        try:
            metadata_temp_file.write_text(
                json.dumps(
                    document_metadata,
                    indent=2,
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            metadata_temp_file.replace(
                metadata_file
            )

        except OSError as error:
            metadata_temp_file.unlink(
                missing_ok=True
            )

            raise RuntimeError(
                "Failed to write repaired "
                "document metadata."
            ) from error



    @staticmethod
    def _normalize_runtime_context(
            runtime_context: dict[str, Any] | None,
    ) -> dict[str, Any]:
        """
        Normalize optional runtime/tooling context
        before writing it into document metadata.

        Supports:

        1. Raw user context:
           additional_context
           context_blocks
           screenshots

        2. LLM-analyzed runtime understanding:
           runtime_understanding
        """

        if not isinstance(runtime_context, dict):
            return {
                "additional_context": None,
                "context_blocks": [],
                "screenshots": [],
                "runtime_understanding": None,
                "asset_batch_id": None,
                "asset_directory": None,
            }

        additional_context = runtime_context.get(
            "additional_context"
        )

        if additional_context is not None:
            additional_context = str(
                additional_context
            ).strip() or None

        screenshots = runtime_context.get(
            "screenshots",
            [],
        )

        if not isinstance(screenshots, list):
            screenshots = []

        valid_screenshots: list[
            dict[str, Any]
        ] = []

        for item in screenshots:
            if isinstance(item, dict):
                valid_screenshots.append(
                    item
                )

        context_blocks = runtime_context.get(
            "context_blocks",
            [],
        )

        if not isinstance(context_blocks, list):
            context_blocks = []

        valid_context_blocks: list[
            dict[str, Any]
        ] = []

        for index, block in enumerate(
                context_blocks,
                start=1,
        ):
            if not isinstance(block, dict):
                continue

            title = str(
                block.get(
                    "title",
                    f"Runtime context {index}",
                )
                or f"Runtime context {index}"
            ).strip()

            text = str(
                block.get(
                    "text",
                    "",
                )
                or ""
            ).strip()

            screenshot = block.get(
                "screenshot"
            )

            if not isinstance(screenshot, dict):
                screenshot = None

            if not title and not text and screenshot is None:
                continue

            valid_context_blocks.append(
                {
                    "title": title,
                    "text": text,
                    "screenshot": screenshot,
                }
            )

        runtime_understanding = runtime_context.get(
            "runtime_understanding"
        )

        if not isinstance(
                runtime_understanding,
                dict,
        ):
            runtime_understanding = None

        return {
            "additional_context": (
                additional_context
            ),
            "context_blocks": (
                valid_context_blocks
            ),
            "screenshots": (
                valid_screenshots
            ),
            "runtime_understanding": (
                runtime_understanding
            ),
            "asset_batch_id": (
                runtime_context.get(
                    "asset_batch_id"
                )
            ),
            "asset_directory": (
                runtime_context.get(
                    "asset_directory"
                )
            ),
        }


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