from typing import Any

from fastapi import (
    APIRouter,
    HTTPException,
    status,
)
from fastapi.responses import FileResponse

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


# ============================================================
# Helper functions
# ============================================================


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


# ============================================================
# Scan endpoints
# ============================================================


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
    try:
        previous_document = (
            document_storage
            .get_document_metadata(
                project_name=project_name,
                document_id=request.document_id,
            )
        )

        old_scan_id = str(
            previous_document.get(
                "scan_id",
                "",
            )
        ).strip()

        if not old_scan_id:
            raise ValueError(
                "The existing document does not "
                "contain an original scan ID."
            )

        previous_understanding_id = str(
            previous_document.get(
                "understanding_id",
                "",
            )
        )

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
                ),
                document=None,
            )

        old_stored_scan = scan_storage.get_scan(
            project_name=project_name,
            scan_id=old_scan_id,
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
                ),
                document=None,
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
                stored_scan=new_stored_scan,
                provider_name=provider_name,
                api_key=api_key,
                model=model_name,
            )
        )

        understanding_storage_info = (
            understanding_storage
            .save_understanding(
                understanding_result=(
                    understanding_result
                ),
            )
        )

        new_understanding_id = str(
            understanding_storage_info.get(
                "understanding_id",
                "",
            )
        ).strip()

        if not new_understanding_id:
            raise RuntimeError(
                "The generated understanding "
                "was saved without an ID."
            )

        stored_understanding = (
            understanding_storage
            .get_understanding(
                project_name=project_name,
                understanding_id=(
                    new_understanding_id
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

        new_document = (
            document_storage.save_document(
                project_name=project_name,
                understanding_id=(
                    new_understanding_id
                ),
                scan_id=request.new_scan_id,
                html_content=html_content,
                previous_document_id=(
                    request.document_id
                ),
                update_type="version_update",
                comparison_summary=(
                    comparison_summary
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
            detail="Document update failed.",
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