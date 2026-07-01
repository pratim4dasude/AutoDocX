from typing import Any

from pydantic import BaseModel, Field


class ProjectScanRequest(BaseModel):
    project_path: str = Field(
        ...,
        min_length=1,
        description="Absolute path of the local project",
        examples=[
            "C:\\Users\\PratimMangaldasDasud\\PycharmProjects\\AutoDocX"
        ],
    )


class ProjectScanResponse(BaseModel):
    project_name: str
    project_path: str
    total_files: int
    total_directories: int
    total_size_bytes: int
    ignored_items: int
    file_types: dict[str, int]
    files: list[str]
    parsed_files: list[dict[str, Any]]