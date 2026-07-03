from typing import Any

from app.services.llm.factory import (
    LLMProviderFactory,
)
from app.services.llm.prompts import (
    PROJECT_UNDERSTANDING_SYSTEM_PROMPT,
    build_project_understanding_prompt,
)
from app.services.project_context_builder import (
    ProjectContextBuilder,
)


class ProjectUnderstandingService:
    """
    Builds LLM-ready context and asks the selected provider
    to generate structured project understanding.
    """

    REQUIRED_UNDERSTANDING_FIELDS = {
        "project_summary",
        "architecture_overview",
        "execution_flow",
        "module_responsibilities",
        "api_overview",
        "key_dependencies",
        "risks_and_gaps",
        "recommended_document_sections",
    }

    def __init__(self) -> None:
        self.context_builder = (
            ProjectContextBuilder()
        )

    def generate_understanding(
        self,
        stored_scan: dict[str, Any],
        provider_name: str,
        api_key: str,
        model: str | None = None,
    ) -> dict[str, Any]:
        normalized_provider = (
            LLMProviderFactory
            .normalize_provider_name(
                provider_name=provider_name,
            )
        )

        provider = (
            LLMProviderFactory.create_provider(
                provider_name=(
                    normalized_provider
                ),
                api_key=api_key,
                model=model,
            )
        )

        project_context = (
            self.context_builder.build_context(
                stored_scan=stored_scan,
                mode="llm",
            )
        )

        user_prompt = (
            build_project_understanding_prompt(
                project_context=project_context,
            )
        )

        understanding = provider.generate_json(
            system_prompt=(
                PROJECT_UNDERSTANDING_SYSTEM_PROMPT
            ),
            user_prompt=user_prompt,
        )

        self._validate_understanding(
            understanding=understanding,
        )

        scan_result = stored_scan.get(
            "scan_result",
            {},
        )

        return {
            "project_name": (
                scan_result.get(
                    "project_name"
                )
            ),
            "scan_id": stored_scan.get(
                "scan_id"
            ),
            "provider": provider.provider_name,
            "model": provider.model,
            "understanding": understanding,
        }

    def _validate_understanding(
        self,
        understanding: Any,
    ) -> None:
        if not isinstance(
            understanding,
            dict,
        ):
            raise RuntimeError(
                "The LLM project understanding "
                "must be a JSON object."
            )

        missing_fields = (
            self.REQUIRED_UNDERSTANDING_FIELDS
            - set(understanding.keys())
        )

        if missing_fields:
            missing_field_text = ", ".join(
                sorted(missing_fields)
            )

            raise RuntimeError(
                "The LLM response is missing "
                "required fields: "
                f"{missing_field_text}."
            )

        self._validate_string_field(
            understanding=understanding,
            field_name="project_summary",
        )

        self._validate_string_field(
            understanding=understanding,
            field_name=(
                "architecture_overview"
            ),
        )

        list_fields = [
            "execution_flow",
            "module_responsibilities",
            "api_overview",
            "key_dependencies",
            "risks_and_gaps",
            "recommended_document_sections",
        ]

        for field_name in list_fields:
            if not isinstance(
                understanding.get(
                    field_name
                ),
                list,
            ):
                raise RuntimeError(
                    "The LLM response field "
                    f"'{field_name}' must be a list."
                )

    @staticmethod
    def _validate_string_field(
        understanding: dict[str, Any],
        field_name: str,
    ) -> None:
        field_value = understanding.get(
            field_name
        )

        if (
            not isinstance(field_value, str)
            or not field_value.strip()
        ):
            raise RuntimeError(
                "The LLM response field "
                f"'{field_name}' must be "
                "a non-empty string."
            )