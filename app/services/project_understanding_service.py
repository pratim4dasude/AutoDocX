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

    Important:
    The LLM is used for narrative understanding only.
    Developer reference data such as API paths, handlers,
    signatures, parameters, return types, classes, and methods
    is merged from parser/analyzer output to avoid hallucination.
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
        self.context_builder = ProjectContextBuilder()

    def generate_understanding(
        self,
        stored_scan: dict[str, Any],
        provider_name: str,
        api_key: str,
        model: str | None = None,
    ) -> dict[str, Any]:
        normalized_provider = (
            LLMProviderFactory.normalize_provider_name(
                provider_name=provider_name,
            )
        )

        provider = LLMProviderFactory.create_provider(
            provider_name=normalized_provider,
            api_key=api_key,
            model=model,
        )

        project_context = self.context_builder.build_context(
            stored_scan=stored_scan,
            mode="llm",
        )

        user_prompt = build_project_understanding_prompt(
            project_context=project_context,
        )

        understanding = self._generate_understanding_with_retry(
            provider=provider,
            user_prompt=user_prompt,
        )

        understanding = self._merge_developer_reference_data(
            understanding=understanding,
            project_context=project_context,
        )

        self._validate_understanding(
            understanding=understanding,
        )

        scan_result = stored_scan.get(
            "scan_result",
            {},
        )

        return {
            "project_name": scan_result.get("project_name"),
            "scan_id": stored_scan.get("scan_id"),
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
        If the LLM returns malformed JSON or misses required
        fields, retry once with stricter JSON-only instructions.
        """

        try:
            understanding = provider.generate_json(
                system_prompt=PROJECT_UNDERSTANDING_SYSTEM_PROMPT,
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
                "Your previous response could not be parsed "
                "or validated by the backend.\n"
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

    def _merge_developer_reference_data(
        self,
        understanding: dict[str, Any],
        project_context: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Merge reliable parser/analyzer data into LLM output.

        This makes final documentation closer to professional
        developer docs. API paths, handlers, signatures, classes,
        methods, and parameters should come from code parsing,
        not from LLM guesses.
        """

        merged_understanding = dict(understanding)

        api_reference = project_context.get(
            "api_reference",
            [],
        )

        module_references = project_context.get(
            "module_references",
            [],
        )

        internal_dependencies = project_context.get(
            "internal_dependencies",
            [],
        )

        statistics = project_context.get(
            "statistics",
            {},
        )

        if isinstance(api_reference, list):
            merged_understanding["api_overview"] = (
                self._build_api_overview_from_context(
                    api_reference=api_reference,
                )
            )

        if isinstance(module_references, list):
            merged_understanding["module_responsibilities"] = (
                self._build_module_responsibilities_from_context(
                    module_references=module_references,
                )
            )

        if isinstance(internal_dependencies, list):
            merged_understanding["key_dependencies"] = (
                self._build_key_dependencies_from_context(
                    internal_dependencies=internal_dependencies,
                )
            )

        merged_understanding["developer_reference"] = {
            "statistics": statistics,
            "api_reference": api_reference,
            "module_references": module_references,
            "internal_dependencies": internal_dependencies,
        }

        return merged_understanding

    @staticmethod
    def _build_api_overview_from_context(
        api_reference: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        api_overview: list[dict[str, Any]] = []

        for route in api_reference:
            if not isinstance(route, dict):
                continue

            method = route.get("method")
            path = route.get("path")
            handler = route.get("handler")

            if not method or not path:
                continue

            summary = (
                route.get("summary")
                or route.get("description")
                or route.get("docstring")
                or "API endpoint discovered from FastAPI route decorators."
            )

            api_overview.append(
                {
                    "method": method,
                    "path": path,
                    "handler": handler,
                    "handler_signature": route.get(
                        "handler_signature",
                    ),
                    "arguments": route.get("arguments", []),
                    "returns": route.get("returns"),
                    "response_model": route.get("response_model"),
                    "status_code": route.get("status_code"),
                    "purpose": summary,
                    "summary": route.get("summary"),
                    "description": route.get("description"),
                    "tags": route.get("tags", []),
                    "file": route.get("file"),
                    "module": route.get("module"),
                    "line": route.get("line"),
                    "source_preview": route.get("source_preview"),
                }
            )

        return api_overview

    @staticmethod
    def _build_module_responsibilities_from_context(
        module_references: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        module_responsibilities: list[dict[str, Any]] = []

        for module in module_references:
            if not isinstance(module, dict):
                continue

            module_name = module.get("module")
            file_path = module.get("file")

            if not module_name or not file_path:
                continue

            classes = module.get("classes", [])
            functions = module.get("functions", [])
            async_functions = module.get("async_functions", [])
            routes = module.get("routes", [])
            constants = module.get("constants", [])

            important_symbols = (
                list(module.get("public_symbols", []))
                or ProjectUnderstandingService
                ._extract_important_symbols_from_module(
                    constants=constants,
                    functions=functions,
                    async_functions=async_functions,
                    classes=classes,
                )
            )

            responsibility = (
                module.get("module_docstring")
                or module.get("summary")
                or module.get("purpose_hint")
                or "Python module discovered during project scan."
            )

            module_responsibilities.append(
                {
                    "module": module_name,
                    "file": file_path,
                    "responsibility": responsibility,
                    "important_symbols": important_symbols,
                    "constants": constants,
                    "functions": functions,
                    "async_functions": async_functions,
                    "classes": classes,
                    "routes": routes,
                    "imports": module.get("imports", []),
                    "internal_dependencies": module.get(
                        "internal_dependencies",
                        [],
                    ),
                    "module_docstring": module.get(
                        "module_docstring",
                    ),
                    "summary": module.get("summary"),
                    "purpose_hint": module.get("purpose_hint"),
                }
            )

        return module_responsibilities

    @staticmethod
    def _extract_important_symbols_from_module(
        constants: Any,
        functions: Any,
        async_functions: Any,
        classes: Any,
    ) -> list[str]:
        symbols: list[str] = []

        if isinstance(constants, list):
            for constant in constants:
                if not isinstance(constant, dict):
                    continue

                name = constant.get("name")

                if isinstance(name, str) and not name.startswith("_"):
                    symbols.append(name)

        if isinstance(functions, list):
            for function in functions:
                if not isinstance(function, dict):
                    continue

                name = function.get("name")

                if isinstance(name, str) and not name.startswith("_"):
                    symbols.append(name)

        if isinstance(async_functions, list):
            for async_function in async_functions:
                if not isinstance(async_function, dict):
                    continue

                name = async_function.get("name")

                if isinstance(name, str) and not name.startswith("_"):
                    symbols.append(name)

        if isinstance(classes, list):
            for class_item in classes:
                if not isinstance(class_item, dict):
                    continue

                name = class_item.get("name")

                if isinstance(name, str) and not name.startswith("_"):
                    symbols.append(name)

        return sorted(set(symbols))

    @staticmethod
    def _build_key_dependencies_from_context(
        internal_dependencies: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        key_dependencies: list[dict[str, Any]] = []

        seen: set[tuple[str, str, str]] = set()

        for dependency in internal_dependencies:
            if not isinstance(dependency, dict):
                continue

            source_module = dependency.get("source_module")
            target_module = dependency.get("target_module")
            imported_name = dependency.get("imported_name") or ""

            if not source_module or not target_module:
                continue

            identity = (
                str(source_module),
                str(target_module),
                str(imported_name),
            )

            if identity in seen:
                continue

            seen.add(identity)

            if imported_name:
                purpose = (
                    f"`{source_module}` imports "
                    f"`{imported_name}` from `{target_module}`."
                )
            else:
                purpose = (
                    f"`{source_module}` depends on "
                    f"`{target_module}`."
                )

            key_dependencies.append(
                {
                    "source": source_module,
                    "target": target_module,
                    "imported_name": imported_name or None,
                    "alias": dependency.get("alias"),
                    "purpose": purpose,
                }
            )

        return key_dependencies

    def _validate_understanding(
        self,
        understanding: Any,
    ) -> None:
        if not isinstance(understanding, dict):
            raise RuntimeError(
                "The LLM project understanding must be a JSON object."
            )

        missing_fields = (
            self.REQUIRED_UNDERSTANDING_FIELDS
            - set(understanding.keys())
        )

        if missing_fields:
            missing_field_text = ", ".join(
                sorted(missing_fields),
            )

            raise RuntimeError(
                "The LLM response is missing required fields: "
                f"{missing_field_text}."
            )

        self._validate_string_field(
            understanding=understanding,
            field_name="project_summary",
        )

        self._validate_string_field(
            understanding=understanding,
            field_name="architecture_overview",
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
                understanding.get(field_name),
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
            field_name,
        )

        if (
            not isinstance(field_value, str)
            or not field_value.strip()
        ):
            raise RuntimeError(
                "The LLM response field "
                f"'{field_name}' must be a non-empty string."
            )


