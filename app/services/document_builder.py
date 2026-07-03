from html import escape
from typing import Any


class DocumentBuilder:
    """
    Builds a standalone HTML documentation file
    from a saved project understanding.
    """

    def build_html(
        self,
        stored_understanding: dict[str, Any],
    ) -> str:
        project_name = str(
            stored_understanding.get(
                "project_name",
                "Unknown Project",
            )
        )

        understanding_id = str(
            stored_understanding.get(
                "understanding_id",
                "",
            )
        )

        scan_id = str(
            stored_understanding.get(
                "scan_id",
                "",
            )
        )

        provider = str(
            stored_understanding.get(
                "provider",
                "",
            )
        )

        model = str(
            stored_understanding.get(
                "model",
                "",
            )
        )

        created_at = str(
            stored_understanding.get(
                "created_at",
                "",
            )
        )

        understanding = (
            stored_understanding.get(
                "understanding",
                {},
            )
        )

        if not isinstance(
            understanding,
            dict,
        ):
            raise ValueError(
                "Stored understanding contains "
                "invalid understanding data."
            )

        project_summary = str(
            understanding.get(
                "project_summary",
                "No project summary available.",
            )
        )

        architecture_overview = str(
            understanding.get(
                "architecture_overview",
                (
                    "No architecture overview "
                    "available."
                ),
            )
        )

        execution_flow = understanding.get(
            "execution_flow",
            [],
        )

        module_responsibilities = (
            understanding.get(
                "module_responsibilities",
                [],
            )
        )

        api_overview = understanding.get(
            "api_overview",
            [],
        )

        key_dependencies = understanding.get(
            "key_dependencies",
            [],
        )

        risks_and_gaps = understanding.get(
            "risks_and_gaps",
            [],
        )

        recommended_sections = (
            understanding.get(
                "recommended_document_sections",
                [],
            )
        )

        navigation = self._build_navigation(
            execution_flow=execution_flow,
            module_responsibilities=(
                module_responsibilities
            ),
            api_overview=api_overview,
            key_dependencies=key_dependencies,
            risks_and_gaps=risks_and_gaps,
            recommended_sections=(
                recommended_sections
            ),
        )

        execution_html = (
            self._build_execution_flow(
                execution_flow
            )
        )

        modules_html = (
            self._build_module_responsibilities(
                module_responsibilities
            )
        )

        api_html = self._build_api_overview(
            api_overview
        )

        dependencies_html = (
            self._build_dependencies(
                key_dependencies
            )
        )

        risks_html = self._build_risks(
            risks_and_gaps
        )

        recommended_html = (
            self._build_recommended_sections(
                recommended_sections
            )
        )

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta
        name="viewport"
        content="width=device-width, initial-scale=1.0"
    >
    <title>{escape(project_name)} Documentation</title>

    <style>
        :root {{
            color-scheme: light dark;
            --background: #f4f6f8;
            --surface: #ffffff;
            --surface-soft: #f8fafc;
            --text: #172033;
            --muted: #5f6b7a;
            --border: #dce3ea;
            --primary: #2563eb;
            --primary-soft: #dbeafe;
            --danger: #b42318;
            --warning: #b54708;
            --success: #067647;
            --shadow: 0 12px 35px rgba(15, 23, 42, 0.08);
        }}

        * {{
            box-sizing: border-box;
        }}

        html {{
            scroll-behavior: smooth;
        }}

        body {{
            margin: 0;
            font-family:
                Inter,
                ui-sans-serif,
                system-ui,
                -apple-system,
                BlinkMacSystemFont,
                "Segoe UI",
                sans-serif;
            background: var(--background);
            color: var(--text);
            line-height: 1.65;
        }}

        .layout {{
            display: grid;
            grid-template-columns: 280px minmax(0, 1fr);
            min-height: 100vh;
        }}

        .sidebar {{
            position: sticky;
            top: 0;
            height: 100vh;
            overflow-y: auto;
            padding: 28px 22px;
            background: #111827;
            color: #ffffff;
        }}

        .sidebar h1 {{
            margin: 0 0 8px;
            font-size: 22px;
            line-height: 1.25;
        }}

        .sidebar p {{
            margin: 0 0 24px;
            color: #cbd5e1;
            font-size: 13px;
        }}

        .sidebar nav {{
            display: flex;
            flex-direction: column;
            gap: 6px;
        }}

        .sidebar a {{
            color: #e5e7eb;
            text-decoration: none;
            padding: 9px 11px;
            border-radius: 8px;
            font-size: 14px;
        }}

        .sidebar a:hover {{
            background: #1f2937;
            color: #ffffff;
        }}

        .content {{
            width: 100%;
            max-width: 1220px;
            padding: 48px;
        }}

        .hero {{
            padding: 38px;
            margin-bottom: 26px;
            border-radius: 18px;
            background:
                linear-gradient(
                    135deg,
                    #1d4ed8,
                    #4f46e5
                );
            color: #ffffff;
            box-shadow: var(--shadow);
        }}

        .hero h1 {{
            margin: 0 0 10px;
            font-size: 38px;
            line-height: 1.2;
        }}

        .hero p {{
            margin: 0;
            max-width: 760px;
            color: #dbeafe;
        }}

        .metadata {{
            display: grid;
            grid-template-columns:
                repeat(
                    auto-fit,
                    minmax(180px, 1fr)
                );
            gap: 12px;
            margin-top: 24px;
        }}

        .metadata div {{
            padding: 14px;
            border: 1px solid rgba(255, 255, 255, 0.18);
            border-radius: 12px;
            background: rgba(255, 255, 255, 0.10);
        }}

        .metadata span {{
            display: block;
            color: #bfdbfe;
            font-size: 12px;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }}

        .metadata strong {{
            display: block;
            margin-top: 4px;
            overflow-wrap: anywhere;
        }}

        section {{
            margin-bottom: 26px;
            padding: 30px;
            border: 1px solid var(--border);
            border-radius: 16px;
            background: var(--surface);
            box-shadow: var(--shadow);
        }}

        section h2 {{
            margin: 0 0 18px;
            font-size: 25px;
        }}

        .paragraph {{
            white-space: pre-line;
        }}

        .card-grid {{
            display: grid;
            grid-template-columns:
                repeat(
                    auto-fit,
                    minmax(280px, 1fr)
                );
            gap: 16px;
        }}

        .card {{
            padding: 20px;
            border: 1px solid var(--border);
            border-radius: 13px;
            background: var(--surface-soft);
        }}

        .card h3 {{
            margin: 0 0 10px;
            font-size: 18px;
        }}

        .card p {{
            margin: 8px 0;
        }}

        .label {{
            color: var(--muted);
            font-size: 12px;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }}

        .pill-list {{
            display: flex;
            flex-wrap: wrap;
            gap: 7px;
            margin-top: 12px;
        }}

        .pill {{
            display: inline-block;
            padding: 5px 9px;
            border-radius: 999px;
            background: var(--primary-soft);
            color: #1d4ed8;
            font-size: 12px;
            overflow-wrap: anywhere;
        }}

        .flow-step {{
            position: relative;
            padding: 20px 20px 20px 68px;
            margin-bottom: 14px;
            border: 1px solid var(--border);
            border-radius: 13px;
            background: var(--surface-soft);
        }}

        .step-number {{
            position: absolute;
            left: 18px;
            top: 20px;
            display: grid;
            place-items: center;
            width: 34px;
            height: 34px;
            border-radius: 50%;
            background: var(--primary);
            color: #ffffff;
            font-weight: 800;
        }}

        table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 14px;
        }}

        th,
        td {{
            padding: 13px;
            border-bottom: 1px solid var(--border);
            text-align: left;
            vertical-align: top;
        }}

        th {{
            background: var(--surface-soft);
        }}

        code {{
            padding: 2px 6px;
            border-radius: 6px;
            background: #eef2f7;
            color: #1e293b;
            overflow-wrap: anywhere;
        }}

        .severity {{
            display: inline-block;
            padding: 5px 9px;
            border-radius: 999px;
            font-size: 12px;
            font-weight: 800;
            text-transform: uppercase;
        }}

        .severity-high {{
            color: var(--danger);
            background: #fee4e2;
        }}

        .severity-medium {{
            color: var(--warning);
            background: #fef0c7;
        }}

        .severity-low {{
            color: var(--success);
            background: #d1fadf;
        }}

        .empty {{
            color: var(--muted);
            font-style: italic;
        }}

        footer {{
            padding: 8px 0 36px;
            color: var(--muted);
            text-align: center;
            font-size: 13px;
        }}

        @media (max-width: 900px) {{
            .layout {{
                display: block;
            }}

            .sidebar {{
                position: static;
                width: 100%;
                height: auto;
            }}

            .content {{
                padding: 24px;
            }}

            .hero {{
                padding: 26px;
            }}

            .hero h1 {{
                font-size: 30px;
            }}
        }}

        @media print {{
            .sidebar {{
                display: none;
            }}

            .layout {{
                display: block;
            }}

            .content {{
                max-width: none;
                padding: 0;
            }}

            section,
            .hero {{
                break-inside: avoid;
                box-shadow: none;
            }}
        }}
    </style>
