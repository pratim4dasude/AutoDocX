from pathlib import Path, PureWindowsPath
from typing import Any
from urllib.parse import quote
import io
import json

from uuid import uuid4
import requests
import streamlit as st
from streamlit_paste_button import (
    paste_image_button as pbutton,
)


# ============================================================
# Application configuration
# ============================================================

DEFAULT_API_URL = "http://127.0.0.1:7832"

DEFAULT_PROJECT_PATH = (
    r"C:\Users\PratimMangaldasDasud"
    r"\PycharmProjects\AutoDocX"
)

SYNC_ENDPOINT = "/api/projects/documentation/sync"

SYNC_WITH_CONTEXT_ENDPOINT = (
    "/api/projects/documentation/sync-with-context"
)
REQUEST_TIMEOUT_SECONDS = 900
HISTORY_TIMEOUT_SECONDS = 60

_PROJECT_ROOT = Path(__file__).parent.parent
_ENV_FILE     = _PROJECT_ROOT / ".env"
_ENV_EXAMPLE  = _PROJECT_ROOT / ".env.example"


# ============================================================
# .env helpers (must be defined before setup gate)
# ============================================================

def _read_env_file() -> dict[str, str]:
    env: dict[str, str] = {}
    if not _ENV_FILE.exists():
        return env
    for line in _ENV_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        env[key.strip()] = value.strip()
    return env


def _is_llm_configured(env: dict[str, str]) -> bool:
    provider = env.get("LLM_PROVIDER", "").strip().lower()
    if provider not in ("openai", "open_ai", "anthropic", "claude"):
        return False
    key_name = (
        "OPENAI_API_KEY"
        if provider in ("openai", "open_ai")
        else "ANTHROPIC_API_KEY"
    )
    api_key = env.get(key_name, "").strip()
    return (
        bool(api_key)
        and "your-" not in api_key
        and "placeholder" not in api_key.lower()
    )


def _write_env_file(env: dict[str, str]) -> None:
    lines = [f"{k}={v}" for k, v in env.items()]
    _ENV_FILE.write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )


# ============================================================
# Streamlit page configuration
# ============================================================

