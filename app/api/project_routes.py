from typing import Any
import json
from fastapi import (
    APIRouter,
    File,
    Form,
    HTTPException,
    UploadFile,
    status,
)

from fastapi.responses import FileResponse
import tempfile
from pathlib import Path
from app.core.config import (
    get_llm_api_key,
    get_llm_model,
    get_llm_provider,
)
from app.models.project import (
    DocumentGenerationRequest,
    DocumentGenerationResponse,
    DocumentSummaryResponse,
    DocumentUpdateRequest,
    DocumentUpdateResponse,
    ProjectContextRequest,
    ProjectContextResponse,
    ProjectScanRequest,
    ProjectScanResponse,
    ProjectUnderstandingRequest,
    ProjectUnderstandingResponse,
    ScanComparisonRequest,
    ScanComparisonResponse,
    ScanSummaryResponse,
    StoredScanResponse,
    StoredUnderstandingResponse,
    UnderstandingSummaryResponse,
    DocumentationSyncRequest,
    DocumentationSyncResponse,
)
from app.services.document_builder import (
    DocumentBuilder,
)
from app.services.document_storage import (
    DocumentStorage,
)
from app.services.project_context_builder import (
    ProjectContextBuilder,
)
from app.services.project_scanner import (
    ProjectScanner,
)
from app.services.project_understanding_service import (
    ProjectUnderstandingService,
)
from app.services.scan_comparator import (
    ScanComparator,
)
from app.services.scan_storage import (
    ScanStorage,
)
from app.services.understanding_storage import (
    UnderstandingStorage,
)
from app.services.runtime_context_analyzer import (
    RuntimeContextAnalyzer,
)

router = APIRouter(
    prefix="/api/projects",
    tags=["Projects"],
)


project_scanner = ProjectScanner()
scan_storage = ScanStorage()
scan_comparator = ScanComparator()
project_context_builder = ProjectContextBuilder()

project_understanding_service = (
    ProjectUnderstandingService()
)

understanding_storage = (
    UnderstandingStorage()
)

document_builder = DocumentBuilder()
document_storage = DocumentStorage()
runtime_context_analyzer = RuntimeContextAnalyzer()


# ============================================================
# Helper functions
# ============================================================

def _parse_context_blocks_json(
    context_blocks_json: str,
) -> list[dict[str, Any]]:
    """
    Parse ordered runtime context blocks sent by
    the Streamlit UI.

    Rule:
    - If title, text, and screenshot_index are all empty,
      ignore the block.
    - If any one exists, keep the block.
    """

    cleaned_json = (
        context_blocks_json
        or ""
    ).strip()

    if not cleaned_json:
        return []

    try:
        parsed_data = json.loads(
            cleaned_json
        )

    except json.JSONDecodeError as error:
        raise ValueError(
            "context_blocks_json must be valid JSON."
        ) from error

    if not isinstance(parsed_data, list):
        raise ValueError(
            "context_blocks_json must be a JSON list."
        )

    context_blocks: list[dict[str, Any]] = []

    for item in parsed_data:
        if not isinstance(item, dict):
            continue

        title = str(
            item.get(
                "title",
                "",
            )
            or ""
        ).strip()

        text = str(
            item.get(
                "text",
                "",
            )
            or ""
        ).strip()

        screenshot_index = item.get(
            "screenshot_index"
        )

        if screenshot_index is not None:
            try:
                screenshot_index = int(
                    screenshot_index
                )

            except (
                TypeError,
                ValueError,
            ):
                screenshot_index = None

        has_title = bool(title)
        has_text = bool(text)
        has_screenshot = (
            screenshot_index is not None
        )

        if not (
            has_title
            or has_text
            or has_screenshot
        ):
            continue

        context_blocks.append(
            {
                "title": title,
                "text": text,
                "screenshot_index": (
                    screenshot_index
                ),
            }
        )

    return context_blocks


def _build_runtime_context_from_blocks(
    additional_context: str,
    context_blocks_json: str,
    runtime_assets: dict[str, Any],
) -> dict[str, Any]:
    """
    Build the final runtime context object used
    by DocumentBuilder and DocumentStorage.

    This connects each context block to the correct
    uploaded/pasted screenshot using screenshot_index.
    """

    screenshots = runtime_assets.get(
        "screenshots",
        [],
    )

    if not isinstance(screenshots, list):
        screenshots = []

    parsed_blocks = (
        _parse_context_blocks_json(
            context_blocks_json=(
                context_blocks_json
            ),
        )
    )

    context_blocks: list[
        dict[str, Any]
    ] = []

    for index, block in enumerate(
        parsed_blocks,
        start=1,
    ):
        title = str(
            block.get(
                "title",
                "",
            )
            or ""
        ).strip()

        text = str(
            block.get(
                "text",
                "",
            )
            or ""
        ).strip()

        screenshot_index = block.get(
            "screenshot_index"
        )

        screenshot = None

        if isinstance(
            screenshot_index,
            int,
        ):
            if (
                screenshot_index >= 0
                and screenshot_index < len(screenshots)
            ):
                screenshot = screenshots[
                    screenshot_index
                ]

        if (
            not title
            and not text
            and screenshot is None
        ):
            continue

        context_blocks.append(
            {
                "title": (
                        title
                        or f"Runtime context {index}"
                ),
                "text": text,
                "screenshot": screenshot,
            }
        )

    return {
        "additional_context": (
            additional_context.strip()
            or None
        ),
        "context_blocks": context_blocks,
        "asset_batch_id": (
            runtime_assets.get(
                "asset_batch_id"
            )
        ),
        "asset_directory": (
            runtime_assets.get(
                "asset_directory"
            )
        ),
        "screenshots": screenshots,
    }

def _has_runtime_context(
    runtime_context: dict[str, Any] | None,
) -> bool:
    """
    Check whether runtime context contains user/runtime
    information worth carrying into documentation.
    """

    if not isinstance(runtime_context, dict):
        return False

    return bool(
        runtime_context.get("additional_context")
        or runtime_context.get("context_blocks")
        or runtime_context.get("screenshots")
    )


def _get_runtime_context_from_document(
    document_metadata: dict[str, Any] | None,
) -> dict[str, Any]:
    """
    Read runtime_context from a previous document metadata object.
    """

    if not isinstance(document_metadata, dict):
        return {
            "additional_context": None,
            "context_blocks": [],
            "screenshots": [],
            "asset_batch_id": None,
            "asset_directory": None,
        }

    runtime_context = document_metadata.get(
        "runtime_context"
    )

    if not isinstance(runtime_context, dict):
        return {
            "additional_context": None,
            "context_blocks": [],
            "screenshots": [],
            "asset_batch_id": None,
            "asset_directory": None,
        }

    return runtime_context