</head>

<body>
    <div class="layout">
        <aside class="sidebar">
            <h1>{escape(project_name)}</h1>
            <p>Generated AutoDocX documentation</p>

            <nav>
                {navigation}
            </nav>
        </aside>

        <main class="content">
            <header class="hero">
                <h1>{escape(project_name)}</h1>

                <p>
                    Automatically generated project
                    documentation based on stored scan
                    analysis and LLM project understanding.
                </p>

                <div class="metadata">
                    <div>
                        <span>Understanding ID</span>
                        <strong>
                            {escape(understanding_id)}
                        </strong>
                    </div>

                    <div>
                        <span>Scan ID</span>
                        <strong>
                            {escape(scan_id)}
                        </strong>
                    </div>

                    <div>
                        <span>Provider</span>
                        <strong>
                            {escape(provider)}
                        </strong>
                    </div>

                    <div>
                        <span>Model</span>
                        <strong>
                            {escape(model)}
                        </strong>
                    </div>

                    <div>
                        <span>Understanding created</span>
                        <strong>
                            {escape(created_at)}
                        </strong>
                    </div>
                </div>
            </header>

            <section id="summary">
                <h2>Project Summary</h2>

                <div class="paragraph">
                    {escape(project_summary)}
                </div>
            </section>

            <section id="architecture">
                <h2>Architecture Overview</h2>

                <div class="paragraph">
                    {escape(architecture_overview)}
                </div>
            </section>

            <section id="execution-flow">
                <h2>Execution Flow</h2>
                {execution_html}
            </section>

            <section id="modules">
                <h2>Module Responsibilities</h2>
                {modules_html}
            </section>

            <section id="api">
                <h2>API Overview</h2>
                {api_html}
            </section>

            <section id="dependencies">
                <h2>Key Dependencies</h2>
                {dependencies_html}
            </section>

            <section id="risks">
                <h2>Risks and Gaps</h2>
                {risks_html}
            </section>

            <section id="recommended-sections">
                <h2>
                    Recommended Documentation Sections
                </h2>

                {recommended_html}
            </section>

            <footer>
                Generated by AutoDocX from understanding
                {escape(understanding_id)}
            </footer>
        </main>
    </div>