st.set_page_config(
    page_title="AutoDocX",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ============================================================
# Session state
# ============================================================

if "sync_result" not in st.session_state:
    st.session_state.sync_result = None

if "last_project_path" not in st.session_state:
    st.session_state.last_project_path = (
        DEFAULT_PROJECT_PATH
    )

if "last_error" not in st.session_state:
    st.session_state.last_error = None

if "history_refresh_counter" not in st.session_state:
    st.session_state.history_refresh_counter = 0

if "runtime_context_blocks" not in st.session_state:
    st.session_state.runtime_context_blocks = [
        {
            "id": uuid4().hex[:8],
            "title": "",
            "text": "",
            "image_bytes": None,
            "image_name": None,
        },
        {
            "id": uuid4().hex[:8],
            "title": "",
            "text": "",
            "image_bytes": None,
            "image_name": None,
        },
    ]


# ============================================================
# API key setup gate
# ============================================================

_current_env = _read_env_file()

if not _is_llm_configured(_current_env):
    st.title("AutoDocX — Setup")

    st.info(
        "AutoDocX needs an LLM API key before it can "
        "generate documentation. Fill in the fields "
        "below and click Save."
    )

    with st.form("llm_setup_form"):
        provider_choice = st.selectbox(
            "LLM provider",
            options=["openai", "anthropic"],
            index=0,
            help=(
                "openai → uses OpenAI GPT models. "
                "anthropic → uses Anthropic Claude models."
            ),
        )

        api_key_input = st.text_input(
            "API key",
            type="password",
            placeholder=(
                "sk-...  (OpenAI)   or   sk-ant-...  (Anthropic)"
            ),
        )

        model_input = st.text_input(
            "Model name (optional — leave blank for default)",
            placeholder=(
                "gpt-4o-mini   or   claude-sonnet-4-20250514"
            ),
        )

        save_clicked = st.form_submit_button(
            "Save and continue",
            type="primary",
            use_container_width=True,
        )

    if save_clicked:
        api_key_clean = api_key_input.strip()

        if not api_key_clean:
            st.error("API key cannot be empty.")

        else:
            new_env = _current_env.copy()
            new_env["LLM_PROVIDER"] = provider_choice

            if provider_choice == "openai":
                new_env["OPENAI_API_KEY"] = api_key_clean
                new_env["OPENAI_MODEL"] = (
                    model_input.strip() or "gpt-5-mini"
                )
            else:
                new_env["ANTHROPIC_API_KEY"] = api_key_clean
                new_env["ANTHROPIC_MODEL"] = (
                    model_input.strip()
                    or "claude-sonnet-4-20250514"
                )

            _write_env_file(new_env)

            # Tell the running backend to reload .env so no restart is needed
            try:
                requests.post(
                    f"{DEFAULT_API_URL}/api/config/reload",
                    timeout=5,
                )
            except Exception:
                pass

            st.success("API key saved. Loading AutoDocX...")
            st.rerun()

    st.stop()


# ============================================================
# Styling
# ============================================================

st.markdown(
    """
    <style>
        .main-title {
            font-size: 2.4rem;
            font-weight: 800;
            margin-bottom: 0.2rem;
        }

        .subtitle {
            color: #64748b;
            font-size: 1.05rem;
            margin-bottom: 2rem;
        }

        .status-card {
            border: 1px solid rgba(128, 128, 128, 0.25);
            border-radius: 14px;
            padding: 18px;
            margin-top: 12px;
        }

        .status-created {
            border-left: 6px solid #16a34a;
        }

        .status-updated {
            border-left: 6px solid #2563eb;
        }

        .status-unchanged {
            border-left: 6px solid #ca8a04;
        }

        .small-muted {
            color: #64748b;
            font-size: 0.9rem;
        }

        .latest-card {
            border: 1px solid rgba(128, 128, 128, 0.25);
            border-radius: 14px;
            padding: 18px;
            margin-top: 12px;
            margin-bottom: 16px;
        }

        div[data-testid="stMetric"] {
            border: 1px solid rgba(128, 128, 128, 0.20);
            border-radius: 12px;
            padding: 12px;
        }
    </style>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# General helper functions
# ============================================================

def normalize_api_url(
    api_url: str,
) -> str:
    """
    Remove trailing slashes from the configured
    FastAPI base URL.
    """

    return api_url.strip().rstrip("/")


def get_project_name_from_path(
    project_path: str,
) -> str:
    """
    Extract the final folder name from a Windows
    project path.
    """

    cleaned_path = project_path.strip()

    if not cleaned_path:
        return ""

    cleaned_path = cleaned_path.rstrip("\\/")

    if not cleaned_path:
        return ""

    return PureWindowsPath(
        cleaned_path
    ).name.strip()


def build_document_url(
    api_url: str,
    project_name: str,
    document_id: str,
) -> str:
    """
    Build the FastAPI URL used to open generated
    HTML documentation.
    """

    safe_project_name = quote(
        project_name,
        safe="",
    )

    safe_document_id = quote(
        document_id,
        safe="",
    )

    return (
        f"{normalize_api_url(api_url)}"
        f"/api/projects/"
        f"{safe_project_name}"
        f"/documents/"
        f"{safe_document_id}"
        f"/html"
    )


def parse_json_response(
    response: requests.Response,
) -> Any:
    """
    Parse a requests response as JSON and produce
    a useful fallback when JSON is not returned.
    """

    try:
        return response.json()

    except requests.exceptions.JSONDecodeError:
        return {
            "detail": (
                response.text
                or "The backend returned a non-JSON response."
            )
        }


def get_error_detail(
    response_data: Any,
    default_message: str,
) -> str:
    """
    Read a useful error message from a backend
    response.
    """

    if isinstance(response_data, dict):
        detail = response_data.get(
            "detail",
            default_message,
        )

        return str(detail)

    return default_message


# ============================================================
# FastAPI client functions
# ============================================================

def sync_documentation(
    api_url: str,
    project_path: str,
) -> dict[str, Any]:
    """
    Call the all-in-one AutoDocX documentation
    synchronization endpoint.
    """

    endpoint_url = (
        f"{normalize_api_url(api_url)}"
        f"{SYNC_ENDPOINT}"
    )

    response = requests.post(
        endpoint_url,
        json={
            "project_path": project_path,
        },
        headers={
            "accept": "application/json",
            "Content-Type": "application/json",
        },
        timeout=REQUEST_TIMEOUT_SECONDS,
    )

    response_data = parse_json_response(
        response
    )

    if not response.ok:
        detail = get_error_detail(
            response_data=response_data,
            default_message=(
                "Documentation synchronization "
                "failed."
            ),
        )

        raise RuntimeError(
            f"Backend returned HTTP "
            f"{response.status_code}: {detail}"
        )

    if not isinstance(response_data, dict):
        raise RuntimeError(
            "The backend returned an invalid "
            "synchronization response."
        )

    return response_data

def create_runtime_context_block(
    title: str = "",
) -> dict[str, Any]:
    """
    Create one empty runtime context block.
    """

    return {
        "id": uuid4().hex[:8],
        "title": title,
        "text": "",
        "image_bytes": None,
        "image_name": None,
    }


def image_to_png_bytes(
    image: Any,
) -> bytes:
    """
    Convert a pasted PIL image into PNG bytes.
    """

    buffer = io.BytesIO()

    image.save(
        buffer,
        format="PNG",
    )

    return buffer.getvalue()


def context_blocks_have_content(
    context_blocks: list[dict[str, Any]],
) -> bool:
    """
    Check whether any runtime context block has
    useful text or a pasted screenshot.
    """

    for block in context_blocks:
        title = str(
            block.get(
                "title",
                "",
            )
            or ""
        ).strip()

        text = str(
            block.get(
                "text",
                "",
            )
            or ""
        ).strip()

        image_bytes = block.get(
            "image_bytes"
        )

        if title or text or image_bytes:
            return True

    return False


def build_context_blocks_payload(
    context_blocks: list[dict[str, Any]],
) -> tuple[
    str,
    list[tuple[str, tuple[str, bytes, str]]],
]:
    """
    Build multipart form payload for ordered
    context blocks.

    The screenshots are sent as files. Each block
    stores screenshot_index so the backend can
    connect the correct image to the correct block.
    """

    payload_blocks: list[
        dict[str, Any]
    ] = []

    files: list[
        tuple[str, tuple[str, bytes, str]]
    ] = []

    for block_index, block in enumerate(
        context_blocks,
        start=1,
    ):
        title = str(
            block.get(
                "title",
                "",
            )
            or ""
        ).strip()

        text = str(
            block.get(
                "text",
                "",
            )
            or ""
        ).strip()

        image_bytes = block.get(
            "image_bytes"
        )

        screenshot_index = None

        if isinstance(
            image_bytes,
            bytes,
        ) and image_bytes:
            screenshot_index = len(files)

            image_name = str(
                block.get(
                    "image_name",
                    "",
                )
                or ""
            ).strip()

            if not image_name:
                image_name = (
                    f"context_block_"
                    f"{block_index:03d}.png"
                )

            files.append(
                (
                    "screenshots",
                    (
                        image_name,
                        image_bytes,
                        "image/png",
                    ),
                )
            )

        if (
            not title
            and not text
            and screenshot_index is None
        ):
            continue

        payload_blocks.append(
            {
                "title": (
                    title
                    or f"Runtime context {block_index}"
                ),
                "text": text,
                "screenshot_index": screenshot_index,
            }
        )

    return (
        json.dumps(
            payload_blocks,
            ensure_ascii=False,
        ),
        files,
    )

def sync_documentation_with_context(
    api_url: str,
    project_path: str,
    context_blocks: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    Call the AutoDocX documentation synchronization
    endpoint that accepts ordered runtime/tooling
    context blocks and pasted screenshots.
    """

    endpoint_url = (
        f"{normalize_api_url(api_url)}"
        f"{SYNC_WITH_CONTEXT_ENDPOINT}"
    )

    context_blocks_json, files = (
        build_context_blocks_payload(
            context_blocks=context_blocks,
        )
    )

    response = requests.post(
        endpoint_url,
        data={
            "project_path": project_path,
            "additional_context": "",
            "context_blocks_json": (
                context_blocks_json
            ),
        },
        files=files,
        headers={
            "accept": "application/json",
        },
        timeout=REQUEST_TIMEOUT_SECONDS,
    )

    response_data = parse_json_response(
        response
    )

    if not response.ok:
        detail = get_error_detail(
            response_data=response_data,
            default_message=(
                "Documentation synchronization "
                "with runtime context failed."
            ),
        )

        raise RuntimeError(
            f"Backend returned HTTP "
            f"{response.status_code}: {detail}"
        )

    if not isinstance(response_data, dict):
        raise RuntimeError(
            "The backend returned an invalid "
            "synchronization response."
        )

    return response_data

def get_document_history(
    api_url: str,
    project_name: str,
) -> list[dict[str, Any]]:
    """
    Retrieve every generated document version for
    one project.
    """

    safe_project_name = quote(
        project_name,
        safe="",
    )

    endpoint_url = (
        f"{normalize_api_url(api_url)}"
        f"/api/projects/"
        f"{safe_project_name}"
        f"/documents"
    )

    response = requests.get(
        endpoint_url,
        headers={
            "accept": "application/json",
        },
        timeout=HISTORY_TIMEOUT_SECONDS,
    )

    response_data = parse_json_response(
        response
    )

    if not response.ok:
        detail = get_error_detail(
            response_data=response_data,
            default_message=(
                "Could not retrieve document history."
            ),
        )

        raise RuntimeError(
            f"Backend returned HTTP "
            f"{response.status_code}: {detail}"
        )

    if not isinstance(response_data, list):
        raise RuntimeError(
            "The backend returned invalid "
            "document history data."
        )

    valid_documents: list[
        dict[str, Any]
    ] = []

    for item in response_data:
        if isinstance(item, dict):
            valid_documents.append(item)

    return sorted(
        valid_documents,
        key=lambda document: str(
            document.get(
                "created_at",
                "",
            )
        ),
        reverse=True,
    )


# ============================================================
# Existing-document display functions
# ============================================================

def display_latest_document(
    api_url: str,
    project_name: str,
    documents: list[dict[str, Any]],
) -> None:
    """
    Display the latest document before the user
    starts a create or update operation.
    """

    st.subheader("Existing documentation")

    if not documents:
        st.info(
            "No documentation exists for this "
            "project yet."
        )

        st.caption(
            "Click Create Documentation to scan "
            "the project and generate its first "
            "HTML document."
        )

        return

    latest_document = documents[0]

    document_id = str(
        latest_document.get(
            "document_id",
            "",
        )
    ).strip()

    scan_id = str(
        latest_document.get(
            "scan_id",
            "",
        )
    ).strip()

    understanding_id = str(
        latest_document.get(
            "understanding_id",
            "",
        )
    ).strip()

    created_at = str(
        latest_document.get(
            "created_at",
            "",
        )
    )

    update_type = str(
        latest_document.get(
            "update_type",
            "initial",
        )
    )

    previous_document_id = latest_document.get(
        "previous_document_id"
    )

    document_url = build_document_url(
        api_url=api_url,
        project_name=project_name,
        document_id=document_id,
    )

    metric_columns = st.columns(3)

    metric_columns[0].metric(
        "Document versions",
        len(documents),
    )

    metric_columns[1].metric(
        "Latest type",
        update_type.replace(
            "_",
            " ",
        ).title(),
    )

    metric_columns[2].metric(
        "Latest document",
        document_id,
    )

    st.caption(
        f"Last generated: {created_at}"
    )

    with st.container(
        border=True,
    ):
        identifier_columns = st.columns(2)

        with identifier_columns[0]:
            st.text_input(
                "Latest document ID",
                value=document_id,
                disabled=True,
                key="latest_document_id",
            )

            st.text_input(
                "Latest scan ID",
                value=scan_id,
                disabled=True,
                key="latest_scan_id",
            )

        with identifier_columns[1]:
            st.text_input(
                "Latest understanding ID",
                value=understanding_id,
                disabled=True,
                key="latest_understanding_id",
            )

            st.text_input(
                "Previous document ID",
                value=str(
                    previous_document_id
                    or "None"
                ),
                disabled=True,
                key="latest_previous_document_id",
            )

        st.link_button(
            "📄 Open Latest Documentation",
            url=document_url,
            type="primary",
            use_container_width=True,
        )


def display_document_history(
    api_url: str,
    project_name: str,
    documents: list[dict[str, Any]],
) -> None:
    """
    Display all generated document versions.
    """

    if not documents:
        return

    with st.expander(
        (
            f"View all document versions "
            f"({len(documents)})"
        )
    ):
        total_versions = len(documents)

        for index, document in enumerate(
            documents,
            start=1,
        ):
            document_id = str(
                document.get(
                    "document_id",
                    "",
                )
            ).strip()

            scan_id = str(
                document.get(
                    "scan_id",
                    "",
                )
            ).strip()

            understanding_id = str(
                document.get(
                    "understanding_id",
                    "",
                )
            ).strip()

            created_at = str(
                document.get(
                    "created_at",
                    "",
                )
            )

            update_type = str(
                document.get(
                    "update_type",
                    "initial",
                )
            )

            previous_document_id = document.get(
                "previous_document_id"
            )

            comparison_summary = document.get(
                "comparison_summary"
            )

            document_url = build_document_url(
                api_url=api_url,
                project_name=project_name,
                document_id=document_id,
            )

            version_number = (
                total_versions - index + 1
            )

            with st.container(
                border=True,
            ):
                title_column, type_column = (
                    st.columns(
                        [4, 1]
                    )
                )

                with title_column:
                    st.markdown(
                        f"### Version {version_number}"
                    )

                    st.caption(
                        created_at
                    )

                with type_column:
                    if update_type == "initial":
                        st.success("Initial")
                    else:
                        st.info("Updated")

                identifier_columns = st.columns(2)

                with identifier_columns[0]:
                    st.text_input(
                        "Document ID",
                        value=document_id,
                        disabled=True,
                        key=(
                            "history_document_id_"
                            f"{document_id}"
                        ),
                    )

                    st.text_input(
                        "Scan ID",
                        value=scan_id,
                        disabled=True,
                        key=(
                            "history_scan_id_"
                            f"{document_id}"
                        ),
                    )

                with identifier_columns[1]:
                    st.text_input(
                        "Understanding ID",
                        value=understanding_id,
                        disabled=True,
                        key=(
                            "history_understanding_id_"
                            f"{document_id}"
                        ),
                    )

                    st.text_input(
                        "Previous document ID",
                        value=str(
                            previous_document_id
                            or "None"
                        ),
                        disabled=True,
                        key=(
                            "history_previous_id_"
                            f"{document_id}"
                        ),
                    )

                st.link_button(
                    "Open this version",
                    url=document_url,
                    use_container_width=True,
                )

                if (
                    isinstance(
                        comparison_summary,
                        dict,
                    )
                    and comparison_summary
                ):
                    with st.expander(
                        "View changes in this version"
                    ):
                        st.json(
                            comparison_summary
                        )


# ============================================================
# Synchronization-result display functions
# ============================================================

def display_action_status(
    result: dict[str, Any],
) -> None:
    """
    Display the created, updated, or unchanged
    synchronization result.
    """

    action = str(
        result.get(
            "action",
            "unknown",
        )
    ).lower()

    message = str(
        result.get(
            "message",
            "",
        )
    )

    if action == "created":
        st.success(
            "Initial documentation created "
            "successfully."
        )

    elif action == "updated":
        st.success(
            "Documentation updated successfully."
        )

    elif action == "unchanged":
        st.info(
            "The documentation is already current."
        )

    else:
        st.warning(
            "The backend returned an unknown action."
        )

    css_class = {
        "created": "status-created",
        "updated": "status-updated",
        "unchanged": "status-unchanged",
    }.get(
        action,
        "",
    )

    st.markdown(
        f"""
        <div class="status-card {css_class}">
            <strong>Action:</strong>
            {action.upper()}
            <br>
            <span class="small-muted">
                {message}
            </span>
        </div>
        """,
        unsafe_allow_html=True,
    )


def display_identifiers(
    result: dict[str, Any],
) -> None:
    """
    Display scan, understanding, and document IDs
    returned by synchronization.
    """

    project_name = result.get(
        "project_name",
        "Not available",
    )

    scan_id = result.get(
        "scan_id",
        "Not available",
    )

    understanding_id = result.get(
        "understanding_id",
        "Not generated",
    )

    document_id = result.get(
        "document_id",
        "Not available",
    )

    previous_document_id = result.get(
        "previous_document_id"
    )

    st.subheader("Synchronization result")

    columns = st.columns(2)

    with columns[0]:
        st.text_input(
            "Project name",
            value=str(project_name),
            disabled=True,
            key="result_project_name",
        )

        st.text_input(
            "Scan ID",
            value=str(scan_id),
            disabled=True,
            key="result_scan_id",
        )

    with columns[1]:
        st.text_input(
            "Document ID",
            value=str(document_id),
            disabled=True,
            key="result_document_id",
        )

        st.text_input(
            "Understanding ID",
            value=str(understanding_id),
            disabled=True,
            key="result_understanding_id",
        )

    if previous_document_id:
        st.text_input(
            "Previous document ID",
            value=str(previous_document_id),
            disabled=True,
            key="result_previous_document_id",
        )


def display_comparison_summary(
    result: dict[str, Any],
) -> None:
    """
    Display scan comparison metrics returned by
    the synchronization endpoint.
    """

    comparison_summary = result.get(
        "comparison_summary",
        {},
    )

    if not isinstance(
        comparison_summary,
        dict,
    ):
        return

    if not comparison_summary:
        return

    st.subheader("Change summary")

    first_row = st.columns(4)

    first_row[0].metric(
        "Total changes",
        comparison_summary.get(
            "total_changes",
            0,
        ),
    )

    first_row[1].metric(
        "Added files",
        comparison_summary.get(
            "added_files",
            0,
        ),
    )

    first_row[2].metric(
        "Modified files",
        comparison_summary.get(
            "modified_files",
            0,
        ),
    )

    first_row[3].metric(
        "Deleted files",
        comparison_summary.get(
            "deleted_files",
            0,
        ),
    )

    second_row = st.columns(4)

    second_row[0].metric(
        "Added symbols",
        comparison_summary.get(
            "added_symbols",
            0,
        ),
    )

    second_row[1].metric(
        "Modified symbols",
        comparison_summary.get(
            "modified_symbols",
            0,
        ),
    )

    second_row[2].metric(
        "Added routes",
        comparison_summary.get(
            "added_routes",
            0,
        ),
    )

    second_row[3].metric(
        "Added dependencies",
        comparison_summary.get(
            "added_dependencies",
            0,
        ),
    )

    with st.expander(
        "View complete comparison summary"
    ):
        st.json(
            comparison_summary
        )


def display_document_metadata(
    result: dict[str, Any],
) -> None:
    """
    Display complete metadata returned for the
    generated document.
    """

    document = result.get(
        "document",
        {},
    )

    if not isinstance(document, dict):
        return

    if not document:
        return

    with st.expander(
        "View generated document metadata"
    ):
        st.json(
            document
        )


# ============================================================
# Sidebar
# ============================================================

with st.sidebar:
    st.title("Settings")

    api_url = st.text_input(
        "FastAPI URL",
        value=DEFAULT_API_URL,
        help=(
            "Address where the AutoDocX FastAPI "
            "backend is running."
        ),
    )

    st.divider()

    st.markdown(
        """
        ### Required services

        **FastAPI**

        `http://127.0.0.1:7832`

        **Streamlit**

        `http://localhost:7833`
        """
    )

    st.divider()

    if st.button(
        "Refresh page",
        use_container_width=True,
    ):
        st.session_state.history_refresh_counter += 1
        st.rerun()

    if st.button(
        "Clear synchronization result",
        use_container_width=True,
    ):
        st.session_state.sync_result = None
        st.session_state.last_error = None
        st.rerun()


# ============================================================
# Main page
# ============================================================

st.markdown(
    '<div class="main-title">AutoDocX</div>',
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="subtitle">
        View existing documentation, open previous
        versions, or create and update documentation
        using one workflow.
    </div>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# Project selection
# ============================================================

with st.container(
    border=True,
):
    st.subheader("Project")

    project_path = st.text_input(
        "Project path",
        value=(
            st.session_state
            .last_project_path
        ),
        placeholder=(
            r"C:\Users\Name\PycharmProjects"
            r"\ProjectName"
        ),
        help=(
            "Enter the absolute local path of the "
            "project that AutoDocX should process."
        ),
    )

with st.container(
    border=True,
):
    st.subheader("Runtime and tooling context")

    st.write(
        "Create ordered documentation blocks. "
        "Each block can have notes and one pasted "
        "screenshot from Win + Shift + S."
    )

    st.caption(
        "Use Win + Shift + S, copy the screenshot, "
        "then click the paste button inside the "
        "correct block."
    )

    action_columns = st.columns(
        [1, 1, 3]
    )

    with action_columns[0]:
        if st.button(
            "➕ Add block",
            use_container_width=True,
        ):
            st.session_state.runtime_context_blocks.append(
                create_runtime_context_block(
                    title=(
                        "New runtime context"
                    ),
                )
            )
            st.rerun()

    with action_columns[1]:
        if st.button(
            "🧹 Clear blocks",
            use_container_width=True,
        ):
            st.session_state.runtime_context_blocks = [
                create_runtime_context_block(
                    title="Docker runtime",
                ),
                create_runtime_context_block(
                    title="Temporal workflow",
                ),
            ]
            st.rerun()

    runtime_context_blocks = (
        st.session_state.runtime_context_blocks
    )

    for index, block in enumerate(
        runtime_context_blocks,
        start=1,
    ):
        block_id = str(
            block.get(
                "id",
                index,
            )
        )

        with st.container(
            border=True,
        ):
            header_columns = st.columns(
                [5, 1]
            )

            with header_columns[0]:
                st.markdown(
                    f"### Context block {index}"
                )

            with header_columns[1]:
                if len(runtime_context_blocks) > 1:
                    if st.button(
                        "Remove",
                        key=(
                            "remove_context_block_"
                            f"{block_id}"
                        ),
                        use_container_width=True,
                    ):
                        runtime_context_blocks.pop(
                            index - 1
                        )
                        st.rerun()

            title_value = st.text_input(
                "Block title",
                value=str(
                    block.get(
                        "title",
                        "",
                    )
                    or ""
                ),
                placeholder=(
                    "Example: Docker runtime, "
                    "Temporal workflow, Swagger API"
                ),
                key=(
                    "context_block_title_"
                    f"{block_id}"
                ),
            )

            text_value = st.text_area(
                "Block notes",
                value=str(
                    block.get(
                        "text",
                        "",
                    )
                    or ""
                ),
                placeholder=(
                    "Explain what this screenshot shows "
                    "and why it matters for the project."
                ),
                height=140,
                key=(
                    "context_block_text_"
                    f"{block_id}"
                ),
            )

            block["title"] = title_value
            block["text"] = text_value

            paste_result = pbutton(
                label=(
                    "📋 Paste screenshot "
                    f"for block {index}"
                ),
                key=(
                    "paste_context_block_"
                    f"{block_id}"
                ),
                errors="raise",
            )

            if (
                paste_result is not None
                and paste_result.image_data is not None
            ):
                block["image_bytes"] = (
                    image_to_png_bytes(
                        paste_result.image_data
                    )
                )

                block["image_name"] = (
                    f"context_block_"
                    f"{index:03d}.png"
                )

                st.success(
                    "Screenshot pasted into this block."
                )

            image_bytes = block.get(
                "image_bytes"
            )

            if isinstance(
                image_bytes,
                bytes,
            ) and image_bytes:
                st.image(
                    image_bytes,
                    caption=(
                        block.get(
                            "image_name",
                            "Pasted screenshot",
                        )
                    ),
                    use_container_width=True,
                )

                if st.button(
                    "Remove screenshot",
                    key=(
                        "remove_context_image_"
                        f"{block_id}"
                    ),
                ):
                    block["image_bytes"] = None
                    block["image_name"] = None
                    st.rerun()

cleaned_project_path = project_path.strip()

inferred_project_name = (
    get_project_name_from_path(
        cleaned_project_path
    )
)

existing_documents: list[
    dict[str, Any]
] = []

history_error: str | None = None


# ============================================================
# Load existing documentation before synchronization
# ============================================================

if inferred_project_name:
    try:
        existing_documents = (
            get_document_history(
                api_url=api_url,
                project_name=(
                    inferred_project_name
                ),
            )
        )

    except requests.exceptions.ConnectionError:
        history_error = (
            "Could not connect to FastAPI. Make "
            "sure the backend is running."
        )

    except requests.exceptions.Timeout:
        history_error = (
            "Loading existing documentation "
            "timed out."
        )

    except requests.exceptions.RequestException as error:
        history_error = (
            f"Document history request failed: "
            f"{error}"
        )

    except RuntimeError as error:
        history_error = str(error)

    except Exception as error:
        history_error = (
            "Unexpected error while loading "
            f"document history: {error}"
        )


if not cleaned_project_path:
    st.warning(
        "Enter a project path to check its "
        "documentation."
    )

elif history_error:
    st.warning(
        history_error
    )

else:
    display_latest_document(
        api_url=api_url,
        project_name=inferred_project_name,
        documents=existing_documents,
    )

    display_document_history(
        api_url=api_url,
        project_name=inferred_project_name,
        documents=existing_documents,
    )


# ============================================================
# Create or update button
# ============================================================

st.divider()

with st.container(
    border=True,
):
    if existing_documents:
        st.subheader("Update documentation")

        st.write(
            "Scan the current project, compare it "
            "with the latest documented version, "
            "and create a new HTML version only "
            "when changes are found."
        )

        button_label = (
            "🔄 Update Documentation"
        )

    else:
        st.subheader("Create documentation")

        st.write(
            "Scan this project, generate its first "
            "LLM understanding, and create the "
            "initial HTML documentation."
        )

        button_label = (
            "🚀 Create Documentation"
        )

    submitted = st.button(
        button_label,
        type="primary",
        use_container_width=True,
        disabled=not bool(
            cleaned_project_path
        ),
    )


# ============================================================
# Handle synchronization request
# ============================================================

if submitted:
    if not cleaned_project_path:
        st.session_state.last_error = (
            "Please enter a project path."
        )

    else:
        st.session_state.last_project_path = (
            cleaned_project_path
        )

        st.session_state.last_error = None

        try:
            with st.spinner(
                    (
                    "Scanning the project, comparing "
                    "versions, processing runtime context, "
                    "calling the LLM when required, and "
                    "generating documentation..."
                    ),
                    show_time=True,
            ):
                has_runtime_context = (
                    context_blocks_have_content(
                        st.session_state.runtime_context_blocks
                    )
                )

                if has_runtime_context:
                    sync_result = (
                        sync_documentation_with_context(
                            api_url=api_url,
                            project_path=(
                                cleaned_project_path
                            ),
                            context_blocks=(
                                st.session_state
                                .runtime_context_blocks
                            ),
                        )
                    )

                else:
                    sync_result = (
                        sync_documentation(
                            api_url=api_url,
                            project_path=(
                                cleaned_project_path
                            ),
                        )
            )

            st.session_state.sync_result = (
                sync_result
            )

            st.session_state.history_refresh_counter += 1

            st.rerun()

        except requests.exceptions.ConnectionError:
            st.session_state.last_error = (
                "Could not connect to FastAPI. "
                "Make sure the backend is running "
                "at the configured URL."
            )

        except requests.exceptions.Timeout:
            st.session_state.last_error = (
                "The request timed out. The project "
                "scan or LLM operation took longer "
                "than expected."
            )

        except requests.exceptions.RequestException as error:
            st.session_state.last_error = (
                f"HTTP request failed: {error}"
            )

        except RuntimeError as error:
            st.session_state.last_error = str(
                error
            )

        except Exception as error:
            st.session_state.last_error = (
                "Unexpected UI error: "
                f"{error}"
            )


# ============================================================
# Display synchronization errors
# ============================================================

if st.session_state.last_error:
    st.error(
        st.session_state.last_error
    )

    st.markdown(
        """
        Confirm FastAPI is running:

        ```powershell
        uvicorn app.main:app --reload
        ```
        """
    )


# ============================================================
# Display latest synchronization result
# ============================================================

result = st.session_state.sync_result

if isinstance(result, dict):
    st.divider()

    st.header("Latest operation")

    display_action_status(
        result=result,
    )

    display_identifiers(
        result=result,
    )

    result_project_name = str(
        result.get(
            "project_name",
            "",
        )
    ).strip()

    result_document_id = str(
        result.get(
            "document_id",
            "",
        )
    ).strip()

    if (
        result_project_name
        and result_document_id
    ):
        result_document_url = (
            build_document_url(
                api_url=api_url,
                project_name=(
                    result_project_name
                ),
                document_id=(
                    result_document_id
                ),
            )
        )

        st.link_button(
            "📄 Open Resulting Documentation",
            url=result_document_url,
            type="primary",
            use_container_width=True,
        )

        st.caption(
            result_document_url
        )

    display_comparison_summary(
        result=result,
    )

    display_document_metadata(
        result=result,
    )