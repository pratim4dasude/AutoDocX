from app.services.llm.anthropic_provider import (
    AnthropicProvider,
)
from app.services.llm.base import (
    BaseLLMProvider,
)
from app.services.llm.openai_provider import (
    OpenAIProvider,
)


class LLMProviderFactory:
    """
    Creates an LLM provider from the provider name
    supplied in the API request.
    """

    PROVIDER_ALIASES = {
        "openai": "openai",
        "open_ai": "openai",
        "anthropic": "anthropic",
        "claude": "anthropic",
    }

    @classmethod
    def create_provider(
        cls,
        provider_name: str,
        api_key: str,
        model: str | None = None,
    ) -> BaseLLMProvider:
        normalized_provider = (
            cls.normalize_provider_name(
                provider_name=provider_name,
            )
        )

        if normalized_provider == "openai":
            return OpenAIProvider(
                api_key=api_key,
                model=model,
            )

        if normalized_provider == "anthropic":
            return AnthropicProvider(
                api_key=api_key,
                model=model,
            )

        raise ValueError(
            "Unsupported LLM provider. "
            "Use 'openai', 'anthropic', "
            "or 'claude'."
        )

    @classmethod
    def normalize_provider_name(
        cls,
        provider_name: str,
    ) -> str:
        if not isinstance(provider_name, str):
            raise ValueError(
                "The LLM provider name is required."
            )

        cleaned_provider = (
            provider_name.strip().lower()
        )

        normalized_provider = (
            cls.PROVIDER_ALIASES.get(
                cleaned_provider
            )
        )

        if normalized_provider is None:
            raise ValueError(
                "Unsupported LLM provider. "
                "Use 'openai', 'anthropic', "
                "or 'claude'."
            )

        return normalized_provider