def _recover_runtime_assets_for_document(
    project_name: str,
    document_metadata: dict[str, Any],
) -> dict[str, Any]:
    """
    Repair missing screenshot asset files using
    embedded base64 images from the previous HTML
    document before runtime context is reused.
    """

    return (
        document_storage
        .recover_missing_runtime_assets_from_html(
            project_name=project_name,
            document_metadata=document_metadata,
        )
    )


def _merge_runtime_contexts(
    previous_runtime_context: dict[str, Any] | None,
    new_runtime_context: dict[str, Any] | None,
) -> dict[str, Any]:
    """
    Merge old runtime context with the newly submitted
    runtime context.

    This allows every new document version to carry
    forward old screenshots/text and add new ones.
    """

    previous_context = (
        previous_runtime_context
        if isinstance(previous_runtime_context, dict)
        else {}
    )

    current_context = (
        new_runtime_context
        if isinstance(new_runtime_context, dict)
        else {}
    )

    merged_additional_context = (
        _merge_additional_context(
            previous_value=previous_context.get(
                "additional_context"
            ),
            new_value=current_context.get(
                "additional_context"
            ),
        )
    )

    merged_screenshots = (
        _merge_screenshot_lists(
            previous_screenshots=previous_context.get(
                "screenshots",
                [],
            ),
            new_screenshots=current_context.get(
                "screenshots",
                [],
            ),
        )
    )

    merged_context_blocks = (
        _merge_context_blocks(
            previous_blocks=previous_context.get(
                "context_blocks",
                [],
            ),
            new_blocks=current_context.get(
                "context_blocks",
                [],
            ),
        )
    )

    return {
        "additional_context": merged_additional_context,
        "context_blocks": merged_context_blocks,
        "screenshots": merged_screenshots,
        "runtime_understanding": None,
        "asset_batch_id": (
            current_context.get("asset_batch_id")
            or previous_context.get("asset_batch_id")
        ),
        "asset_directory": (
            current_context.get("asset_directory")
            or previous_context.get("asset_directory")
        ),
    }


def _merge_additional_context(
    previous_value: Any,
    new_value: Any,
) -> str | None:
    previous_text = str(
        previous_value or ""
    ).strip()

    new_text = str(
        new_value or ""
    ).strip()

    if not previous_text and not new_text:
        return None

    if previous_text and not new_text:
        return previous_text

    if new_text and not previous_text:
        return new_text

    if previous_text == new_text:
        return previous_text

    if new_text in previous_text:
        return previous_text

    if previous_text in new_text:
        return new_text

    return (
        previous_text
        + "\n\n"
        + new_text
    )


def _merge_context_blocks(
    previous_blocks: Any,
    new_blocks: Any,
) -> list[dict[str, Any]]:
    merged_blocks: list[dict[str, Any]] = []
    seen_signatures: set[str] = set()

    for block in _safe_dict_list(previous_blocks):
        signature = _context_block_signature(
            block
        )

        if signature in seen_signatures:
            continue

        seen_signatures.add(signature)
        merged_blocks.append(block)

    for block in _safe_dict_list(new_blocks):
        signature = _context_block_signature(
            block
        )

        if signature in seen_signatures:
            continue

        seen_signatures.add(signature)
        merged_blocks.append(block)

    return merged_blocks


def _merge_screenshot_lists(
    previous_screenshots: Any,
    new_screenshots: Any,
) -> list[dict[str, Any]]:
    merged_screenshots: list[dict[str, Any]] = []
    seen_signatures: set[str] = set()

    for screenshot in _safe_dict_list(
        previous_screenshots
    ):
        signature = _screenshot_signature(
            screenshot
        )

        if signature in seen_signatures:
            continue

        seen_signatures.add(signature)
        merged_screenshots.append(screenshot)

    for screenshot in _safe_dict_list(
        new_screenshots
    ):
        signature = _screenshot_signature(
            screenshot
        )

        if signature in seen_signatures:
            continue

        seen_signatures.add(signature)
        merged_screenshots.append(screenshot)

    return merged_screenshots


def _safe_dict_list(
    value: Any,
) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []

    return [
        item
        for item in value
        if isinstance(item, dict)
    ]


def _context_block_signature(
    block: dict[str, Any],
) -> str:
    title = str(
        block.get("title", "")
        or ""
    ).strip().lower()

    text = str(
        block.get("text", "")
        or ""
    ).strip().lower()

    screenshot = block.get(
        "screenshot"
    )

    screenshot_key = ""

    if isinstance(screenshot, dict):
        screenshot_key = _screenshot_signature(
            screenshot
        )

    return (
        title
        + "|"
        + text
        + "|"
        + screenshot_key
    )


def _screenshot_signature(
    screenshot: dict[str, Any],
) -> str:
    """
    Build a stable signature for deduping screenshots.

    asset_file/html_src is more reliable than screenshot_id
    because each upload batch can reuse screenshot_001.
    """

    return "|".join(
        [
            str(
                screenshot.get("asset_file", "")
                or ""
            ).strip(),
            str(
                screenshot.get("html_src", "")
                or screenshot.get("relative_path", "")
                or ""
            ).strip(),
            str(
                screenshot.get("original_filename", "")
                or screenshot.get("filename", "")
                or ""
            ).strip(),
        ]
    ).lower()


def _analyze_runtime_context_with_llm(
    stored_scan: dict[str, Any],
    runtime_context: dict[str, Any],
) -> dict[str, Any] | None:
    """
    Analyze runtime/tooling context using the configured
    vision-capable LLM.

    This uses project scan context, user-written notes,
    and screenshots together.
    """

    has_runtime_context = bool(
        runtime_context.get(
            "additional_context"
        )
        or runtime_context.get(
            "context_blocks"
        )
        or runtime_context.get(
            "screenshots"
        )
    )

    if not has_runtime_context:
        return None

    provider_name = get_llm_provider()

    api_key = get_llm_api_key(
        provider_name=provider_name,
    )

    model_name = get_llm_model(
        provider_name=provider_name,
    )

    return runtime_context_analyzer.analyze(
        stored_scan=stored_scan,
        runtime_context=runtime_context,
        provider_name=provider_name,
        api_key=api_key,
        model=model_name,
    )


def _contains_non_empty_change(
    value: object,
) -> bool:
    """
    Recursively check whether a comparison section
    contains a meaningful change.
    """

    if isinstance(value, bool):
        return value

    if isinstance(value, int):
        return value > 0

    if isinstance(value, str):
        return bool(value.strip())

    if isinstance(value, list):
        return any(
            _contains_non_empty_change(item)
            for item in value
        )

    if isinstance(value, dict):
        return any(
            _contains_non_empty_change(
                nested_value
            )
            for nested_value
            in value.values()
        )

    return False


def comparison_contains_changes(
    comparison_result: dict[str, Any],
) -> bool:
    """
    Determine whether a scan comparison contains
    documentation-relevant changes.
    """

    change_sections = [
        comparison_result.get(
            "file_changes",
            {},
        ),
        comparison_result.get(
            "symbol_changes",
            {},
        ),
        comparison_result.get(
            "route_changes",
            {},
        ),
        comparison_result.get(
            "dependency_changes",
            {},
        ),
    ]

    return any(
        _contains_non_empty_change(section)
        for section in change_sections
    )


