import base64
import mimetypes
from pathlib import Path
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

            response_text = (
                self._extract_text_response(
                    response=response,
                )
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

    def generate_json_with_images(
        self,
        system_prompt: str,
        user_prompt: str,
        image_paths: list[str],
    ) -> dict[str, Any]:
        """
        Send text plus screenshots to a Claude vision-capable
        model and parse the JSON response.
        """

        try:
            content: list[dict[str, Any]] = [
                {
                    "type": "text",
                    "text": user_prompt,
                }
            ]

            for image_path in image_paths:
                image_block = (
                    self._image_path_to_anthropic_block(
                        image_path=image_path,
                    )
                )

                content.append(
                    image_block
                )

            response = (
                self.client.messages.create(
                    model=self.model,
                    max_tokens=8000,
                    temperature=0,
                    system=system_prompt,
                    messages=[
                        {
                            "role": "user",
                            "content": content,
                        }
                    ],
                )
            )

            response_text = (
                self._extract_text_response(
                    response=response,
                )
            )

            return self.parse_json_response(
                response_text=response_text,
            )

        except RuntimeError:
            raise

        except Exception as error:
            raise RuntimeError(
                "Anthropic vision request failed. Check "
                "that the selected Claude model supports "
                "image input, and verify the API key, "
                "quota, and internet connection."
            ) from error

    @staticmethod
    def _extract_text_response(
        response: Any,
    ) -> str:
        """
        Extract all text blocks from an Anthropic response.
        """

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

        return "\n".join(
            response_text_parts
        )

    @staticmethod
    def _image_path_to_anthropic_block(
        image_path: str,
    ) -> dict[str, Any]:
        """
        Convert an image file path into an Anthropic
        image content block.
        """

        file_path = Path(
            image_path
        )

        if not file_path.exists():
            raise RuntimeError(
                "Screenshot file does not exist: "
                f"{image_path}"
            )

        mime_type = (
            mimetypes.guess_type(
                file_path.name
            )[0]
            or "image/png"
        )

        if mime_type not in {
            "image/png",
            "image/jpeg",
            "image/webp",
            "image/gif",
        }:
            raise RuntimeError(
                "Unsupported screenshot MIME type "
                f"for Anthropic vision: {mime_type}"
            )

        image_bytes = (
            file_path.read_bytes()
        )

        encoded_image = (
            base64.b64encode(
                image_bytes
            ).decode("utf-8")
        )

        return {
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": mime_type,
                "data": encoded_image,
            },
        }