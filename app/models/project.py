from typing import Any, Literal

from pydantic import (
    BaseModel,
    Field,
)

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
        description=(
            "Scan ID of the older project state"
        ),
    )

    new_scan_id: str = Field(
        ...,
        min_length=1,
        description=(
            "Scan ID of the newer project state"
        ),
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


class ProjectContextRequest(BaseModel):
    scan_id: str = Field(
        ...,
        min_length=1,
        description=(
            "Saved scan ID used to build "
            "project context"
        ),
    )

    mode: Literal[
        "detailed",
        "llm",
    ] = Field(
        default="llm",
        description=(
            "detailed keeps complete context; "
            "llm creates a reduced context for "
            "language-model processing"
        ),
    )


class ProjectContextResponse(BaseModel):
    context_mode: str
    project: dict[str, Any]
    statistics: dict[str, Any]
    important_files: dict[str, list[str]]
    modules: list[dict[str, Any]]
    api_routes: list[dict[str, Any]]
    internal_dependencies: list[
        dict[str, Any]
    ]

class ProjectUnderstandingRequest(
    BaseModel
):
    scan_id: str = Field(
        ...,
        min_length=1,
        description=(
            "Saved project scan used for "
            "LLM analysis"
        ),
    )



class UnderstandingStorageInfo(
    BaseModel
):
    understanding_id: str
    created_at: str
    understanding_file: str


class UnderstandingSummaryResponse(
    BaseModel
):
    understanding_id: str
    created_at: str
    project_name: str
    scan_id: str
    provider: str
    model: str


class StoredUnderstandingResponse(
    BaseModel
):
    understanding_id: str
    created_at: str
    project_name: str
    scan_id: str
    provider: str
    model: str
    understanding: dict[str, Any]

class ProjectUnderstandingResponse(
    BaseModel
):
    project_name: str
    scan_id: str
    provider: str
    model: str
    understanding: dict[str, Any]
    storage: UnderstandingStorageInfo

class DocumentGenerationRequest(
    BaseModel
):
    understanding_id: str = Field(
        ...,
        min_length=1,
        description=(
            "Saved understanding used to "
            "generate HTML documentation"
        ),
    )


class DocumentStorageInfo(
    BaseModel
):
    document_id: str
    created_at: str
    project_name: str
    scan_id: str
    understanding_id: str
    document_type: str

    update_type: str = "initial"

    previous_document_id: (
        str | None
    ) = None

    comparison_summary: (
        dict[str, Any] | None
    ) = None

    document_file: str
    metadata_file: str


class DocumentGenerationResponse(
    BaseModel
):
    message: str
    document: DocumentStorageInfo


class DocumentSummaryResponse(
    BaseModel
):
    document_id: str
    created_at: str
    project_name: str
    scan_id: str
    understanding_id: str
    document_type: str

    update_type: str = "initial"

    previous_document_id: (
        str | None
    ) = None

    comparison_summary: (
        dict[str, Any] | None
    ) = None

    document_file: str
    metadata_file: str

class DocumentUpdateRequest(
    BaseModel
):
    document_id: str = Field(
        ...,
        min_length=1,
        description=(
            "Existing generated document that "
            "will be checked for updates"
        ),
    )

    new_scan_id: str = Field(
        ...,
        min_length=1,
        description=(
            "New saved scan used to update "
            "the documentation"
        ),
    )


class DocumentUpdateResponse(
    BaseModel
):
    updated: bool
    message: str
    project_name: str
    previous_document_id: str
    document_id: str
    old_scan_id: str
    new_scan_id: str
    comparison_summary: dict[str, Any]
    understanding_id: str | None = None
    document: (
        DocumentStorageInfo | None
    ) = None

class DocumentationSyncRequest(
    BaseModel
):
    project_path: str = Field(
        ...,
        min_length=1,
        description=(
            "Absolute path of the project whose "
            "documentation should be created "
            "or updated"
        ),
        examples=[
            "C:\\Users\\PratimMangaldasDasud\\"
            "PycharmProjects\\AutoDocX"
        ],
    )


class DocumentationSyncResponse(
    BaseModel
):
    action: Literal[
        "created",
        "updated",
        "unchanged",
    ]

    message: str
    project_name: str

    scan_id: str

    previous_document_id: (
        str | None
    ) = None

    document_id: str

    understanding_id: (
        str | None
    ) = None

    has_changes: bool

    comparison_summary: dict[
        str,
        Any
    ] = Field(
        default_factory=dict
    )

    document: DocumentStorageInfo