def _value_error_status(
    error_message: str,
) -> int:
    """
    Convert common storage lookup errors into
    HTTP 404 responses.
    """

    not_found_messages = (
        "Scan not found",
        "Understanding not found",
        "Document not found",
        "No saved understandings found",
        "No generated documents found",
        "Generated document file does not exist",
    )

    if any(
        message in error_message
        for message in not_found_messages
    ):
        return status.HTTP_404_NOT_FOUND

    return status.HTTP_400_BAD_REQUEST

def _generate_and_save_understanding(
    stored_scan: dict[str, Any],
) -> tuple[
    str,
    dict[str, Any],
]:
    """
    Generate an LLM understanding for a stored scan,
    save it, and return its ID and stored payload.
    """

    provider_name = get_llm_provider()

    api_key = get_llm_api_key(
        provider_name=provider_name,
    )

    model_name = get_llm_model(
        provider_name=provider_name,
    )

    understanding_result = (
        project_understanding_service
        .generate_understanding(
            stored_scan=stored_scan,
            provider_name=provider_name,
            api_key=api_key,
            model=model_name,
        )
    )

    storage_info = (
        understanding_storage
        .save_understanding(
            understanding_result=(
                understanding_result
            ),
        )
    )

    understanding_id = str(
        storage_info.get(
            "understanding_id",
            "",
        )
    ).strip()

    if not understanding_id:
        raise RuntimeError(
            "The generated understanding was "
            "saved without an understanding ID."
        )

    project_name = str(
        understanding_result.get(
            "project_name",
            "",
        )
    ).strip()

    if not project_name:
        raise RuntimeError(
            "The generated understanding does "
            "not contain a project name."
        )

    stored_understanding = (
        understanding_storage
        .get_understanding(
            project_name=project_name,
            understanding_id=(
                understanding_id
            ),
        )
    )

    return (
        understanding_id,
        stored_understanding,
    )


def _generate_and_save_document(
    project_name: str,
    scan_id: str,
    understanding_id: str,
    stored_understanding: dict[str, Any],
    update_type: str,
    previous_document_id: (
        str | None
    ) = None,
    comparison_summary: (
        dict[str, Any] | None
    ) = None,
    runtime_context: (
        dict[str, Any] | None
    ) = None,
) -> dict[str, Any]:
    """
    Build HTML from a stored understanding and
    save the generated document.
    """

    html_content = (
        document_builder.build_html(
            stored_understanding=(
                stored_understanding
            ),
            runtime_context=runtime_context,
        )
    )

    return document_storage.save_document(
        project_name=project_name,
        understanding_id=understanding_id,
        scan_id=scan_id,
        html_content=html_content,
        previous_document_id=(
            previous_document_id
        ),
        update_type=update_type,
        comparison_summary=(
            comparison_summary
        ),
        runtime_context=runtime_context,
    )

def _save_uploaded_screenshots_to_temp(
    screenshots: list[UploadFile] | None,
) -> list[dict[str, Any]]:
    """
    Save FastAPI UploadFile screenshots to temporary
    files so DocumentStorage can copy them into the
    project asset directory.
    """

    saved_files: list[dict[str, Any]] = []
    for screenshot in screenshots or []:
        original_filename = (
            screenshot.filename or ""
        ).strip()

        if not original_filename:
            continue

        suffix = Path(
            original_filename
        ).suffix.lower()

        if suffix not in {
            ".png",
            ".jpg",
            ".jpeg",
            ".webp",
        }:
            continue

        try:
            with tempfile.NamedTemporaryFile(
                delete=False,
                suffix=suffix,
            ) as temp_file:
                temp_path = Path(
                    temp_file.name
                )

                while True:
                    chunk = screenshot.file.read(
                        1024 * 1024
                    )

                    if not chunk:
                        break

                    temp_file.write(chunk)

            saved_files.append(
                {
                    "filename": original_filename,
                    "content_type": (
                        screenshot.content_type
                    ),
                    "file_path": temp_path,
                }
            )

        finally:
            screenshot.file.close()

    return saved_files


def _cleanup_temp_files(
    temp_files: list[dict[str, Any]],
) -> None:
    """
    Remove temporary upload files after they have
    been copied into document storage.
    """

    for file_item in temp_files:
        file_path = file_item.get(
            "file_path"
        )

        if file_path is None:
            continue

        try:
            Path(file_path).unlink(
                missing_ok=True
            )

        except OSError:
            pass

# ============================================================
# Complete documentation synchronization endpoint
# ============================================================


