from typing import Any
from urllib.parse import quote

import requests
import streamlit as st


# ============================================================
# Application configuration
# ============================================================

DEFAULT_API_URL = "http://127.0.0.1:8000"

DEFAULT_PROJECT_PATH = (
    r"C:\Users\PratimMangaldasDasud"
    r"\PycharmProjects\AutoDocX"
)

SYNC_ENDPOINT = "/api/projects/documentation/sync"

REQUEST_TIMEOUT_SECONDS = 900


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
# Helper functions
# ============================================================

def normalize_api_url(
    api_url: str,
) -> str:
    """
    Remove trailing slashes from the configured
    FastAPI base URL.
    """

    return api_url.strip().rstrip("/")


def build_document_url(
    api_url: str,
    project_name: str,
    document_id: str,
) -> str:
    """
    Build the FastAPI URL used to open the generated
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


def sync_documentation(
    api_url: str,
    project_path: str,
) -> dict[str, Any]:
    """
    Call the complete AutoDocX documentation
    synchronization endpoint.
    """

    normalized_api_url = normalize_api_url(
        api_url
    )

    endpoint_url = (
        f"{normalized_api_url}"
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

    try:
        response_data = response.json()
    except requests.exceptions.JSONDecodeError:
        response_data = {
            "detail": response.text
            or "The backend returned a non-JSON response."
        }

    if not response.ok:
        detail = response_data.get(
            "detail",
            (
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
            "The backend returned an invalid response."
        )

    return response_data


def display_action_status(
    result: dict[str, Any],
) -> None:
    """
    Display the created, updated, or unchanged
    result returned by FastAPI.
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
            "Initial documentation created successfully."
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
    Display the generated scan, understanding,
    and document identifiers.
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
        "previous_document_id",
    )

    st.subheader("Generated result")

    column_1, column_2 = st.columns(2)

    with column_1:
        st.text_input(
            "Project name",
            value=str(project_name),
            disabled=True,
        )

        st.text_input(
            "Scan ID",
            value=str(scan_id),
            disabled=True,
        )

    with column_2:
        st.text_input(
            "Document ID",
            value=str(document_id),
            disabled=True,
        )

        st.text_input(
            "Understanding ID",
            value=str(understanding_id),
            disabled=True,
        )

    if previous_document_id:
        st.text_input(
            "Previous document ID",
            value=str(previous_document_id),
            disabled=True,
        )


def display_comparison_summary(
    result: dict[str, Any],
) -> None:
    """
    Display scan comparison metrics when the
    backend returns them.
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

    row_1 = st.columns(4)

    row_1[0].metric(
        "Total changes",
        comparison_summary.get(
            "total_changes",
            0,
        ),
    )

    row_1[1].metric(
        "Added files",
        comparison_summary.get(
            "added_files",
            0,
        ),
    )

    row_1[2].metric(
        "Modified files",
        comparison_summary.get(
            "modified_files",
            0,
        ),
    )

    row_1[3].metric(
        "Deleted files",
        comparison_summary.get(
            "deleted_files",
            0,
        ),
    )

    row_2 = st.columns(4)

    row_2[0].metric(
        "Added symbols",
        comparison_summary.get(
            "added_symbols",
            0,
        ),
    )

    row_2[1].metric(
        "Modified symbols",
        comparison_summary.get(
            "modified_symbols",
            0,
        ),
    )

    row_2[2].metric(
        "Added routes",
        comparison_summary.get(
            "added_routes",
            0,
        ),
    )

    row_2[3].metric(
        "Added dependencies",
        comparison_summary.get(
            "added_dependencies",
            0,
        ),
    )

    with st.expander(
        "View complete comparison summary"
    ):
        st.json(comparison_summary)


def display_document_metadata(
    result: dict[str, Any],
) -> None:
    """
    Display complete document metadata in a
    collapsible section.
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
        "View document metadata"
    ):
        st.json(document)


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

        `http://127.0.0.1:8000`

        **Streamlit**

        `http://localhost:8501`
        """
    )

    st.divider()

    if st.button(
        "Clear current result",
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
        Scan a project and automatically create,
        update, or reuse its documentation.
    </div>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# Documentation generation form
# ============================================================

with st.container(
    border=True,
):
    st.subheader(
        "Create or update documentation"
    )

    st.write(
        "Enter the absolute local path of the "
        "project that AutoDocX should process."
    )

    with st.form(
        key="documentation_sync_form",
    ):
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
        )

        submitted = st.form_submit_button(
            "Create or Update Documentation",
            type="primary",
            use_container_width=True,
        )


# ============================================================
# Handle request
# ============================================================

if submitted:
    cleaned_project_path = (
        project_path.strip()
    )

    if not cleaned_project_path:
        st.error(
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
                    "versions, calling the LLM, and "
                    "generating documentation..."
                ),
                show_time=True,
            ):
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
# Display errors
# ============================================================

if st.session_state.last_error:
    st.error(
        st.session_state.last_error
    )

    st.markdown(
        """
        Check that FastAPI is running:

        ```powershell
        uvicorn app.main:app --reload
        ```
        """
    )


# ============================================================
# Display API result
# ============================================================

result = st.session_state.sync_result

if isinstance(result, dict):
    st.divider()

    display_action_status(
        result=result,
    )

    display_identifiers(
        result=result,
    )

    project_name = str(
        result.get(
            "project_name",
            "",
        )
    ).strip()

    document_id = str(
        result.get(
            "document_id",
            "",
        )
    ).strip()

    if project_name and document_id:
        document_url = build_document_url(
            api_url=api_url,
            project_name=project_name,
            document_id=document_id,
        )

        st.link_button(
            "Open Generated Documentation",
            url=document_url,
            type="primary",
            use_container_width=True,
        )

        st.caption(
            document_url
        )

    display_comparison_summary(
        result=result,
    )

    display_document_metadata(
        result=result,
    )