import json
from abc import ABC, abstractmethod
from typing import Any


class BaseLLMProvider(ABC):
    """
    Common interface implemented by every AutoDocX LLM provider.
    """

    def __init__(
        self,
        api_key: str,
        model: str,
    ) -> None:
        cleaned_api_key = api_key.strip()
        cleaned_model = model.strip()

        if not cleaned_api_key:
            raise ValueError(
                "The LLM API key cannot be empty."
            )

        if not cleaned_model:
            raise ValueError(
                "The LLM model cannot be empty."
            )

        self.api_key = cleaned_api_key
        self.model = cleaned_model

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """
        Returns the normalized provider name.
        """

    @abstractmethod
    def generate_json(
        self,
        system_prompt: str,
        user_prompt: str,
    ) -> dict[str, Any]:
        """
        Sends a prompt to the provider and returns parsed JSON.
        """

    @staticmethod
    def parse_json_response(
        response_text: str,
    ) -> dict[str, Any]:
        """
        Parses a model response into a JSON dictionary.

        It supports:
        - plain JSON
        - JSON wrapped in Markdown code fences
        - surrounding explanatory text containing one JSON object
        """

        if not isinstance(response_text, str):
            raise RuntimeError(
                "The LLM returned an invalid response type."
            )

        cleaned_text = response_text.strip()

        if not cleaned_text:
            raise RuntimeError(
                "The LLM returned an empty response."
            )

        if cleaned_text.startswith("```"):
            cleaned_text = (
                BaseLLMProvider._remove_code_fence(
                    cleaned_text
                )
            )

        try:
            parsed_response = json.loads(
                cleaned_text
            )
        except json.JSONDecodeError:
            parsed_response = (
                BaseLLMProvider._extract_json_object(
                    cleaned_text
                )
            )

        if not isinstance(
            parsed_response,
            dict,
        ):
            raise RuntimeError(
                "The LLM response must be a JSON object."
            )

        return parsed_response

    @staticmethod
    def _remove_code_fence(
        value: str,
    ) -> str:
        lines = value.splitlines()

        if lines and lines[0].strip().startswith(
            "```"
        ):
            lines = lines[1:]

        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]

        return "\n".join(lines).strip()

    @staticmethod
    def _extract_json_object(
        value: str,
    ) -> dict[str, Any]:
        first_brace = value.find("{")
        last_brace = value.rfind("}")

        if (
            first_brace == -1
            or last_brace == -1
            or last_brace <= first_brace
        ):
            raise RuntimeError(
                "The LLM response did not contain "
                "a valid JSON object."
            )

        json_text = value[
            first_brace:last_brace + 1
        ]

        try:
            parsed_value = json.loads(
                json_text
            )
        except json.JSONDecodeError as error:
            raise RuntimeError(
                "The LLM returned malformed JSON."
            ) from error

        if not isinstance(parsed_value, dict):
            raise RuntimeError(
                "The LLM response must be a JSON object."
            )

        return parsed_value