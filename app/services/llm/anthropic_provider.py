from typing import Any

from anthropic import Anthropic

from app.services.llm.base import (
    BaseLLMProvider,
)


class AnthropicProvider(BaseLLMProvider):
    """
    Anthropic Claude implementation using the Messages API.
    """

    DEFAULT_MODEL = (
        "claude-sonnet-4-20250514"
    )

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

        self.client = Anthropic(
            api_key=self.api_key,
        )

    @property
    def provider_name(self) -> str:
        return "anthropic"

    def generate_json(
        self,
        system_prompt: str,
        user_prompt: str,
    ) -> dict[str, Any]:
        try:
            response = (
                self.client.messages.create(
                    model=self.model,
                    max_tokens=8000,
                    temperature=0,
                    system=system_prompt,
                    messages=[
                        {
                            "role": "user",
                            "content": user_prompt,
                        }
                    ],
                )
            )

            response_text_parts: list[str] = []

            for content_block in response.content:
                block_type = getattr(
                    content_block,
                    "type",
                    None,
                )

                block_text = getattr(
                    content_block,
                    "text",
                    None,
                )

                if (
                    block_type == "text"
                    and isinstance(
                        block_text,
                        str,
                    )
                ):
                    response_text_parts.append(
                        block_text
                    )

            response_text = "\n".join(
                response_text_parts
            )

            return self.parse_json_response(
                response_text=response_text,
            )

        except RuntimeError:
            raise

        except Exception as error:
            raise RuntimeError(
                "Anthropic request failed. Check the "
                "API key, model name, account access, "
                "quota, and internet connection."
            ) from error