@router.post(
    "/documentation/sync",
    response_model=DocumentationSyncResponse,
    status_code=status.HTTP_200_OK,
    summary=(
        "Create or update project documentation "
        "using one request"
    ),
)
def sync_project_documentation(
    request: DocumentationSyncRequest,
) -> DocumentationSyncResponse:
    """
    Complete documentation workflow.

    The endpoint:

    1. Scans and saves the project.
    2. Finds the latest document.
    3. Creates initial documentation when no
       document exists.
    4. Compares scans when a document exists.
    5. Creates a new version when changes exist.
    6. Returns the existing document when there
       are no changes.
    """

    try:
        # ----------------------------------------------------
        # Step 1: Scan the project
        # ----------------------------------------------------

        scan_result = (
            project_scanner.scan_project(
                project_path=request.project_path,
            )
        )

        scan_storage_info = (
            scan_storage.save_scan(
                scan_result=scan_result,
            )
        )

        project_name = str(
            scan_result.get(
                "project_name",
                "",
            )
        ).strip()

        new_scan_id = str(
            scan_storage_info.get(
                "scan_id",
                "",
            )
        ).strip()

        if not project_name:
            raise RuntimeError(
                "The project scan did not return "
                "a project name."
            )

        if not new_scan_id:
            raise RuntimeError(
                "The project scan was saved "
                "without a scan ID."
            )

        new_stored_scan = (
            scan_storage.get_scan(
                project_name=project_name,
                scan_id=new_scan_id,
            )
        )

        # ----------------------------------------------------
        # Step 2: Find existing documentation
        # ----------------------------------------------------

        existing_documents = (
            document_storage.list_documents(
                project_name=project_name,
            )
        )

        # ----------------------------------------------------
        # Step 3: No previous document - create initial doc
        # ----------------------------------------------------

        if not existing_documents:
            (
                understanding_id,
                stored_understanding,
            ) = _generate_and_save_understanding(
                stored_scan=new_stored_scan,
            )

            new_document = (
                _generate_and_save_document(
                    project_name=project_name,
                    scan_id=new_scan_id,
                    understanding_id=(
                        understanding_id
                    ),
                    stored_understanding=(
                        stored_understanding
                    ),
                    update_type="initial",
                )
            )

            document_id = str(
                new_document.get(
                    "document_id",
                    "",
                )
            )

            return DocumentationSyncResponse(
                action="created",
                message=(
                    "Initial project documentation "
                    "was created successfully."
                ),
                project_name=project_name,
                scan_id=new_scan_id,
                previous_document_id=None,
                document_id=document_id,
                understanding_id=(
                    understanding_id
                ),
                has_changes=True,
                comparison_summary={},
                document=new_document,
            )

        # ----------------------------------------------------
        # Step 4: Read latest document information
        # ----------------------------------------------------

        latest_document = (
            existing_documents[0]
        )

        latest_document = (
            _recover_runtime_assets_for_document(
                project_name=project_name,
                document_metadata=latest_document,
            )
        )

        previous_runtime_context = (
            _get_runtime_context_from_document(
                document_metadata=latest_document,
            )
        )

        has_previous_runtime_context = (
            _has_runtime_context(
                runtime_context=previous_runtime_context,
            )
        )

        previous_document_id = str(
            latest_document.get(
                "document_id",
                "",
            )
        ).strip()

        old_scan_id = str(
            latest_document.get(
                "scan_id",
                "",
            )
        ).strip()

        previous_understanding_id = str(
            latest_document.get(
                "understanding_id",
                "",
            )
        ).strip()

        if not previous_document_id:
            raise RuntimeError(
                "The latest document does not "
                "contain a document ID."
            )

        if not old_scan_id:
            raise RuntimeError(
                "The latest document does not "
                "contain its original scan ID."
            )

        old_stored_scan = (
            scan_storage.get_scan(
                project_name=project_name,
                scan_id=old_scan_id,
            )
        )

        # ----------------------------------------------------
        # Step 5: Compare old and new scans
        # ----------------------------------------------------

        comparison_result = (
            scan_comparator.compare_scans(
                old_stored_scan=old_stored_scan,
                new_stored_scan=new_stored_scan,
            )
        )

        comparison_summary = (
            comparison_result.get(
                "summary",
                {},
            )
        )

        has_changes = bool(
            comparison_summary.get(
                "has_changes",
                comparison_contains_changes(
                    comparison_result
                ),
            )
        )

        # ----------------------------------------------------
        # Step 6: No changes - return latest document
        # ----------------------------------------------------

        if not has_changes:
            return DocumentationSyncResponse(
                action="unchanged",
                message=(
                    "No project changes were "
                    "detected. The existing "
                    "documentation is current."
                ),
                project_name=project_name,
                scan_id=new_scan_id,
                previous_document_id=(
                    previous_document_id
                ),
                document_id=(
                    previous_document_id
                ),
                understanding_id=(
                    previous_understanding_id
                    or None
                ),
                has_changes=False,
                comparison_summary=(
                    comparison_summary
                ),
                document=latest_document,
            )

        # ----------------------------------------------------
        # Step 7: Changes found - create new version
        # ----------------------------------------------------

        (
            new_understanding_id,
            stored_understanding,
        ) = _generate_and_save_understanding(
            stored_scan=new_stored_scan,
        )

        runtime_context_for_new_document = None

        if has_previous_runtime_context:
            previous_runtime_context[
                "runtime_understanding"
            ] = _analyze_runtime_context_with_llm(
                stored_scan=new_stored_scan,
                runtime_context=previous_runtime_context,
            )

            runtime_context_for_new_document = (
                previous_runtime_context
            )

        new_document = (
            _generate_and_save_document(
                project_name=project_name,
                scan_id=new_scan_id,
                understanding_id=(
                    new_understanding_id
                ),
                stored_understanding=(
                    stored_understanding
                ),
                update_type="version_update",
                previous_document_id=(
                    previous_document_id
                ),
                comparison_summary=(
                    comparison_summary
                ),
                runtime_context=(
                    runtime_context_for_new_document
                ),
            )
        )

        new_document_id = str(
            new_document.get(
                "document_id",
                "",
            )
        )

        return DocumentationSyncResponse(
            action="updated",
            message=(
                "Project changes were detected "
                "and a new documentation version "
                "was created successfully."
            ),
            project_name=project_name,
            scan_id=new_scan_id,
            previous_document_id=(
                previous_document_id
            ),
            document_id=new_document_id,
            understanding_id=(
                new_understanding_id
            ),
            has_changes=True,
            comparison_summary=(
                comparison_summary
            ),
            document=new_document,
        )

    except ValueError as error:
        error_message = str(error)

        raise HTTPException(
            status_code=_value_error_status(
                error_message
            ),
            detail=error_message,
        ) from error

    except PermissionError as error:
        raise HTTPException(
            status_code=(
                status.HTTP_403_FORBIDDEN
            ),
            detail=f"Permission denied: {error}",
        ) from error

    except RuntimeError as error:
        raise HTTPException(
            status_code=(
                status.HTTP_502_BAD_GATEWAY
            ),
            detail=str(error),
        ) from error

    except Exception as error:
        raise HTTPException(
            status_code=(
                status.HTTP_500_INTERNAL_SERVER_ERROR
            ),
            detail=(
                "Documentation synchronization "
                f"failed: {error}"
            ),
        ) from error
# ============================================================
# Scan endpoints
# ============================================================

