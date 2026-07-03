from typing import Any

from openai import OpenAI

from app.services.llm.base import (
    BaseLLMProvider,
)


class OpenAIProvider(BaseLLMProvider):
    """
    OpenAI implementation using the Responses API.
    """

    DEFAULT_MODEL = "gpt-5-mini"

    def __init__(
        self,
        api_key: str,
        model: str | None = None,
    ) -> None:
        selected_model = (
            model.strip()
            if isinstance(model, str)
            and model.strip()
            else self.DEFAULT_MODEL
        )

        super().__init__(
            api_key=api_key,
            model=selected_model,
        )

        self.client = OpenAI(
            api_key=self.api_key,
        )

    @property
    def provider_name(self) -> str:
        return "openai"

    def generate_json(
        self,
        system_prompt: str,
        user_prompt: str,
    ) -> dict[str, Any]:
        try:
            response = (
                self.client.responses.create(
                    model=self.model,
                    instructions=system_prompt,
                    input=user_prompt,
                    max_output_tokens=8000,
                )
            )

            response_text = (
                response.output_text
            )

            return self.parse_json_response(
                response_text=response_text,
            )

        except RuntimeError:
            raise

        except Exception as error:
            raise RuntimeError(
                "OpenAI request failed. Check the "
                "API key, model name, account access, "
                "quota, and internet connection."
            ) from error