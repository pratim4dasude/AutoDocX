from pathlib import PureWindowsPath
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
HISTORY_TIMEOUT_SECONDS = 60


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

        `http://127.0.0.1:8000`

        **Streamlit**

        `http://localhost:8501`
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
                    "versions, calling the LLM when "
                    "required, and generating "
                    "documentation..."
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