@router.post(
    "/documentation/sync-with-context",
    response_model=DocumentationSyncResponse,
    status_code=status.HTTP_200_OK,
    summary=(
        "Create or update project documentation "
        "with extra runtime context and screenshots"
    ),
)
def sync_project_documentation_with_context(
    project_path: str = Form(
        ...,
        min_length=1,
        description=(
            "Absolute path of the project whose "
            "documentation should be created "
            "or updated"
        ),
    ),
    additional_context: str = Form(
        default="",
        description=(
                "Optional general project context that is "
                "not visible from source code."
        ),
    ),
    context_blocks_json: str = Form(
        default="[]",
        description=(
                "JSON list of ordered runtime context blocks. "
                "Each block can contain title, text, and "
                "screenshot_index."
        ),
    ),
    screenshots: list[UploadFile] | None = File(
        default=None,
        description=(
            "Optional screenshots from Docker, Temporal, "
            "Swagger, Cortex, ServiceNow, dashboards, logs, "
            "or other project tooling."
        ),
    ),
) -> DocumentationSyncResponse:
    """
    Complete documentation workflow with external
    runtime/tooling context.

    This endpoint keeps the original code documentation
    pipeline but also accepts human-written context and
    screenshots. The extra context is added to the final
    HTML documentation under Runtime and Tooling Context.
    """

    temp_files: list[dict[str, Any]] = []

    try:
        # ----------------------------------------------------
        # Step 1: Scan the project
        # ----------------------------------------------------

        scan_result = (
            project_scanner.scan_project(
                project_path=project_path,
            )
        )

        scan_storage_info = (
            scan_storage.save_scan(
                scan_result=scan_result,
            )
        )

        project_name = str(
            scan_result.get(
                "project_name",
                "",
            )
        ).strip()

        new_scan_id = str(
            scan_storage_info.get(
                "scan_id",
                "",
            )
        ).strip()

        if not project_name:
            raise RuntimeError(
                "The project scan did not return "
                "a project name."
            )

        if not new_scan_id:
            raise RuntimeError(
                "The project scan was saved "
                "without a scan ID."
            )

        new_stored_scan = (
            scan_storage.get_scan(
                project_name=project_name,
                scan_id=new_scan_id,
            )
        )

        # ----------------------------------------------------
        # Step 2: Save uploaded screenshots
        # ----------------------------------------------------

        temp_files = (
            _save_uploaded_screenshots_to_temp(
                screenshots=screenshots,
            )
        )

        runtime_assets = (
            document_storage.prepare_runtime_assets(
                project_name=project_name,
                files=temp_files,
            )
        )

        runtime_context = (
            _build_runtime_context_from_blocks(
                additional_context=(
                    additional_context
                ),
                context_blocks_json=(
                    context_blocks_json
                ),
                runtime_assets=runtime_assets,
            )
        )

        has_new_runtime_context = (
            _has_runtime_context(
                runtime_context=runtime_context,
            )
        )



        # ----------------------------------------------------
        # Step 3: Find existing documentation
        # ----------------------------------------------------

        existing_documents = (
            document_storage.list_documents(
                project_name=project_name,
            )
        )

        # ----------------------------------------------------
        # Step 4: No previous document - create initial doc
        # ----------------------------------------------------

        if not existing_documents:
            (
                understanding_id,
                stored_understanding,
            ) = _generate_and_save_understanding(
                stored_scan=new_stored_scan,
            )

            if has_new_runtime_context:
                runtime_context[
                    "runtime_understanding"
                ] = _analyze_runtime_context_with_llm(
                    stored_scan=new_stored_scan,
                    runtime_context=runtime_context,
                )

            new_document = (
                _generate_and_save_document(
                    project_name=project_name,
                    scan_id=new_scan_id,
                    understanding_id=(
                        understanding_id
                    ),
                    stored_understanding=(
                        stored_understanding
                    ),
                    update_type="initial",
                    runtime_context=runtime_context,
                )
            )

            document_id = str(
                new_document.get(
                    "document_id",
                    "",
                )
            )

            return DocumentationSyncResponse(
                action="created",
                message=(
                    "Initial project documentation "
                    "was created successfully with "
                    "runtime context."
                ),
                project_name=project_name,
                scan_id=new_scan_id,
                previous_document_id=None,
                document_id=document_id,
                understanding_id=(
                    understanding_id
                ),
                has_changes=True,
                comparison_summary={},
                document=new_document,
            )

        # ----------------------------------------------------
        # Step 5: Read latest document information
        # ----------------------------------------------------

        latest_document = (
            existing_documents[0]
        )

        latest_document = (
            _recover_runtime_assets_for_document(
                project_name=project_name,
                document_metadata=latest_document,
            )
        )

        previous_runtime_context = (
            _get_runtime_context_from_document(
                document_metadata=latest_document,
            )
        )

        merged_runtime_context = (
            _merge_runtime_contexts(
                previous_runtime_context=(
                    previous_runtime_context
                ),
                new_runtime_context=runtime_context,
            )
        )

        has_merged_runtime_context = (
            _has_runtime_context(
                runtime_context=merged_runtime_context,
            )
        )

        previous_document_id = str(
            latest_document.get(
                "document_id",
                "",
            )
        ).strip()

        old_scan_id = str(
            latest_document.get(
                "scan_id",
                "",
            )
        ).strip()

        previous_understanding_id = str(
            latest_document.get(
                "understanding_id",
                "",
            )
        ).strip()

        if not previous_document_id:
            raise RuntimeError(
                "The latest document does not "
                "contain a document ID."
            )

        if not old_scan_id:
            raise RuntimeError(
                "The latest document does not "
                "contain its original scan ID."
            )

        old_stored_scan = (
            scan_storage.get_scan(
                project_name=project_name,
                scan_id=old_scan_id,
            )
        )

        # ----------------------------------------------------
        # Step 6: Compare old and new scans
        # ----------------------------------------------------

        comparison_result = (
            scan_comparator.compare_scans(
                old_stored_scan=old_stored_scan,
                new_stored_scan=new_stored_scan,
            )
        )

        comparison_summary = (
            comparison_result.get(
                "summary",
                {},
            )
        )

        has_code_changes = bool(
            comparison_summary.get(
                "has_changes",
                comparison_contains_changes(
                    comparison_result
                ),
            )
        )

        should_create_new_version = (
                has_code_changes
                or has_new_runtime_context
        )

        # ----------------------------------------------------
        # Step 7: No changes and no context - return latest
        # ----------------------------------------------------

        if not should_create_new_version:
            return DocumentationSyncResponse(
                action="unchanged",
                message=(
                    "No project changes or runtime "
                    "context updates were detected. "
                    "The existing documentation is current."
                ),
                project_name=project_name,
                scan_id=new_scan_id,
                previous_document_id=(
                    previous_document_id
                ),
                document_id=(
                    previous_document_id
                ),
                understanding_id=(
                    previous_understanding_id
                    or None
                ),
                has_changes=False,
                comparison_summary=(
                    comparison_summary
                ),
                document=latest_document,
            )

        # ----------------------------------------------------
        # Step 8: Create new documentation version
        # ----------------------------------------------------

        (
            new_understanding_id,
            stored_understanding,
        ) = _generate_and_save_understanding(
            stored_scan=new_stored_scan,
        )

        update_type = (
            "version_update"
        )


        if has_merged_runtime_context:
            merged_runtime_context[
                "runtime_understanding"
            ] = _analyze_runtime_context_with_llm(
                stored_scan=new_stored_scan,
                runtime_context=merged_runtime_context,
            )

        new_document = (
            _generate_and_save_document(
                project_name=project_name,
                scan_id=new_scan_id,
                understanding_id=(
                    new_understanding_id
                ),
                stored_understanding=(
                    stored_understanding
                ),
                update_type=update_type,
                previous_document_id=(
                    previous_document_id
                ),
                comparison_summary=(
                    comparison_summary
                ),
                runtime_context=merged_runtime_context,
            )
        )


        new_document_id = str(
            new_document.get(
                "document_id",
                "",
            )
        )

        return DocumentationSyncResponse(
            action="updated",
            message=(
                "A new documentation version was "
                "created with the latest code state "
                "and runtime context."
            ),
            project_name=project_name,
            scan_id=new_scan_id,
            previous_document_id=(
                previous_document_id
            ),
            document_id=new_document_id,
            understanding_id=(
                new_understanding_id
            ),
            has_changes=True,
            comparison_summary=(
                comparison_summary
            ),
            document=new_document,
        )

    except ValueError as error:
        error_message = str(error)

        raise HTTPException(
            status_code=_value_error_status(
                error_message
            ),
            detail=error_message,
        ) from error

    except PermissionError as error:
        raise HTTPException(
            status_code=(
                status.HTTP_403_FORBIDDEN
            ),
            detail=f"Permission denied: {error}",
        ) from error

    except RuntimeError as error:
        raise HTTPException(
            status_code=(
                status.HTTP_502_BAD_GATEWAY
            ),
            detail=str(error),
        ) from error

    except Exception as error:
        raise HTTPException(
            status_code=(
                status.HTTP_500_INTERNAL_SERVER_ERROR
            ),
            detail=(
                "Documentation synchronization "
                "with runtime context failed: "
                f"{error}"
            ),
        ) from error

    finally:
        _cleanup_temp_files(
            temp_files=temp_files,
        )

