import json
from typing import Any

from app.services.llm.factory import (
    LLMProviderFactory,
)
from app.services.project_context_builder import (
    ProjectContextBuilder,
)


RUNTIME_CONTEXT_SYSTEM_PROMPT = """
You are AutoDocX Runtime Context Analyzer.

Your job is to analyze a software project using:
1. Parsed project/code scan context.
2. User-written runtime/tooling notes.
3. Screenshots attached by the user.

You must understand what the project does outside the codebase:
- how it runs
- what tools are involved
- what commands are used
- what services are connected
- how UI/backend/API/workflows interact
- what the screenshots prove
- what a developer should understand from this evidence

You MUST return only valid JSON.
Do not use markdown.
Do not wrap the response in ```json.

Return this exact JSON structure:

{
  "runtime_summary": "string",
  "tooling_stack": [
    {
      "tool": "string",
      "purpose": "string",
      "evidence": "string"
    }
  ],
  "runtime_flow": [
    {
      "step": 1,
      "title": "string",
      "description": "string",
      "evidence": "string"
    }
  ],
  "screenshot_insights": [
    {
      "title": "string",
      "what_it_shows": "string",
      "why_it_matters": "string"
    }
  ],
  "operational_notes": [
    "string"
  ],
  "risks_or_gaps": [
    {
      "title": "string",
      "description": "string",
      "severity": "low|medium|high"
    }
  ]
}

Rules:
- Use the screenshots as evidence, not decoration.
- Use the user notes as hints, but correct and improve them.
- Use project scan context to connect runtime behavior to actual code.
- Do not invent external systems that are not supported by code, notes, or screenshots.
- If a screenshot shows terminal commands, ports, URLs, services, or errors, explain them.
- Keep the output developer-facing and practical.
"""


