from fastapi import APIRouter, HTTPException, status

from app.models.project import (
    ProjectScanRequest,
    ProjectScanResponse,
)
from app.services.project_scanner import ProjectScanner


router = APIRouter(
    prefix="/api/projects",
    tags=["Projects"],
)

project_scanner = ProjectScanner()


@router.post(
    "/scan",
    response_model=ProjectScanResponse,
    status_code=status.HTTP_200_OK,
    summary="Scan a local project",
)
def scan_project(
    request: ProjectScanRequest,
) -> ProjectScanResponse:
    try:
        scan_result = project_scanner.scan_project(
            project_path=request.project_path
        )

        return ProjectScanResponse(**scan_result)

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

    except Exception as error:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Project scan failed: {error}",
        ) from error