@router.post(
    "/scan",
    response_model=ProjectScanResponse,
    status_code=status.HTTP_200_OK,
    summary=(
        "Scan, analyze, and save a local project"
    ),
)
def scan_project(
    request: ProjectScanRequest,
) -> ProjectScanResponse:
    try:
        scan_result = (
            project_scanner.scan_project(
                project_path=request.project_path,
            )
        )

        storage_info = scan_storage.save_scan(
            scan_result=scan_result,
        )

        response_data = {
            **scan_result,
            "storage": storage_info,
        }

        return ProjectScanResponse(
            **response_data,
        )

    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(error),
        ) from error

    except PermissionError as error:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Permission denied: {error}",
        ) from error

    except RuntimeError as error:
        raise HTTPException(
            status_code=(
                status.HTTP_500_INTERNAL_SERVER_ERROR
            ),
            detail=str(error),
        ) from error

    except Exception as error:
        raise HTTPException(
            status_code=(
                status.HTTP_500_INTERNAL_SERVER_ERROR
            ),
            detail=f"Project scan failed: {error}",
        ) from error


@router.get(
    "/{project_name}/scans",
    response_model=list[ScanSummaryResponse],
    status_code=status.HTTP_200_OK,
    summary="List all saved project scans",
)
def list_project_scans(
    project_name: str,
) -> list[ScanSummaryResponse]:
    try:
        scans = scan_storage.list_scans(
            project_name=project_name,
        )

        return [
            ScanSummaryResponse(**scan)
            for scan in scans
        ]

    except RuntimeError as error:
        raise HTTPException(
            status_code=(
                status.HTTP_500_INTERNAL_SERVER_ERROR
            ),
            detail=str(error),
        ) from error


@router.get(
    "/{project_name}/scans/latest",
    response_model=StoredScanResponse,
    status_code=status.HTTP_200_OK,
    summary="Get the latest saved project scan",
)
def get_latest_project_scan(
    project_name: str,
) -> StoredScanResponse:
    try:
        stored_scan = (
            scan_storage.get_latest_scan(
                project_name=project_name,
            )
        )

        return StoredScanResponse(
            **stored_scan,
        )

    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error

    except RuntimeError as error:
        raise HTTPException(
            status_code=(
                status.HTTP_500_INTERNAL_SERVER_ERROR
            ),
            detail=str(error),
        ) from error


@router.get(
    "/{project_name}/scans/{scan_id}",
    response_model=StoredScanResponse,
    status_code=status.HTTP_200_OK,
    summary="Get one saved project scan",
)
def get_project_scan(
    project_name: str,
    scan_id: str,
) -> StoredScanResponse:
    try:
        stored_scan = scan_storage.get_scan(
            project_name=project_name,
            scan_id=scan_id,
        )

        return StoredScanResponse(
            **stored_scan,
        )

    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error

    except RuntimeError as error:
        raise HTTPException(
            status_code=(
                status.HTTP_500_INTERNAL_SERVER_ERROR
            ),
            detail=str(error),
        ) from error


# ============================================================
# Scan comparison endpoint
# ============================================================


@router.post(
    "/{project_name}/compare",
    response_model=ScanComparisonResponse,
    status_code=status.HTTP_200_OK,
    summary="Compare two saved project scans",
)
def compare_project_scans(
    project_name: str,
    request: ScanComparisonRequest,
) -> ScanComparisonResponse:
    try:
        if (
            request.old_scan_id
            == request.new_scan_id
        ):
            raise ValueError(
                "Old scan ID and new scan ID "
                "must be different."
            )

        old_stored_scan = scan_storage.get_scan(
            project_name=project_name,
            scan_id=request.old_scan_id,
        )

        new_stored_scan = scan_storage.get_scan(
            project_name=project_name,
            scan_id=request.new_scan_id,
        )

        comparison_result = (
            scan_comparator.compare_scans(
                old_stored_scan=old_stored_scan,
                new_stored_scan=new_stored_scan,
            )
        )

        return ScanComparisonResponse(
            **comparison_result,
        )

    except ValueError as error:
        error_message = str(error)

        raise HTTPException(
            status_code=_value_error_status(
                error_message
            ),
            detail=error_message,
        ) from error

    except RuntimeError as error:
        raise HTTPException(
            status_code=(
                status.HTTP_500_INTERNAL_SERVER_ERROR
            ),
            detail=str(error),
        ) from error

    except Exception as error:
        raise HTTPException(
            status_code=(
                status.HTTP_500_INTERNAL_SERVER_ERROR
            ),
            detail=f"Scan comparison failed: {error}",
        ) from error


# ============================================================
# Context endpoint
# ============================================================


@router.post(
    "/{project_name}/context",
    response_model=ProjectContextResponse,
    status_code=status.HTTP_200_OK,
    summary=(
        "Build compact LLM-ready project context"
    ),
)
def build_project_context(
    project_name: str,
    request: ProjectContextRequest,
) -> ProjectContextResponse:
    try:
        stored_scan = scan_storage.get_scan(
            project_name=project_name,
            scan_id=request.scan_id,
        )

        project_context = (
            project_context_builder.build_context(
                stored_scan=stored_scan,
                mode=request.mode,
            )
        )

        return ProjectContextResponse(
            **project_context,
        )

    except ValueError as error:
        error_message = str(error)

        raise HTTPException(
            status_code=_value_error_status(
                error_message
            ),
            detail=error_message,
        ) from error

    except RuntimeError as error:
        raise HTTPException(
            status_code=(
                status.HTTP_500_INTERNAL_SERVER_ERROR
            ),
            detail=str(error),
        ) from error

    except Exception as error:
        raise HTTPException(
            status_code=(
                status.HTTP_500_INTERNAL_SERVER_ERROR
            ),
            detail=(
                "Project context generation failed: "
                f"{error}"
            ),
        ) from error


# ============================================================
# Understanding generation endpoint
# ============================================================