class RuntimeContextAnalyzer:
    """
    Uses a vision-capable LLM to analyze project code context,
    user-written runtime notes, and screenshots together.

    This turns pasted screenshots into real project understanding,
    instead of simply placing raw screenshots into the generated docs.
    """

    REQUIRED_FIELDS = {
        "runtime_summary",
        "tooling_stack",
        "runtime_flow",
        "screenshot_insights",
        "operational_notes",
        "risks_or_gaps",
    }

    def __init__(
        self,
    ) -> None:
        self.context_builder = (
            ProjectContextBuilder()
        )

    def analyze(
        self,
        stored_scan: dict[str, Any],
        runtime_context: dict[str, Any],
        provider_name: str,
        api_key: str,
        model: str | None = None,
    ) -> dict[str, Any]:
        """
        Analyze runtime/tooling context with text and
        screenshots together.
        """

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

        project_context = (
            self.context_builder.build_context(
                stored_scan=stored_scan,
                mode="llm",
            )
        )

        image_paths = (
            self._extract_image_paths(
                runtime_context=runtime_context,
            )
        )

        user_prompt = (
            self._build_runtime_prompt(
                project_context=project_context,
                runtime_context=runtime_context,
                image_paths=image_paths,
            )
        )

        runtime_understanding = (
            self._generate_with_retry(
                provider=provider,
                user_prompt=user_prompt,
                image_paths=image_paths,
            )
        )

        self._validate_runtime_understanding(
            runtime_understanding
        )

        return runtime_understanding

    def _generate_with_retry(
        self,
        provider: Any,
        user_prompt: str,
        image_paths: list[str],
    ) -> dict[str, Any]:
        """
        Generate runtime understanding. Retry once with
        stricter JSON instructions if parsing fails.
        """

        try:
            result = provider.generate_json_with_images(
                system_prompt=(
                    RUNTIME_CONTEXT_SYSTEM_PROMPT
                ),
                user_prompt=user_prompt,
                image_paths=image_paths,
            )

            self._validate_runtime_understanding(
                result
            )

            return result

        except Exception as first_error:
            print(
                "[AutoDocX] First runtime context "
                "analysis attempt failed: "
                f"{first_error}"
            )

            retry_system_prompt = (
                RUNTIME_CONTEXT_SYSTEM_PROMPT
                + "\n\n"
                "STRICT RETRY RULES:\n"
                "Return only valid JSON.\n"
                "No markdown.\n"
                "No explanations outside JSON.\n"
                "The response must start with { and end with }.\n"
            )

            retry_user_prompt = (
                user_prompt
                + "\n\n"
                "Your previous response could not be parsed "
                "or validated. Generate the runtime analysis "
                "again using the exact required JSON schema."
            )

            try:
                result = (
                    provider.generate_json_with_images(
                        system_prompt=retry_system_prompt,
                        user_prompt=retry_user_prompt,
                        image_paths=image_paths,
                    )
                )

                self._validate_runtime_understanding(
                    result
                )

                return result

            except Exception as retry_error:
                print(
                    "[AutoDocX] Second runtime context "
                    "analysis attempt failed: "
                    f"{retry_error}"
                )

                raise RuntimeError(
                    "The LLM failed to analyze runtime "
                    "context screenshots and notes as valid JSON."
                ) from retry_error

    @staticmethod
    def _extract_image_paths(
        runtime_context: dict[str, Any],
    ) -> list[str]:
        """
        Extract screenshot asset paths in the same order
        as the context blocks.
        """

        image_paths: list[str] = []

        context_blocks = runtime_context.get(
            "context_blocks",
            [],
        )

        if isinstance(context_blocks, list):
            for block in context_blocks:
                if not isinstance(block, dict):
                    continue

                screenshot = block.get(
                    "screenshot"
                )

                if not isinstance(screenshot, dict):
                    continue

                asset_file = str(
                    screenshot.get(
                        "asset_file",
                        "",
                    )
                    or ""
                ).strip()

                if asset_file:
                    image_paths.append(
                        asset_file
                    )

        if image_paths:
            return image_paths

        screenshots = runtime_context.get(
            "screenshots",
            [],
        )

        if isinstance(screenshots, list):
            for screenshot in screenshots:
                if not isinstance(screenshot, dict):
                    continue

                asset_file = str(
                    screenshot.get(
                        "asset_file",
                        "",
                    )
                    or ""
                ).strip()

                if asset_file:
                    image_paths.append(
                        asset_file
                    )

        return image_paths

    @staticmethod
    def _build_runtime_prompt(
        project_context: dict[str, Any],
        runtime_context: dict[str, Any],
        image_paths: list[str],
    ) -> str:
        """
        Build the multimodal prompt for runtime analysis.
        """

        compact_project_context = (
            RuntimeContextAnalyzer
            ._compact_project_context(
                project_context=project_context,
            )
        )

        context_blocks = runtime_context.get(
            "context_blocks",
            [],
        )

        if not isinstance(context_blocks, list):
            context_blocks = []

        screenshots = runtime_context.get(
            "screenshots",
            [],
        )

        if not isinstance(screenshots, list):
            screenshots = []

        additional_context = str(
            runtime_context.get(
                "additional_context",
                "",
            )
            or ""
        ).strip()

        runtime_payload = {
            "additional_context": additional_context,
            "context_blocks": (
                RuntimeContextAnalyzer
                ._compact_context_blocks(
                    context_blocks=context_blocks,
                )
            ),
            "screenshots": (
                RuntimeContextAnalyzer
                ._compact_screenshots(
                    screenshots=screenshots,
                )
            ),
            "image_count": len(image_paths),
        }

        return (
            "Analyze the following project runtime context.\n\n"
            "The attached images are screenshots provided by "
            "the user. They are attached in the same order as "
            "the screenshots/context blocks shown in the JSON "
            "payload below.\n\n"
            "PROJECT CODE CONTEXT:\n"
            f"{json.dumps(compact_project_context, indent=2, ensure_ascii=False)}"
            "\n\n"
            "USER RUNTIME CONTEXT AND SCREENSHOT METADATA:\n"
            f"{json.dumps(runtime_payload, indent=2, ensure_ascii=False)}"
            "\n\n"
            "Now produce the final runtime understanding JSON. "
            "Connect the screenshots, user notes, and project "
            "code scan into one coherent explanation of how the "
            "project works."
        )

    @staticmethod
    def _compact_project_context(
        project_context: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Keep only the project fields useful for runtime
        understanding so the prompt stays manageable.
        """

        return {
            "project_name": project_context.get(
                "project_name"
            ),
            "project_path": project_context.get(
                "project_path"
            ),
            "statistics": project_context.get(
                "statistics",
                {},
            ),
            "entrypoints": project_context.get(
                "entrypoints",
                [],
            ),
            "api_reference": (
                RuntimeContextAnalyzer
                ._limit_list(
                    project_context.get(
                        "api_reference",
                        [],
                    ),
                    limit=30,
                )
            ),
            "module_references": (
                RuntimeContextAnalyzer
                ._compact_modules(
                    project_context.get(
                        "module_references",
                        [],
                    )
                )
            ),
            "internal_dependencies": (
                RuntimeContextAnalyzer
                ._limit_list(
                    project_context.get(
                        "internal_dependencies",
                        [],
                    ),
                    limit=40,
                )
            ),
        }

    @staticmethod
    def _compact_modules(
        modules: Any,
    ) -> list[dict[str, Any]]:
        if not isinstance(modules, list):
            return []

        compact_modules: list[
            dict[str, Any]
        ] = []

        for module in modules[:30]:
            if not isinstance(module, dict):
                continue

            compact_modules.append(
                {
                    "module": module.get(
                        "module"
                    ),
                    "file": module.get(
                        "file"
                    ),
                    "summary": (
                        module.get("summary")
                        or module.get(
                            "purpose_hint"
                        )
                        or module.get(
                            "module_docstring"
                        )
                    ),
                    "routes": module.get(
                        "routes",
                        [],
                    ),
                    "functions": (
                        RuntimeContextAnalyzer
                        ._compact_symbols(
                            module.get(
                                "functions",
                                [],
                            )
                        )
                    ),
                    "async_functions": (
                        RuntimeContextAnalyzer
                        ._compact_symbols(
                            module.get(
                                "async_functions",
                                [],
                            )
                        )
                    ),
                    "classes": (
                        RuntimeContextAnalyzer
                        ._compact_symbols(
                            module.get(
                                "classes",
                                [],
                            )
                        )
                    ),
                }
            )

        return compact_modules

    @staticmethod
    def _compact_symbols(
        symbols: Any,
    ) -> list[dict[str, Any]]:
        if not isinstance(symbols, list):
            return []

        compact_symbols: list[
            dict[str, Any]
        ] = []

        for symbol in symbols[:12]:
            if not isinstance(symbol, dict):
                continue

            compact_symbols.append(
                {
                    "name": symbol.get(
                        "name"
                    ),
                    "signature": symbol.get(
                        "signature"
                    ),
                    "docstring": symbol.get(
                        "docstring"
                    ),
                    "called_functions": symbol.get(
                        "called_functions_preview",
                        symbol.get(
                            "called_functions",
                            [],
                        ),
                    ),
                }
            )

        return compact_symbols

    @staticmethod
    def _compact_context_blocks(
        context_blocks: list[Any],
    ) -> list[dict[str, Any]]:
        compact_blocks: list[
            dict[str, Any]
        ] = []

        for index, block in enumerate(
            context_blocks,
            start=1,
        ):
            if not isinstance(block, dict):
                continue

            screenshot = block.get(
                "screenshot"
            )

            screenshot_name = None

            if isinstance(screenshot, dict):
                screenshot_name = (
                    screenshot.get(
                        "original_filename"
                    )
                    or screenshot.get(
                        "filename"
                    )
                )

            compact_blocks.append(
                {
                    "block_number": index,
                    "title": block.get(
                        "title"
                    ),
                    "text": block.get(
                        "text"
                    ),
                    "screenshot_filename": (
                        screenshot_name
                    ),
                }
            )

        return compact_blocks

    @staticmethod
    def _compact_screenshots(
        screenshots: list[Any],
    ) -> list[dict[str, Any]]:
        compact_screenshots: list[
            dict[str, Any]
        ] = []

        for index, screenshot in enumerate(
            screenshots,
            start=1,
        ):
            if not isinstance(screenshot, dict):
                continue

            compact_screenshots.append(
                {
                    "image_number": index,
                    "original_filename": screenshot.get(
                        "original_filename"
                    ),
                    "filename": screenshot.get(
                        "filename"
                    ),
                    "content_type": screenshot.get(
                        "content_type"
                    ),
                }
            )

        return compact_screenshots

    @staticmethod
    def _limit_list(
        value: Any,
        limit: int,
    ) -> list[Any]:
        if not isinstance(value, list):
            return []

        return value[:limit]

    def _validate_runtime_understanding(
        self,
        runtime_understanding: Any,
    ) -> None:
        if not isinstance(runtime_understanding, dict):
            raise RuntimeError(
                "Runtime understanding must be a JSON object."
            )

        missing_fields = (
            self.REQUIRED_FIELDS
            - set(runtime_understanding.keys())
        )

        if missing_fields:
            raise RuntimeError(
                "Runtime understanding is missing fields: "
                + ", ".join(
                    sorted(missing_fields)
                )
            )

        if not isinstance(
            runtime_understanding.get(
                "runtime_summary"
            ),
            str,
        ):
            raise RuntimeError(
                "runtime_summary must be a string."
            )

        list_fields = [
            "tooling_stack",
            "runtime_flow",
            "screenshot_insights",
            "operational_notes",
            "risks_or_gaps",
        ]

        for field_name in list_fields:
            if not isinstance(
                runtime_understanding.get(
                    field_name
                ),
                list,
            ):
                raise RuntimeError(
                    f"{field_name} must be a list."
                )