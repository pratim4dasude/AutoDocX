import base64
import mimetypes
from pathlib import Path
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
                or ""
            ).strip()

            if not response_text:
                raise RuntimeError(
                    "OpenAI returned an empty response."
                )

            return self.parse_json_response(
                response_text=response_text,
            )

        except RuntimeError:
            raise

        except Exception as error:
            error_type = type(error).__name__
            error_message = str(error)

            raise RuntimeError(
                "OpenAI request failed. "
                f"Model: {self.model}. "
                f"Error type: {error_type}. "
                f"Error message: {error_message}"
            ) from error

    def generate_json_with_images(
        self,
        system_prompt: str,
        user_prompt: str,
        image_paths: list[str],
    ) -> dict[str, Any]:
        """
        Send text plus screenshots to an OpenAI vision-capable
        model and parse the JSON response.
        """

        try:
            content: list[dict[str, Any]] = [
                {
                    "type": "input_text",
                    "text": user_prompt,
                }
            ]

            for image_path in image_paths:
                image_url = self._image_path_to_data_url(
                    image_path=image_path,
                )

                content.append(
                    {
                        "type": "input_image",
                        "image_url": image_url,
                    }
                )

            response = (
                self.client.responses.create(
                    model=self.model,
                    instructions=system_prompt,
                    input=[
                        {
                            "role": "user",
                            "content": content,
                        }
                    ],
                    max_output_tokens=8000,
                )
            )

            response_text = (
                response.output_text
                or ""
            ).strip()

            if not response_text:
                raise RuntimeError(
                    "OpenAI vision returned an empty response."
                )

            return self.parse_json_response(
                response_text=response_text,
            )

        except RuntimeError:
            raise

        except Exception as error:
            error_type = type(error).__name__
            error_message = str(error)

            raise RuntimeError(
                "OpenAI vision request failed. "
                f"Model: {self.model}. "
                f"Error type: {error_type}. "
                f"Error message: {error_message}"
            ) from error

    @staticmethod
    def _image_path_to_data_url(
        image_path: str,
    ) -> str:
        """
        Convert an image file path to a base64 data URL.
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

        image_bytes = (
            file_path.read_bytes()
        )

        encoded_image = (
            base64.b64encode(
                image_bytes
            ).decode("utf-8")
        )

        return (
            f"data:{mime_type};base64,"
            f"{encoded_image}"
        )