@router.post(
    "/{project_name}/understand",
    response_model=ProjectUnderstandingResponse,
    status_code=status.HTTP_200_OK,
    summary=(
        "Generate and save structured project "
        "understanding using the configured LLM"
    ),
)
def understand_project(
    project_name: str,
    request: ProjectUnderstandingRequest,
) -> ProjectUnderstandingResponse:
    try:
        stored_scan = scan_storage.get_scan(
            project_name=project_name,
            scan_id=request.scan_id,
        )

        provider_name = get_llm_provider()

        api_key = get_llm_api_key(
            provider_name=provider_name,
        )

        model_name = get_llm_model(
            provider_name=provider_name,
        )

        understanding_result = (
            project_understanding_service
            .generate_understanding(
                stored_scan=stored_scan,
                provider_name=provider_name,
                api_key=api_key,
                model=model_name,
            )
        )

        storage_info = (
            understanding_storage
            .save_understanding(
                understanding_result=(
                    understanding_result
                ),
            )
        )

        response_data = {
            **understanding_result,
            "storage": storage_info,
        }

        return ProjectUnderstandingResponse(
            **response_data,
        )

    except ValueError as error:
        error_message = str(error)

        raise HTTPException(
            status_code=_value_error_status(
                error_message
            ),
            detail=error_message,
        ) from error

    except RuntimeError as error:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(error),
        ) from error

    except Exception as error:
        raise HTTPException(
            status_code=(
                status.HTTP_500_INTERNAL_SERVER_ERROR
            ),
            detail=(
                "Project understanding "
                "generation failed."
            ),
        ) from error


# ============================================================
# Understanding retrieval endpoints
# Static /latest route must come before /{understanding_id}
# ============================================================


@router.get(
    "/{project_name}/understandings",
    response_model=list[
        UnderstandingSummaryResponse
    ],
    status_code=status.HTTP_200_OK,
    summary=(
        "List saved project understandings"
    ),
)
def list_project_understandings(
    project_name: str,
) -> list[UnderstandingSummaryResponse]:
    try:
        saved_understandings = (
            understanding_storage
            .list_understandings(
                project_name=project_name,
            )
        )

        return [
            UnderstandingSummaryResponse(
                **saved_understanding
            )
            for saved_understanding
            in saved_understandings
        ]

    except RuntimeError as error:
        raise HTTPException(
            status_code=(
                status.HTTP_500_INTERNAL_SERVER_ERROR
            ),
            detail=str(error),
        ) from error


@router.get(
    "/{project_name}/understandings/latest",
    response_model=StoredUnderstandingResponse,
    status_code=status.HTTP_200_OK,
    summary=(
        "Get the latest saved project "
        "understanding"
    ),
)
def get_latest_project_understanding(
    project_name: str,
) -> StoredUnderstandingResponse:
    try:
        stored_understanding = (
            understanding_storage
            .get_latest_understanding(
                project_name=project_name,
            )
        )

        return StoredUnderstandingResponse(
            **stored_understanding,
        )

    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error

    except RuntimeError as error:
        raise HTTPException(
            status_code=(
                status.HTTP_500_INTERNAL_SERVER_ERROR
            ),
            detail=str(error),
        ) from error


@router.get(
    (
        "/{project_name}/understandings/"
        "{understanding_id}"
    ),
    response_model=StoredUnderstandingResponse,
    status_code=status.HTTP_200_OK,
    summary=(
        "Get one saved project understanding"
    ),
)
def get_project_understanding(
    project_name: str,
    understanding_id: str,
) -> StoredUnderstandingResponse:
    try:
        stored_understanding = (
            understanding_storage
            .get_understanding(
                project_name=project_name,
                understanding_id=(
                    understanding_id
                ),
            )
        )

        return StoredUnderstandingResponse(
            **stored_understanding,
        )

    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error

    except RuntimeError as error:
        raise HTTPException(
            status_code=(
                status.HTTP_500_INTERNAL_SERVER_ERROR
            ),
            detail=str(error),
        ) from error


# ============================================================
# Document generation endpoint
# ============================================================


@router.post(
    "/{project_name}/documents",
    response_model=DocumentGenerationResponse,
    status_code=status.HTTP_201_CREATED,
    summary=(
        "Generate and save HTML project "
        "documentation"
    ),
)
def generate_project_document(
    project_name: str,
    request: DocumentGenerationRequest,
) -> DocumentGenerationResponse:
    try:
        stored_understanding = (
            understanding_storage
            .get_understanding(
                project_name=project_name,
                understanding_id=(
                    request.understanding_id
                ),
            )
        )

        html_content = (
            document_builder.build_html(
                stored_understanding=(
                    stored_understanding
                ),
            )
        )

        scan_id = str(
            stored_understanding.get(
                "scan_id",
                "",
            )
        )

        document_info = (
            document_storage.save_document(
                project_name=project_name,
                understanding_id=(
                    request.understanding_id
                ),
                scan_id=scan_id,
                html_content=html_content,
                update_type="initial",
            )
        )

        return DocumentGenerationResponse(
            message=(
                "HTML documentation generated "
                "successfully."
            ),
            document=document_info,
        )

    except ValueError as error:
        error_message = str(error)

        raise HTTPException(
            status_code=_value_error_status(
                error_message
            ),
            detail=error_message,
        ) from error

    except RuntimeError as error:
        raise HTTPException(
            status_code=(
                status.HTTP_500_INTERNAL_SERVER_ERROR
            ),
            detail=str(error),
        ) from error

    except Exception as error:
        raise HTTPException(
            status_code=(
                status.HTTP_500_INTERNAL_SERVER_ERROR
            ),
            detail=(
                "HTML documentation generation "
                "failed."
            ),
        ) from error


# ============================================================
# Incremental document update endpoint
# Static /update route must remain before dynamic document IDs
# ============================================================


