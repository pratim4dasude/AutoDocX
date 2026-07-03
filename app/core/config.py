import os
from pathlib import Path

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[2]
ENV_FILE_PATH = PROJECT_ROOT / ".env"

load_dotenv(
    dotenv_path=ENV_FILE_PATH,
)

WORKSPACE_PATH = PROJECT_ROOT / "workspace"
SCANS_PATH = WORKSPACE_PATH / "scans"
UNDERSTANDINGS_PATH = (
    WORKSPACE_PATH / "understandings"
)
DOCUMENTS_PATH = (
    WORKSPACE_PATH / "documents"
)


def create_required_directories() -> None:
    WORKSPACE_PATH.mkdir(
        parents=True,
        exist_ok=True,
    )

    SCANS_PATH.mkdir(
        parents=True,
        exist_ok=True,
    )

    UNDERSTANDINGS_PATH.mkdir(
        parents=True,
        exist_ok=True,
    )

    DOCUMENTS_PATH.mkdir(
        parents=True,
        exist_ok=True,
    )


def get_llm_provider() -> str:
    provider_name = os.getenv(
        "LLM_PROVIDER",
        "",
    ).strip().lower()

    provider_aliases = {
        "openai": "openai",
        "open_ai": "openai",
        "anthropic": "anthropic",
        "claude": "anthropic",
    }

    normalized_provider = (
        provider_aliases.get(provider_name)
    )

    if normalized_provider is None:
        raise ValueError(
            "LLM_PROVIDER is missing or invalid. "
            "Use 'openai', 'anthropic', or "
            "'claude' in the .env file."
        )

    return normalized_provider


def get_llm_api_key(
    provider_name: str,
) -> str:
    normalized_provider = (
        provider_name.strip().lower()
    )

    if normalized_provider == "openai":
        variable_name = "OPENAI_API_KEY"

    elif normalized_provider == "anthropic":
        variable_name = "ANTHROPIC_API_KEY"

    else:
        raise ValueError(
            "Unsupported LLM provider."
        )

    api_key = os.getenv(
        variable_name,
        "",
    ).strip()

    if not api_key:
        raise ValueError(
            f"{variable_name} is missing. "
            "Add it to the .env file."
        )

    return api_key


def get_llm_model(
    provider_name: str,
) -> str | None:
    normalized_provider = (
        provider_name.strip().lower()
    )

    if normalized_provider == "openai":
        variable_name = "OPENAI_MODEL"

    elif normalized_provider == "anthropic":
        variable_name = "ANTHROPIC_MODEL"

    else:
        raise ValueError(
            "Unsupported LLM provider."
        )

    model_name = os.getenv(
        variable_name,
        "",
    ).strip()

    return model_name or None