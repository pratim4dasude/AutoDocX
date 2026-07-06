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

        understanding = (
            self._generate_understanding_with_retry(
                provider=provider,
                user_prompt=user_prompt,
            )
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

    def _generate_understanding_with_retry(
        self,
        provider: Any,
        user_prompt: str,
    ) -> dict[str, Any]:
        """
        Generate project understanding from the LLM.

        The first attempt uses the normal prompt.
        If the LLM returns malformed JSON or misses
        required fields, retry once with stricter
        JSON-only instructions.
        """

        try:
            understanding = provider.generate_json(
                system_prompt=(
                    PROJECT_UNDERSTANDING_SYSTEM_PROMPT
                ),
                user_prompt=user_prompt,
            )

            self._validate_understanding(
                understanding=understanding,
            )

            return understanding

        except Exception as first_error:
            print(
                "[AutoDocX] First LLM understanding "
                "generation attempt failed: "
                f"{first_error}"
            )

            retry_system_prompt = (
                PROJECT_UNDERSTANDING_SYSTEM_PROMPT
                + "\n\n"
                "IMPORTANT JSON OUTPUT RULES:\n"
                "Return ONLY one valid JSON object.\n"
                "Do not include markdown.\n"
                "Do not wrap the response in ```json.\n"
                "Do not include text before the JSON.\n"
                "Do not include text after the JSON.\n"
                "The response must start with { and end with }.\n"
                "All required top-level fields must be present.\n"
            )

            retry_user_prompt = (
                user_prompt
                + "\n\n"
                "Your previous response could not be "
                "parsed or validated by the backend.\n"
                "Generate the project understanding again.\n"
                "Return ONLY valid JSON with these exact "
                "top-level keys:\n"
                "1. project_summary\n"
                "2. architecture_overview\n"
                "3. execution_flow\n"
                "4. module_responsibilities\n"
                "5. api_overview\n"
                "6. key_dependencies\n"
                "7. risks_and_gaps\n"
                "8. recommended_document_sections\n\n"
                "Field type requirements:\n"
                "- project_summary must be a non-empty string\n"
                "- architecture_overview must be a non-empty string\n"
                "- execution_flow must be a list\n"
                "- module_responsibilities must be a list\n"
                "- api_overview must be a list\n"
                "- key_dependencies must be a list\n"
                "- risks_and_gaps must be a list\n"
                "- recommended_document_sections must be a list\n"
            )

            try:
                understanding = provider.generate_json(
                    system_prompt=retry_system_prompt,
                    user_prompt=retry_user_prompt,
                )

                self._validate_understanding(
                    understanding=understanding,
                )

                return understanding

            except Exception as retry_error:
                print(
                    "[AutoDocX] Second LLM understanding "
                    "generation attempt failed: "
                    f"{retry_error}"
                )

                raise RuntimeError(
                    "The LLM returned malformed or incomplete "
                    "JSON after retry. Please try again. If this "
                    "keeps happening, reduce the project context "
                    "size or improve the LLM JSON parser."
                ) from retry_error

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