@router.post(
    "/{project_name}/documents/update",
    response_model=DocumentUpdateResponse,
    status_code=status.HTTP_200_OK,
    summary=(
        "Compare a new scan and create an "
        "updated documentation version"
    ),
)
def update_project_document(
    project_name: str,
    request: DocumentUpdateRequest,
) -> DocumentUpdateResponse:
    """
    Update an existing generated document using a new
    saved scan.

    Important:
    - If the previous document contains runtime/tooling
      context, it is carried into the new document.
    - This prevents screenshots, notes, and runtime
      understanding from disappearing during manual
      document updates.
    """

    try:
        # ----------------------------------------------------
        # Step 1: Read previous document metadata
        # ----------------------------------------------------

        previous_document = (
            document_storage
            .get_document_metadata(
                project_name=project_name,
                document_id=request.document_id,
            )
        )

        previous_document = (
            _recover_runtime_assets_for_document(
                project_name=project_name,
                document_metadata=previous_document,
            )
        )

        previous_runtime_context = (
            _get_runtime_context_from_document(
                document_metadata=previous_document,
            )
        )

        has_previous_runtime_context = (
            _has_runtime_context(
                runtime_context=previous_runtime_context,
            )
        )

        old_scan_id = str(
            previous_document.get(
                "scan_id",
                "",
            )
        ).strip()

        previous_understanding_id = str(
            previous_document.get(
                "understanding_id",
                "",
            )
        ).strip()

        if not old_scan_id:
            raise ValueError(
                "The existing document does not "
                "contain an original scan ID."
            )

        # ----------------------------------------------------
        # Step 2: Same scan - no update needed
        # ----------------------------------------------------

        if old_scan_id == request.new_scan_id:
            return DocumentUpdateResponse(
                updated=False,
                message=(
                    "The document already uses "
                    "this scan. No update was "
                    "required."
                ),
                project_name=project_name,
                previous_document_id=(
                    request.document_id
                ),
                document_id=(
                    request.document_id
                ),
                old_scan_id=old_scan_id,
                new_scan_id=(
                    request.new_scan_id
                ),
                comparison_summary={},
                understanding_id=(
                    previous_understanding_id
                    or None
                ),
                document=None,
            )

        # ----------------------------------------------------
        # Step 3: Load old and new scans
        # ----------------------------------------------------

        old_stored_scan = (
            scan_storage.get_scan(
                project_name=project_name,
                scan_id=old_scan_id,
            )
        )

        new_stored_scan = (
            scan_storage.get_scan(
                project_name=project_name,
                scan_id=request.new_scan_id,
            )
        )

        # ----------------------------------------------------
        # Step 4: Compare scans
        # ----------------------------------------------------

        comparison_result = (
            scan_comparator.compare_scans(
                old_stored_scan=old_stored_scan,
                new_stored_scan=new_stored_scan,
            )
        )

        comparison_summary = (
            comparison_result.get(
                "summary",
                {},
            )
        )

        has_changes = (
            comparison_contains_changes(
                comparison_result
            )
        )

        if not has_changes:
            return DocumentUpdateResponse(
                updated=False,
                message=(
                    "The scans contain no "
                    "documentation-relevant "
                    "changes."
                ),
                project_name=project_name,
                previous_document_id=(
                    request.document_id
                ),
                document_id=(
                    request.document_id
                ),
                old_scan_id=old_scan_id,
                new_scan_id=(
                    request.new_scan_id
                ),
                comparison_summary=(
                    comparison_summary
                ),
                understanding_id=(
                    previous_understanding_id
                    or None
                ),
                document=None,
            )

        # ----------------------------------------------------
        # Step 5: Generate new project understanding
        # ----------------------------------------------------

        (
            new_understanding_id,
            stored_understanding,
        ) = _generate_and_save_understanding(
            stored_scan=new_stored_scan,
        )

        # ----------------------------------------------------
        # Step 6: Carry runtime context forward
        # ----------------------------------------------------

        runtime_context_for_new_document = None

        if has_previous_runtime_context:
            previous_runtime_context[
                "runtime_understanding"
            ] = _analyze_runtime_context_with_llm(
                stored_scan=new_stored_scan,
                runtime_context=previous_runtime_context,
            )

            runtime_context_for_new_document = (
                previous_runtime_context
            )

        # ----------------------------------------------------
        # Step 7: Build and save new document version
        # ----------------------------------------------------

        new_document = (
            _generate_and_save_document(
                project_name=project_name,
                scan_id=request.new_scan_id,
                understanding_id=(
                    new_understanding_id
                ),
                stored_understanding=(
                    stored_understanding
                ),
                update_type="version_update",
                previous_document_id=(
                    request.document_id
                ),
                comparison_summary=(
                    comparison_summary
                ),
                runtime_context=(
                    runtime_context_for_new_document
                ),
            )
        )

        new_document_id = str(
            new_document.get(
                "document_id",
                "",
            )
        )

        return DocumentUpdateResponse(
            updated=True,
            message=(
                "A new documentation version "
                "was generated successfully."
            ),
            project_name=project_name,
            previous_document_id=(
                request.document_id
            ),
            document_id=new_document_id,
            old_scan_id=old_scan_id,
            new_scan_id=request.new_scan_id,
            comparison_summary=(
                comparison_summary
            ),
            understanding_id=(
                new_understanding_id
            ),
            document=new_document,
        )

    except ValueError as error:
        error_message = str(error)

        raise HTTPException(
            status_code=_value_error_status(
                error_message
            ),
            detail=error_message,
        ) from error

    except RuntimeError as error:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(error),
        ) from error

    except Exception as error:
        raise HTTPException(
            status_code=(
                status.HTTP_500_INTERNAL_SERVER_ERROR
            ),
            detail=(
                "Document update failed: "
                f"{error}"
            ),
        ) from error


# ============================================================
# Document retrieval endpoints
# Static /latest route must remain before /{document_id}/html
# ============================================================


@router.get(
    "/{project_name}/documents",
    response_model=list[
        DocumentSummaryResponse
    ],
    status_code=status.HTTP_200_OK,
    summary="List generated project documents",
)
def list_project_documents(
    project_name: str,
) -> list[DocumentSummaryResponse]:
    try:
        documents = (
            document_storage.list_documents(
                project_name=project_name,
            )
        )

        return [
            DocumentSummaryResponse(
                **document
            )
            for document in documents
        ]

    except RuntimeError as error:
        raise HTTPException(
            status_code=(
                status.HTTP_500_INTERNAL_SERVER_ERROR
            ),
            detail=str(error),
        ) from error


@router.get(
    "/{project_name}/documents/latest",
    response_model=DocumentSummaryResponse,
    status_code=status.HTTP_200_OK,
    summary=(
        "Get the latest generated project "
        "document metadata"
    ),
)
def get_latest_project_document(
    project_name: str,
) -> DocumentSummaryResponse:
    try:
        document = (
            document_storage
            .get_latest_document_metadata(
                project_name=project_name,
            )
        )

        return DocumentSummaryResponse(
            **document,
        )

    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error

    except RuntimeError as error:
        raise HTTPException(
            status_code=(
                status.HTTP_500_INTERNAL_SERVER_ERROR
            ),
            detail=str(error),
        ) from error


@router.get(
    (
        "/{project_name}/documents/"
        "{document_id}/html"
    ),
    response_class=FileResponse,
    status_code=status.HTTP_200_OK,
    summary=(
        "Open or download generated HTML "
        "documentation"
    ),
)
def get_project_document_html(
    project_name: str,
    document_id: str,
) -> FileResponse:
    try:
        document_file = (
            document_storage
            .get_document_file(
                project_name=project_name,
                document_id=document_id,
            )
        )

        return FileResponse(
            path=document_file,
            media_type="text/html",
            filename=document_file.name,
        )

    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error

    except RuntimeError as error:
        raise HTTPException(
            status_code=(
                status.HTTP_500_INTERNAL_SERVER_ERROR
            ),
            detail=str(error),
        ) from error
