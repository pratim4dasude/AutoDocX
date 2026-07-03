from typing import Any

from pydantic import BaseModel, Field


class ProjectScanRequest(BaseModel):
    project_path: str = Field(
        ...,
        min_length=1,
        description=(
            "Absolute path of the local project"
        ),
        examples=[
            "C:\\Users\\PratimMangaldasDasud\\"
            "PycharmProjects\\AutoDocX"
        ],
    )


class ScanStorageInfo(BaseModel):
    scan_id: str
    created_at: str
    scan_file: str


class ProjectScanResponse(BaseModel):
    project_name: str
    project_path: str
    total_files: int
    total_directories: int
    total_size_bytes: int
    ignored_items: int
    file_types: dict[str, int]
    files: list[str]
    file_hashes: dict[str, str]
    parsed_files: list[dict[str, Any]]
    project_analysis: dict[str, Any]
    storage: ScanStorageInfo


class ScanSummaryResponse(BaseModel):
    scan_id: str
    created_at: str
    project_name: str | None = None
    project_path: str | None = None
    total_files: int
    total_directories: int
    total_size_bytes: int
    parsed_python_files: int


class StoredScanResponse(BaseModel):
    scan_id: str
    created_at: str
    project_name: str
    project_path: str | None = None
    scan_result: dict[str, Any]


class ScanComparisonRequest(BaseModel):
    old_scan_id: str = Field(
        ...,
        min_length=1,
        description="Scan ID of the older project state",
    )

    new_scan_id: str = Field(
        ...,
        min_length=1,
        description="Scan ID of the newer project state",
    )


class ScanComparisonResponse(BaseModel):
    project_name: str
    old_scan: dict[str, Any]
    new_scan: dict[str, Any]
    summary: dict[str, Any]
    file_changes: dict[str, Any]
    symbol_changes: dict[str, Any]
    route_changes: dict[str, Any]
    dependency_changes: dict[str, Any]