</body>
</html>
"""

    @staticmethod
    def _build_navigation(
        execution_flow: Any,
        module_responsibilities: Any,
        api_overview: Any,
        key_dependencies: Any,
        risks_and_gaps: Any,
        recommended_sections: Any,
    ) -> str:
        links = [
            (
                "summary",
                "Project Summary",
                True,
            ),
            (
                "architecture",
                "Architecture Overview",
                True,
            ),
            (
                "execution-flow",
                "Execution Flow",
                bool(execution_flow),
            ),
            (
                "modules",
                "Module Responsibilities",
                bool(module_responsibilities),
            ),
            (
                "api",
                "API Overview",
                bool(api_overview),
            ),
            (
                "dependencies",
                "Key Dependencies",
                bool(key_dependencies),
            ),
            (
                "risks",
                "Risks and Gaps",
                bool(risks_and_gaps),
            ),
            (
                "recommended-sections",
                "Recommended Sections",
                bool(recommended_sections),
            ),
        ]

        return "\n".join(
            (
                f'<a href="#{section_id}">'
                f"{escape(title)}</a>"
            )
            for section_id, title, enabled in links
            if enabled
        )

    @staticmethod
    def _build_execution_flow(
        execution_flow: Any,
    ) -> str:
        if not isinstance(
            execution_flow,
            list,
        ) or not execution_flow:
            return (
                '<p class="empty">'
                "No execution flow available."
                "</p>"
            )

        cards: list[str] = []

        for index, item in enumerate(
            execution_flow,
            start=1,
        ):
            if not isinstance(item, dict):
                continue

            step = item.get(
                "step",
                index,
            )

            title = str(
                item.get(
                    "title",
                    f"Step {step}",
                )
            )

            description = str(
                item.get(
                    "description",
                    "",
                )
            )

            related_modules = item.get(
                "related_modules",
                [],
            )

            pills = (
                DocumentBuilder._build_pills(
                    related_modules
                )
            )

            cards.append(
                f"""
                <article class="flow-step">
                    <div class="step-number">
                        {escape(str(step))}
                    </div>

                    <h3>{escape(title)}</h3>

                    <p>
                        {escape(description)}
                    </p>

                    {pills}
                </article>
                """
            )

        return "\n".join(cards)

    @staticmethod
    def _build_module_responsibilities(
        modules: Any,
    ) -> str:
        if not isinstance(
            modules,
            list,
        ) or not modules:
            return (
                '<p class="empty">'
                "No module responsibilities available."
                "</p>"
            )

        cards: list[str] = []

        for module in modules:
            if not isinstance(module, dict):
                continue

            module_name = str(
                module.get(
                    "module",
                    "Unknown module",
                )
            )

            file_path = str(
                module.get(
                    "file",
                    "",
                )
            )

            responsibility = str(
                module.get(
                    "responsibility",
                    "",
                )
            )

            symbols = module.get(
                "important_symbols",
                [],
            )

            cards.append(
                f"""
                <article class="card">
                    <h3>{escape(module_name)}</h3>

                    <p class="label">File</p>
                    <p>
                        <code>
                            {escape(file_path)}
                        </code>
                    </p>

                    <p class="label">
                        Responsibility
                    </p>

                    <p>
                        {escape(responsibility)}
                    </p>

                    <p class="label">
                        Important symbols
                    </p>

                    {
                        DocumentBuilder
                        ._build_pills(symbols)
                    }
                </article>
                """
            )

        if not cards:
            return (
                '<p class="empty">'
                "No module responsibilities available."
                "</p>"
            )

        return (
            '<div class="card-grid">'
            + "\n".join(cards)
            + "</div>"
        )

    @staticmethod
    def _build_api_overview(
        api_overview: Any,
    ) -> str:
        if not isinstance(
            api_overview,
            list,
        ) or not api_overview:
            return (
                '<p class="empty">'
                "No API information available."
                "</p>"
            )

        rows: list[str] = []

        for endpoint in api_overview:
            if not isinstance(endpoint, dict):
                continue

            method = str(
                endpoint.get(
                    "method",
                    "",
                )
            )

            path = str(
                endpoint.get(
                    "path",
                    "",
                )
            )

            handler = str(
                endpoint.get(
                    "handler",
                    "",
                )
            )

            purpose = str(
                endpoint.get(
                    "purpose",
                    "",
                )
            )

            rows.append(
                f"""
                <tr>
                    <td>
                        <strong>
                            {escape(method)}
                        </strong>
                    </td>

                    <td>
                        <code>
                            {escape(path)}
                        </code>
                    </td>

                    <td>
                        <code>
                            {escape(handler)}
                        </code>
                    </td>

                    <td>
                        {escape(purpose)}
                    </td>
                </tr>
                """
            )

        if not rows:
            return (
                '<p class="empty">'
                "No API information available."
                "</p>"
            )

        return f"""
        <div style="overflow-x: auto;">
            <table>
                <thead>
                    <tr>
                        <th>Method</th>
                        <th>Path</th>
                        <th>Handler</th>
                        <th>Purpose</th>
                    </tr>
                </thead>

                <tbody>
                    {"".join(rows)}
                </tbody>
            </table>
        </div>
        """

    @staticmethod
    def _build_dependencies(
        dependencies: Any,
    ) -> str:
        if not isinstance(
            dependencies,
            list,
        ) or not dependencies:
            return (
                '<p class="empty">'
                "No dependency information available."
                "</p>"
            )

        cards: list[str] = []

        for dependency in dependencies:
            if not isinstance(
                dependency,
                dict,
            ):
                continue

            source = str(
                dependency.get(
                    "source",
                    "",
                )
            )

            target = str(
                dependency.get(
                    "target",
                    "",
                )
            )

            purpose = str(
                dependency.get(
                    "purpose",
                    "",
                )
            )

            cards.append(
                f"""
                <article class="card">
                    <h3>
                        {escape(source)}
                        &rarr;
                        {escape(target)}
                    </h3>

                    <p>
                        {escape(purpose)}
                    </p>
                </article>
                """
            )

        return (
            '<div class="card-grid">'
            + "\n".join(cards)
            + "</div>"
        )

    @staticmethod
    def _build_risks(
        risks: Any,
    ) -> str:
        if not isinstance(
            risks,
            list,
        ) or not risks:
            return (
                '<p class="empty">'
                "No risks or gaps available."
                "</p>"
            )

        cards: list[str] = []

        for risk in risks:
            if not isinstance(risk, dict):
                continue

            title = str(
                risk.get(
                    "title",
                    "Untitled risk",
                )
            )

            description = str(
                risk.get(
                    "description",
                    "",
                )
            )

            severity = str(
                risk.get(
                    "severity",
                    "low",
                )
            ).lower()

            if severity not in {
                "high",
                "medium",
                "low",
            }:
                severity = "low"

            cards.append(
                f"""
                <article class="card">
                    <span
                        class="
                            severity
                            severity-{escape(severity)}
                        "
                    >
                        {escape(severity)}
                    </span>

                    <h3>{escape(title)}</h3>

                    <p>
                        {escape(description)}
                    </p>
                </article>
                """
            )

        return (
            '<div class="card-grid">'
            + "\n".join(cards)
            + "</div>"
        )

    @staticmethod
    def _build_recommended_sections(
        sections: Any,
    ) -> str:
        if not isinstance(
            sections,
            list,
        ) or not sections:
            return (
                '<p class="empty">'
                "No recommended sections available."
                "</p>"
            )

        cards: list[str] = []

        for section in sections:
            if not isinstance(section, dict):
                continue

            title = str(
                section.get(
                    "title",
                    "Untitled section",
                )
            )

            purpose = str(
                section.get(
                    "purpose",
                    "",
                )
            )

            cards.append(
                f"""
                <article class="card">
                    <h3>{escape(title)}</h3>

                    <p>
                        {escape(purpose)}
                    </p>
                </article>
                """
            )

        return (
            '<div class="card-grid">'
            + "\n".join(cards)
            + "</div>"
        )

    @staticmethod
    def _build_pills(
        values: Any,
    ) -> str:
        if not isinstance(
            values,
            list,
        ) or not values:
            return (
                '<p class="empty">'
                "None listed."
                "</p>"
            )

        pills = "".join(
            (
                '<span class="pill">'
                f"{escape(str(value))}"
                "</span>"
            )
            for value in values
        )

        return (
            '<div class="pill-list">'
            + pills
            + "</div>"
        )