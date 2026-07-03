from fastapi import (
    APIRouter,
    HTTPException,
    status,
)

from app.models.project import (
    ProjectScanRequest,
    ProjectScanResponse,
    ScanComparisonRequest,
    ScanComparisonResponse,
    ScanSummaryResponse,
    StoredScanResponse,
)
from app.services.project_scanner import (
    ProjectScanner,
)
from app.services.scan_comparator import (
    ScanComparator,
)
from app.services.scan_storage import (
    ScanStorage,
)


router = APIRouter(
    prefix="/api/projects",
    tags=["Projects"],
)

project_scanner = ProjectScanner()
scan_storage = ScanStorage()
scan_comparator = ScanComparator()


@router.post(
    "/scan",
    response_model=ProjectScanResponse,
    status_code=status.HTTP_200_OK,
    summary="Scan, analyze, and save a local project",
)
def scan_project(
    request: ProjectScanRequest,
) -> ProjectScanResponse:
    try:
        scan_result = (
            project_scanner.scan_project(
                project_path=request.project_path
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
            **response_data
        )

    except ValueError as error:
        raise HTTPException(
            status_code=(
                status.HTTP_400_BAD_REQUEST
            ),
            detail=str(error),
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
                "Project scan failed: "
                f"{error}"
            ),
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
            **comparison_result
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
                "Scan comparison failed: "
                f"{error}"
            ),
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
                status
                .HTTP_500_INTERNAL_SERVER_ERROR
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
        stored_scan = scan_storage.get_latest_scan(
            project_name=project_name,
        )

        return StoredScanResponse(
            **stored_scan
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
            **stored_scan
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