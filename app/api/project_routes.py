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
    DocumentGenerationRequest,
    DocumentGenerationResponse,
    DocumentSummaryResponse,
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

from app.services.document_builder import (
    DocumentBuilder,
)
from app.services.document_storage import (
    DocumentStorage,
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

        if "Scan not found" in error_message:
            response_status = (
                status.HTTP_404_NOT_FOUND
            )
        else:
            response_status = (
                status.HTTP_400_BAD_REQUEST
            )

        raise HTTPException(
            status_code=response_status,
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

        if "Scan not found" in error_message:
            response_status = (
                status.HTTP_404_NOT_FOUND
            )
        else:
            response_status = (
                status.HTTP_400_BAD_REQUEST
            )

        raise HTTPException(
            status_code=response_status,
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

@router.post(
    "/{project_name}/understand",
    response_model=(
        ProjectUnderstandingResponse
    ),
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

        if "Scan not found" in error_message:
            response_status = (
                status.HTTP_404_NOT_FOUND
            )
        else:
            response_status = (
                status.HTTP_400_BAD_REQUEST
            )

        raise HTTPException(
            status_code=response_status,
            detail=error_message,
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
                status
                .HTTP_500_INTERNAL_SERVER_ERROR
            ),
            detail=(
                "Project understanding "
                "generation failed."
            ),
        ) from error


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
                status
                .HTTP_500_INTERNAL_SERVER_ERROR
            ),
            detail=str(error),
        ) from error

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

        document_info = (
            document_storage.save_document(
                project_name=project_name,
                understanding_id=(
                    request.understanding_id
                ),
                scan_id=str(
                    stored_understanding.get(
                        "scan_id",
                        "",
                    )
                ),
                html_content=html_content,
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

        if (
            "Understanding not found"
            in error_message
            or "Document not found"
            in error_message
        ):
            response_status = (
                status.HTTP_404_NOT_FOUND
            )
        else:
            response_status = (
                status.HTTP_400_BAD_REQUEST
            )

        raise HTTPException(
            status_code=response_status,
            detail=error_message,
        ) from error

    except RuntimeError as error:
        raise HTTPException(
            status_code=(
                status
                .HTTP_500_INTERNAL_SERVER_ERROR
            ),
            detail=str(error),
        ) from error

    except Exception as error:
        raise HTTPException(
            status_code=(
                status
                .HTTP_500_INTERNAL_SERVER_ERROR
            ),
            detail=(
                "HTML documentation generation "
                "failed."
            ),
        ) from error

@router.get(
    "/{project_name}/understandings/latest",
    response_model=(
        StoredUnderstandingResponse
    ),
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
            status_code=(
                status.HTTP_404_NOT_FOUND
            ),
            detail=str(error),
        ) from error

    except RuntimeError as error:
        raise HTTPException(
            status_code=(
                status
                .HTTP_500_INTERNAL_SERVER_ERROR
            ),
            detail=str(error),
        ) from error


@router.get(
    (
        "/{project_name}/understandings/"
        "{understanding_id}"
    ),
    response_model=(
        StoredUnderstandingResponse
    ),
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
            status_code=(
                status.HTTP_404_NOT_FOUND
            ),
            detail=str(error),
        ) from error

    except RuntimeError as error:
        raise HTTPException(
            status_code=(
                status
                .HTTP_500_INTERNAL_SERVER_ERROR
            ),
            detail=str(error),
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
                status
                .HTTP_500_INTERNAL_SERVER_ERROR
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
            status_code=(
                status.HTTP_404_NOT_FOUND
            ),
            detail=str(error),
        ) from error

    except RuntimeError as error:
        raise HTTPException(
            status_code=(
                status
                .HTTP_500_INTERNAL_SERVER_ERROR
            ),
            detail=str(error),
        ) from error