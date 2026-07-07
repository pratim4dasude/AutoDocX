from html import escape
from typing import Any


class DocumentBuilder:
    """
    Builds a standalone professional developer documentation HTML
    from a saved project understanding.

    The output is closer to developer documentation pages:
    - left navigation
    - main article content
    - right table of contents
    - API reference cards
    - parameter tables
    - module reference cards
    - class/function/method signatures
    - code examples
    - clean callouts
    """

    def build_html(
            self,
            stored_understanding: dict[str, Any],
            runtime_context: dict[str, Any] | None = None,
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

        understanding = stored_understanding.get(
            "understanding",
            {},
        )

        if not isinstance(understanding, dict):
            raise ValueError(
                "Stored understanding contains invalid understanding data."
            )

        project_summary = self._clean_llm_text(
            str(
                understanding.get(
                    "project_summary",
                    "No project summary available.",
                )
            )
        )

        architecture_overview = self._clean_llm_text(
            str(
                understanding.get(
                    "architecture_overview",
                    "No architecture overview available.",
                )
            )
        )

        execution_flow = understanding.get(
            "execution_flow",
            [],
        )

        module_responsibilities = understanding.get(
            "module_responsibilities",
            [],
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

        developer_reference = understanding.get(
            "developer_reference",
            {},
        )

        statistics = {}

        if isinstance(developer_reference, dict):
            statistics = developer_reference.get(
                "statistics",
                {},
            )

        navigation = self._build_left_navigation(
            api_overview=api_overview,
            module_responsibilities=module_responsibilities,
        )

        right_toc = self._build_right_toc(
            api_overview=api_overview,
            module_responsibilities=module_responsibilities,
            risks_and_gaps=risks_and_gaps,
            statistics=statistics,
        )

        quickstart_html = self._build_quickstart(
            project_name=project_name,
        )

        statistics_html = self._build_statistics(
            statistics,
        )

        api_reference_html = self._build_api_reference(
            api_overview,
        )

        modules_html = self._build_module_reference(
            module_responsibilities,
        )

        execution_html = self._build_execution_flow(
            execution_flow,
        )

        dependencies_html = self._build_dependencies(
            key_dependencies,
        )

        troubleshooting_html = self._build_troubleshooting(
            risks_and_gaps,
        )

        runtime_context_html = self._build_runtime_context(
            runtime_context=runtime_context,
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
            color-scheme: dark;
            --bg: #0b0f19;
            --bg-soft: #0f172a;
            --sidebar: #080d18;
            --surface: #101827;
            --surface-soft: #111d31;
            --surface-muted: #172033;
            --border: #233047;
            --border-soft: #1b2638;
            --text: #e5e7eb;
            --text-strong: #f8fafc;
            --muted: #94a3b8;
            --muted-soft: #64748b;
            --primary: #8b5cf6;
            --primary-soft: rgba(139, 92, 246, 0.16);
            --blue: #60a5fa;
            --green: #34d399;
            --yellow: #fbbf24;
            --red: #fb7185;
            --code-bg: #0b1220;
            --shadow: 0 24px 70px rgba(0, 0, 0, 0.35);
        }}

        * {{
            box-sizing: border-box;
        }}

        html {{
            scroll-behavior: smooth;
        }}

        body {{
            margin: 0;
            background: var(--bg);
            color: var(--text);
            font-family:
                Inter,
                ui-sans-serif,
                system-ui,
                -apple-system,
                BlinkMacSystemFont,
                "Segoe UI",
                sans-serif;
            line-height: 1.7;
        }}

        a {{
            color: inherit;
        }}

        .shell {{
            display: grid;
            grid-template-columns: 300px minmax(0, 1fr) 280px;
            min-height: 100vh;
        }}

        .left-sidebar {{
            position: sticky;
            top: 0;
            height: 100vh;
            overflow-y: auto;
            border-right: 1px solid var(--border-soft);
            background: var(--sidebar);
            padding: 24px 18px;
        }}

        .brand {{
            display: flex;
            align-items: center;
            gap: 10px;
            margin-bottom: 22px;
            padding: 0 8px;
        }}

        .brand-mark {{
            width: 14px;
            height: 14px;
            border-radius: 4px;
            background: linear-gradient(
                135deg,
                var(--primary),
                var(--blue)
            );
            box-shadow: 0 0 30px rgba(139, 92, 246, 0.75);
        }}

        .brand h1 {{
            margin: 0;
            color: var(--text-strong);
            font-size: 19px;
            letter-spacing: -0.02em;
        }}

        .search-box {{
            margin: 0 8px 24px;
            padding: 10px 12px;
            border: 1px solid var(--border);
            border-radius: 10px;
            background: #070c16;
            color: var(--muted);
            font-size: 13px;
        }}

        .nav-group {{
            margin-bottom: 24px;
        }}

        .nav-title {{
            margin: 0 8px 8px;
            color: var(--muted-soft);
            font-size: 11px;
            font-weight: 800;
            text-transform: uppercase;
            letter-spacing: 0.08em;
        }}

        .left-sidebar nav a {{
            display: block;
            padding: 8px 10px;
            border-radius: 9px;
            color: #cbd5e1;
            text-decoration: none;
            font-size: 14px;
        }}

        .left-sidebar nav a:hover {{
            background: var(--surface-muted);
            color: var(--text-strong);
        }}

        .main {{
            min-width: 0;
            padding: 58px 64px 80px;
        }}

        .article {{
            max-width: 960px;
            margin: 0 auto;
        }}

        .eyebrow {{
            display: inline-flex;
            align-items: center;
            gap: 8px;
            margin-bottom: 18px;
            padding: 5px 10px;
            border: 1px solid var(--border);
            border-radius: 999px;
            background: var(--primary-soft);
            color: #ddd6fe;
            font-size: 12px;
            font-weight: 700;
        }}

        .page-title {{
            margin: 0 0 18px;
            color: var(--text-strong);
            font-size: 44px;
            line-height: 1.1;
            letter-spacing: -0.04em;
        }}

        .lead {{
            max-width: 780px;
            margin: 0 0 30px;
            color: #cbd5e1;
            font-size: 18px;
        }}

        .meta-strip {{
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
            margin-bottom: 42px;
        }}

        .meta-chip {{
            display: inline-flex;
            gap: 6px;
            align-items: center;
            padding: 7px 10px;
            border: 1px solid var(--border);
            border-radius: 999px;
            background: var(--surface);
            color: var(--muted);
            font-size: 12px;
        }}

        .meta-chip strong {{
            color: var(--text);
            font-weight: 700;
            overflow-wrap: anywhere;
        }}

        .doc-section {{
            padding-top: 30px;
            margin-top: 38px;
            border-top: 1px solid var(--border-soft);
        }}

        .doc-section h2 {{
            margin: 0 0 14px;
            color: var(--text-strong);
            font-size: 28px;
            line-height: 1.25;
            letter-spacing: -0.03em;
        }}

        .doc-section h3 {{
            margin: 28px 0 10px;
            color: var(--text-strong);
            font-size: 20px;
            letter-spacing: -0.02em;
        }}

        .paragraph {{
            white-space: pre-line;
            color: #cbd5e1;
        }}

        .callout {{
            margin: 22px 0;
            padding: 18px 20px;
            border-left: 4px solid var(--green);
            border-radius: 12px;
            background: rgba(52, 211, 153, 0.09);
            color: #d1fae5;
        }}

        .callout.warning {{
            border-left-color: var(--yellow);
            background: rgba(251, 191, 36, 0.09);
            color: #fef3c7;
        }}


        .stats-grid {{
            display: grid;
            grid-template-columns:
                repeat(
                    auto-fit,
                    minmax(150px, 1fr)
                );
            gap: 12px;
            margin-top: 18px;
        }}

        .stat-card {{
            padding: 16px;
            border: 1px solid var(--border);
            border-radius: 14px;
            background: var(--surface);
        }}

        .stat-card span {{
            display: block;
            color: var(--muted-soft);
            font-size: 11px;
            font-weight: 900;
            text-transform: uppercase;
            letter-spacing: 0.08em;
        }}

        .stat-card strong {{
            display: block;
            margin-top: 4px;
            color: var(--text-strong);
            font-size: 22px;
        }}

        .reference-card {{
            margin: 22px 0;
            border: 1px solid var(--border);
            border-radius: 16px;
            background: var(--surface);
            overflow: hidden;
            box-shadow: var(--shadow);
        }}

        .reference-header {{
            padding: 16px 18px;
            border-bottom: 1px solid var(--border);
            background: linear-gradient(
                180deg,
                var(--surface-soft),
                var(--surface)
            );
        }}

        .reference-header h3 {{
            margin: 0;
            font-size: 18px;
        }}

        .reference-header p {{
            margin: 8px 0 0;
            color: var(--muted);
            font-size: 14px;
        }}

        .reference-body {{
            padding: 18px;
        }}

        .signature {{
            display: block;
            margin: 12px 0 0;
            padding: 14px 16px;
            border: 1px solid var(--border);
            border-radius: 12px;
            background: var(--code-bg);
            color: #dbeafe;
            font-family:
                "JetBrains Mono",
                "SFMono-Regular",
                Consolas,
                "Liberation Mono",
                monospace;
            font-size: 13px;
            line-height: 1.65;
            overflow-x: auto;
            white-space: pre;
        }}

        .code-block {{
            position: relative;
            margin: 18px 0;
            border: 1px solid var(--border);
            border-radius: 14px;
            background: var(--code-bg);
            overflow: hidden;
        }}

        .code-title {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 10px 14px;
            border-bottom: 1px solid var(--border);
            background: #0f172a;
            color: var(--muted);
            font-size: 12px;
            font-weight: 700;
        }}

        pre {{
            margin: 0;
            padding: 18px;
            overflow-x: auto;
        }}

        code {{
            font-family:
                "JetBrains Mono",
                "SFMono-Regular",
                Consolas,
                "Liberation Mono",
                monospace;
            font-size: 13px;
        }}

        p code,
        li code,
        td code {{
            padding: 2px 6px;
            border: 1px solid var(--border);
            border-radius: 6px;
            background: #111827;
            color: #bfdbfe;
            overflow-wrap: anywhere;
        }}

        .endpoint {{
            display: grid;
            grid-template-columns: 78px minmax(0, 1fr);
            gap: 12px;
            align-items: start;
        }}

        .method {{
            display: inline-flex;
            justify-content: center;
            min-width: 68px;
            padding: 5px 8px;
            border-radius: 999px;
            font-size: 12px;
            font-weight: 900;
            letter-spacing: 0.04em;
        }}

        .method-get {{
            background: rgba(52, 211, 153, 0.12);
            color: var(--green);
        }}

        .method-post {{
            background: rgba(96, 165, 250, 0.14);
            color: var(--blue);
        }}

        .method-put,
        .method-patch {{
            background: rgba(251, 191, 36, 0.14);
            color: var(--yellow);
        }}

        .method-delete {{
            background: rgba(251, 113, 133, 0.14);
            color: var(--red);
        }}

        .path {{
            color: var(--text-strong);
            font-family:
                "JetBrains Mono",
                "SFMono-Regular",
                Consolas,
                monospace;
            font-size: 14px;
            overflow-wrap: anywhere;
        }}

        .small-label {{
            margin: 18px 0 8px;
            color: var(--muted-soft);
            font-size: 11px;
            font-weight: 900;
            text-transform: uppercase;
            letter-spacing: 0.08em;
        }}

        .sub-reference {{
            margin: 14px 0;
            padding: 14px;
            border: 1px solid var(--border);
            border-radius: 14px;
            background: #0d1525;
        }}

        .sub-reference h4 {{
            margin: 0 0 8px;
            color: var(--text-strong);
            font-size: 15px;
        }}

        .sub-reference p {{
            margin: 8px 0 0;
            color: #cbd5e1;
            font-size: 14px;
        }}

        .pill-list {{
            display: flex;
            flex-wrap: wrap;
            gap: 7px;
            margin-top: 10px;
        }}

        .pill {{
            display: inline-flex;
            align-items: center;
            padding: 5px 9px;
            border: 1px solid var(--border);
            border-radius: 999px;
            background: #101827;
            color: #c4b5fd;
            font-size: 12px;
            overflow-wrap: anywhere;
        }}

        .table-wrap {{
            overflow-x: auto;
            border: 1px solid var(--border);
            border-radius: 14px;
            margin: 12px 0;
        }}

        table {{
            width: 100%;
            border-collapse: collapse;
            min-width: 680px;
            font-size: 14px;
        }}

        th,
        td {{
            padding: 12px 14px;
            border-bottom: 1px solid var(--border);
            text-align: left;
            vertical-align: top;
        }}

        tr:last-child td {{
            border-bottom: 0;
        }}

        th {{
            background: var(--surface-soft);
            color: var(--text-strong);
            font-size: 12px;
            text-transform: uppercase;
            letter-spacing: 0.06em;
        }}

        td {{
            color: #cbd5e1;
        }}

        .flow-list {{
            display: grid;
            gap: 12px;
        }}

        .flow-step {{
            display: grid;
            grid-template-columns: 38px minmax(0, 1fr);
            gap: 14px;
            padding: 16px;
            border: 1px solid var(--border);
            border-radius: 14px;
            background: var(--surface);
        }}

        .step-number {{
            display: grid;
            place-items: center;
            width: 32px;
            height: 32px;
            border-radius: 50%;
            background: var(--primary-soft);
            color: #c4b5fd;
            font-weight: 900;
        }}

        .flow-step h3 {{
            margin: 0 0 6px;
            font-size: 16px;
        }}

        .flow-step p {{
            margin: 0;
            color: #cbd5e1;
        }}

        .severity {{
            display: inline-flex;
            padding: 4px 8px;
            border-radius: 999px;
            font-size: 11px;
            font-weight: 900;
            text-transform: uppercase;
        }}

        .severity-high {{
            background: rgba(251, 113, 133, 0.14);
            color: var(--red);
        }}

        .severity-medium {{
            background: rgba(251, 191, 36, 0.14);
            color: var(--yellow);
        }}

        .severity-low {{
            background: rgba(52, 211, 153, 0.12);
            color: var(--green);
        }}

        .dependency-grid,
        .risk-grid {{
            display: grid;
            grid-template-columns:
                repeat(
                    auto-fit,
                    minmax(260px, 1fr)
                );
            gap: 14px;
        }}

        .mini-card {{
            padding: 16px;
            border: 1px solid var(--border);
            border-radius: 14px;
            background: var(--surface);
        }}

        .mini-card h3 {{
            margin: 0 0 8px;
            font-size: 16px;
        }}

        .mini-card p {{
            margin: 0;
            color: #cbd5e1;
            font-size: 14px;
        }}
        
                .runtime-context-card {{
            margin: 22px 0;
            padding: 18px 20px;
            border: 1px solid var(--border);
            border-radius: 16px;
            background: var(--surface);
        }}

        .runtime-context-card h3 {{
            margin: 0 0 10px;
            color: var(--text-strong);
            font-size: 18px;
        }}

        .runtime-notes {{
            white-space: pre-line;
            color: #cbd5e1;
            font-size: 15px;
        }}

        .screenshot-grid {{
            display: grid;
            grid-template-columns:
                repeat(
                    auto-fit,
                    minmax(280px, 1fr)
                );
            gap: 16px;
            margin-top: 18px;
        }}

        .screenshot-card {{
            border: 1px solid var(--border);
            border-radius: 14px;
            background: #0d1525;
            overflow: hidden;
        }}

        .screenshot-card img {{
            width: 100%;
            display: block;
            border-bottom: 1px solid var(--border);
        }}

        .screenshot-caption {{
            padding: 12px 14px;
            color: var(--muted);
            font-size: 13px;
        }}

        .screenshot-caption strong {{
            display: block;
            color: var(--text-strong);
            margin-bottom: 4px;
            font-size: 14px;
        }}
        
        

        .right-toc {{
            position: sticky;
            top: 0;
            height: 100vh;
            overflow-y: auto;
            border-left: 1px solid var(--border-soft);
            background: var(--bg);
            padding: 72px 22px 24px;
        }}

        .right-toc h2 {{
            margin: 0 0 12px;
            color: var(--text-strong);
            font-size: 13px;
            text-transform: uppercase;
            letter-spacing: 0.08em;
        }}

        .right-toc a {{
            display: block;
            padding: 6px 0;
            color: var(--muted);
            text-decoration: none;
            font-size: 13px;
        }}

        .right-toc a:hover {{
            color: var(--text-strong);
        }}

        .empty {{
            color: var(--muted);
            font-style: italic;
        }}

        footer {{
            margin-top: 60px;
            padding-top: 24px;
            border-top: 1px solid var(--border-soft);
            color: var(--muted-soft);
            font-size: 13px;
        }}

        @media (max-width: 1180px) {{
            .shell {{
                grid-template-columns: 280px minmax(0, 1fr);
            }}

            .right-toc {{
                display: none;
            }}
        }}

        @media (max-width: 860px) {{
            .shell {{
                display: block;
            }}

            .left-sidebar {{
                position: static;
                height: auto;
            }}

            .main {{
                padding: 34px 22px 60px;
            }}

            .page-title {{
                font-size: 34px;
            }}

            .lead {{
                font-size: 16px;
            }}
        }}

        @media print {{
            .left-sidebar,
            .right-toc {{
                display: none;
            }}

            .shell {{
                display: block;
            }}

            .main {{
                padding: 0;
            }}

            .article {{
                max-width: none;
            }}

            .reference-card,
            .mini-card,
            .flow-step,
            .sub-reference {{
                break-inside: avoid;
                box-shadow: none;
            }}
        }}
    </style>
</head>

<body>
    <div class="shell">
        <aside class="left-sidebar">
            <div class="brand">
                <span class="brand-mark"></span>
                <h1>{escape(project_name)}</h1>
            </div>

            <div class="search-box">
                Developer reference
            </div>

            {navigation}
        </aside>

        <main class="main">
            <article class="article">
                <span class="eyebrow">
                    Auto-generated developer documentation
                </span>

                <h1 class="page-title">
                    {escape(project_name)}
                </h1>

                <p class="lead">
                    Developer-focused documentation generated from
                    project scan data and code structure. Use this page
                    to understand the project, inspect APIs, review
                    modules, and see class/function signatures.
                </p>

                <div class="meta-strip">
                    {self._build_meta_chip("Provider", provider)}
                    {self._build_meta_chip("Model", model)}
                    {self._build_meta_chip("Scan", scan_id)}
                    {self._build_meta_chip("Understanding", understanding_id)}
                    {self._build_meta_chip("Created", created_at)}
                </div>

                <section
                    id="overview"
                    class="doc-section"
                >
                    <h2>Overview</h2>

                    <div class="paragraph">
                        {escape(project_summary)}
                    </div>

                    <div class="callout">
                        API paths, handlers, signatures, parameters,
                        classes, and methods are taken from parser data
                        where available, not guessed by the LLM.
                    </div>
                </section>

                <section
                    id="quickstart"
                    class="doc-section"
                >
                    <h2>Quickstart</h2>

                    {quickstart_html}
                </section>

                <section
                    id="project-statistics"
                    class="doc-section"
                >
                    <h2>Project Statistics</h2>

                    {statistics_html}
                </section>




                <section
                    id="architecture"
                    class="doc-section"
                >
                    <h2>Architecture</h2>

                    <div class="paragraph">
                        {escape(architecture_overview)}
                    </div>
                </section>
                
                <section
                    id="runtime-tooling-context"
                    class="doc-section"
                >
                    <h2>Runtime and Tooling Context</h2>
                
                    {runtime_context_html}
                </section>
                
                





                <section
                    id="api-reference"
                    class="doc-section"
                >
                    <h2>API Reference</h2>

                    <p>
                        The following endpoints were discovered from
                        FastAPI route decorators and router inclusion
                        analysis.
                    </p>

                    {api_reference_html}
                </section>

                <section
                    id="module-reference"
                    class="doc-section"
                >
                    <h2>Python Module Reference</h2>

                    <p>
                        Each module includes file path, responsibility,
                        public symbols, constants, functions, classes,
                        methods, and local API routes where available.
                    </p>

                    {modules_html}
                </section>

                <section
                    id="execution-flow"
                    class="doc-section"
                >
                    <h2>Execution Flow</h2>

                    {execution_html}
                </section>

                <section
                    id="dependencies"
                    class="doc-section"
                >
                    <h2>Internal Dependencies</h2>

                    {dependencies_html}
                </section>

                <section
                    id="troubleshooting"
                    class="doc-section"
                >
                    <h2>Troubleshooting and Production Notes</h2>

                    {troubleshooting_html}
                </section>

                <footer>
                    Generated by AutoDocX from understanding
                    <code>{escape(understanding_id)}</code>.
                </footer>
            </article>
        </main>

        <aside class="right-toc">
            {right_toc}
        </aside>
    </div>
</body>
</html>
"""

    @staticmethod
    def _build_left_navigation(
            api_overview: Any,
            module_responsibilities: Any,
    ) -> str:
        api_links = ""

        if isinstance(api_overview, list) and api_overview:
            endpoint_links: list[str] = []

            for index, endpoint in enumerate(api_overview, start=1):
                if not isinstance(endpoint, dict):
                    continue

                method = str(endpoint.get("method", "")).upper()
                path = str(endpoint.get("path", ""))
                label = f"{method} {path}".strip()

                endpoint_links.append(
                    f"""
                    <a href="#endpoint-{index}">
                        {escape(label)}
                    </a>
                    """
                )

            api_links = "\n".join(endpoint_links)

        module_links = ""

        if isinstance(module_responsibilities, list):
            links: list[str] = []

            for index, module in enumerate(
                    module_responsibilities,
                    start=1,
            ):
                if not isinstance(module, dict):
                    continue

                module_name = str(
                    module.get(
                        "module",
                        f"Module {index}",
                    )
                )

                links.append(
                    f"""
                    <a href="#module-{index}">
                        {escape(module_name)}
                    </a>
                    """
                )

            module_links = "\n".join(links)

        return f"""
        <nav>
            <div class="nav-group">
                <p class="nav-title">Get started</p>
                <a href="#overview">Overview</a>
                <a href="#quickstart">Quickstart</a>
                <a href="#project-statistics">Project Statistics</a>
                <a href="#architecture">Architecture</a>
                <a href="#runtime-tooling-context">Runtime Tooling</a>
            </div>

            <div class="nav-group">
                <p class="nav-title">API Reference</p>
                <a href="#api-reference">All endpoints</a>
                {api_links}
            </div>

            <div class="nav-group">
                <p class="nav-title">Modules</p>
                <a href="#module-reference">All modules</a>
                {module_links}
            </div>

            <div class="nav-group">
                <p class="nav-title">Operations</p>
                <a href="#execution-flow">Execution Flow</a>
                <a href="#dependencies">Internal Dependencies</a>
                <a href="#troubleshooting">Troubleshooting</a>
            </div>
        </nav>
        """

    @staticmethod
    def _build_right_toc(
            api_overview: Any,
            module_responsibilities: Any,
            risks_and_gaps: Any,
            statistics: Any,
    ) -> str:
        links = [
            ("overview", "Overview"),
            ("quickstart", "Quickstart"),
            ("project-statistics", "Project Statistics"),
            ("architecture", "Architecture"),
            ("runtime-tooling-context", "Runtime Tooling"),
            ("api-reference", "API Reference"),
            ("module-reference", "Python Module Reference"),
            ("execution-flow", "Execution Flow"),
            ("dependencies", "Internal Dependencies"),
            ("troubleshooting", "Troubleshooting"),
        ]

        api_count = (
            len(api_overview)
            if isinstance(api_overview, list)
            else 0
        )

        module_count = (
            len(module_responsibilities)
            if isinstance(module_responsibilities, list)
            else 0
        )

        risk_count = (
            len(risks_and_gaps)
            if isinstance(risks_and_gaps, list)
            else 0
        )

        class_count = 0
        function_count = 0

        if isinstance(statistics, dict):
            class_count = int(statistics.get("classes", 0) or 0)
            function_count = int(statistics.get("functions", 0) or 0)

        link_html = "\n".join(
            f'<a href="#{section_id}">{escape(title)}</a>'
            for section_id, title in links
        )

        return f"""
        <h2>On this page</h2>
        {link_html}

        <div class="mini-card" style="margin-top: 22px;">
            <h3>Page stats</h3>
            <p>{api_count} endpoints</p>
            <p>{module_count} modules</p>
            <p>{class_count} classes</p>
            <p>{function_count} functions</p>
            <p>{risk_count} production notes</p>
        </div>
        """

    @staticmethod
    def _build_quickstart(
            project_name: str,
    ) -> str:
        safe_project_name = escape(project_name)

        return f"""
        <p>
            Start the FastAPI server, then open the generated API docs
            or call the project documentation sync endpoint.
        </p>

        <div class="code-block">
            <div class="code-title">
                <span>Run the application</span>
                <span>PowerShell / terminal</span>
            </div>
            <pre><code>python -m uvicorn app.main:app --reload</code></pre>
        </div>

        <div class="code-block">
            <div class="code-title">
                <span>Generate documentation</span>
                <span>Python request example</span>
            </div>
            <pre><code>import requests

response = requests.post(
    "http://127.0.0.1:8000/api/projects/documentation/sync",
    json={{
        "project_path": r"C:\\path\\to\\{safe_project_name}"
    }},
    timeout=900,
)

response.raise_for_status()
print(response.json())</code></pre>
        </div>
        """

    @staticmethod
    def _build_statistics(
            statistics: Any,
    ) -> str:
        if not isinstance(statistics, dict) or not statistics:
            return (
                '<p class="empty">'
                "No project statistics available."
                "</p>"
            )

        preferred_keys = [
            ("python_modules", "Python modules"),
            ("modules", "Modules"),
            ("api_routes", "API routes"),
            ("routes", "Routes"),
            ("classes", "Classes"),
            ("functions", "Functions"),
            ("async_functions", "Async functions"),
            ("methods", "Methods"),
            ("constants", "Constants"),
            ("internal_dependencies", "Dependencies"),
            ("documented_functions", "Documented functions"),
            ("documented_classes", "Documented classes"),
            ("modules_with_syntax_errors", "Syntax error modules"),
        ]

        cards: list[str] = []

        for key, label in preferred_keys:
            if key not in statistics:
                continue

            cards.append(
                f"""
                <article class="stat-card">
                    <span>{escape(label)}</span>
                    <strong>{escape(str(statistics.get(key)))}</strong>
                </article>
                """
            )

        if not cards:
            return (
                '<p class="empty">'
                "No project statistics available."
                "</p>"
            )

        return (
                '<div class="stats-grid">'
                + "\n".join(cards)
                + "</div>"
        )

    @staticmethod
    def _build_api_reference(
            api_overview: Any,
    ) -> str:
        if not isinstance(api_overview, list) or not api_overview:
            return (
                '<p class="empty">'
                "No API reference information available."
                "</p>"
            )

        cards: list[str] = []

        for index, endpoint in enumerate(api_overview, start=1):
            if not isinstance(endpoint, dict):
                continue

            method = str(endpoint.get("method", "")).upper()
            path = str(endpoint.get("path", ""))
            handler = str(endpoint.get("handler", ""))
            handler_signature = str(
                endpoint.get("handler_signature") or ""
            )
            returns = str(endpoint.get("returns") or "")
            response_model = str(endpoint.get("response_model") or "")
            status_code = str(endpoint.get("status_code") or "")
            file_path = str(endpoint.get("file") or "")
            module_name = str(endpoint.get("module") or "")
            line = str(endpoint.get("line") or "")

            purpose = DocumentBuilder._clean_llm_text(
                str(
                    endpoint.get("purpose")
                    or endpoint.get("summary")
                    or endpoint.get("description")
                    or endpoint.get("docstring")
                    or "API endpoint discovered from route decorators."
                )
            )

            method_class = DocumentBuilder._get_method_class(method)

            example_json = DocumentBuilder._build_endpoint_example_json(
                path,
            )

            parameters_html = DocumentBuilder._build_parameters_table(
                endpoint.get("arguments", []),
            )

            tags_html = DocumentBuilder._build_pills(
                endpoint.get("tags", []),
            )

            returns_html = DocumentBuilder._build_returns_block(
                returns=returns,
                response_model=response_model,
                status_code=status_code,
            )

            cards.append(
                f"""
                <article
                    id="endpoint-{index}"
                    class="reference-card"
                >
                    <div class="reference-header">
                        <div class="endpoint">
                            <span class="method {method_class}">
                                {escape(method)}
                            </span>

                            <div>
                                <div class="path">
                                    {escape(path)}
                                </div>

                                <p>{escape(purpose)}</p>
                            </div>
                        </div>
                    </div>

                    <div class="reference-body">
                        <p class="small-label">Handler</p>
                        <p><code>{escape(handler)}</code></p>

                        {
                DocumentBuilder._build_optional_signature(
                    label="Handler signature",
                    signature=handler_signature,
                )
                }

                        <p class="small-label">Location</p>
                        <p>
                            <code>{escape(module_name)}</code>
                            ·
                            <code>{escape(file_path)}</code>
                            {DocumentBuilder._build_line_text(line)}
                        </p>

                        <p class="small-label">Tags</p>
                        {tags_html}

                        <p class="small-label">Parameters</p>
                        {parameters_html}

                        <p class="small-label">Returns</p>
                        {returns_html}

                        <p class="small-label">Request example</p>
                        <div class="code-block">
                            <div class="code-title">
                                <span>Example</span>
                                <span>requests</span>
                            </div>
                            <pre><code>{escape(example_json)}</code></pre>
                        </div>
                    </div>
                </article>
                """
            )

        if not cards:
            return (
                '<p class="empty">'
                "No API reference information available."
                "</p>"
            )

        return "\n".join(cards)

    @staticmethod
    def _build_module_reference(
            modules: Any,
    ) -> str:
        if not isinstance(modules, list) or not modules:
            return (
                '<p class="empty">'
                "No module reference information available."
                "</p>"
            )

        cards: list[str] = []

        for index, module in enumerate(modules, start=1):
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

            responsibility = DocumentBuilder._clean_llm_text(
                str(
                    module.get("responsibility")
                    or module.get("summary")
                    or module.get("purpose_hint")
                    or ""
                )
            )

            symbols = module.get(
                "important_symbols",
                [],
            )

            import_example = DocumentBuilder._build_import_example(
                module_name,
                symbols,
            )

            constants_html = DocumentBuilder._build_constants_table(
                module.get("constants", []),
            )

            functions_html = DocumentBuilder._build_function_blocks(
                title="Functions",
                functions=module.get("functions", []),
            )

            async_functions_html = DocumentBuilder._build_function_blocks(
                title="Async functions",
                functions=module.get("async_functions", []),
            )

            classes_html = DocumentBuilder._build_class_blocks(
                module.get("classes", []),
            )

            routes_html = DocumentBuilder._build_module_routes_table(
                module.get("routes", []),
            )

            cards.append(
                f"""
                <article
                    id="module-{index}"
                    class="reference-card"
                >
                    <div class="reference-header">
                        <h3>
                            <code>{escape(module_name)}</code>
                        </h3>

                        <p>
                            <code>{escape(file_path)}</code>
                        </p>
                    </div>

                    <div class="reference-body">
                        <p>{escape(responsibility)}</p>

                        <p class="small-label">Public symbols</p>
                        {DocumentBuilder._build_pills(symbols)}

                        <p class="small-label">Usage pattern</p>
                        <div class="code-block">
                            <div class="code-title">
                                <span>Import example</span>
                                <span>Python</span>
                            </div>
                            <pre><code>{escape(import_example)}</code></pre>
                        </div>

                        {constants_html}
                        {functions_html}
                        {async_functions_html}
                        {classes_html}
                        {routes_html}
                    </div>
                </article>
                """
            )

        if not cards:
            return (
                '<p class="empty">'
                "No module reference information available."
                "</p>"
            )

        return "\n".join(cards)

    @staticmethod
    def _build_constants_table(
            constants: Any,
    ) -> str:
        if not isinstance(constants, list) or not constants:
            return ""

        rows: list[str] = []

        for constant in constants:
            if not isinstance(constant, dict):
                continue

            name = str(constant.get("name") or "")
            annotation = str(constant.get("annotation") or "")
            value = str(constant.get("value") or "")

            rows.append(
                f"""
                <tr>
                    <td><code>{escape(name)}</code></td>
                    <td>{escape(annotation or "-")}</td>
                    <td><code>{escape(value or "-")}</code></td>
                </tr>
                """
            )

        if not rows:
            return ""

        return f"""
        <p class="small-label">Constants</p>
        <div class="table-wrap">
            <table>
                <thead>
                    <tr>
                        <th>Name</th>
                        <th>Type</th>
                        <th>Value</th>
                    </tr>
                </thead>
                <tbody>
                    {"".join(rows)}
                </tbody>
            </table>
        </div>
        """

    @staticmethod
    def _build_function_blocks(
            title: str,
            functions: Any,
    ) -> str:
        if not isinstance(functions, list) or not functions:
            return ""

        blocks: list[str] = []

        for function in functions:
            if not isinstance(function, dict):
                continue

            name = str(function.get("name") or "unknown_function")
            signature = str(function.get("signature") or name)
            docstring = DocumentBuilder._clean_llm_text(
                str(function.get("docstring") or "")
            )
            returns = str(function.get("returns") or "")

            if not docstring:
                docstring = DocumentBuilder._build_function_purpose_sentence(
                    name=name,
                    signature=signature,
                    returns=returns,
                    called_functions=function.get(
                        "called_functions",
                        [],
                    ),
                    called_functions_preview=function.get(
                        "called_functions_preview",
                        [],
                    ),
                )

            calls_html = DocumentBuilder._build_called_functions_block(
                function,
            )

            parameters_html = DocumentBuilder._build_parameters_table(
                function.get("arguments", []),
            )

            returns_html = DocumentBuilder._build_returns_block(
                returns=returns,
                response_model="",
                status_code="",
            )

            blocks.append(
                f"""
                <div class="sub-reference">
                    <h4><code>{escape(name)}</code></h4>
                    <code class="signature">{escape(signature)}</code>

                    <p>{escape(docstring)}</p>

                    {calls_html}

                    <p class="small-label">Parameters</p>
                    {parameters_html}

                    <p class="small-label">Returns</p>
                    {returns_html}
                </div>
                """
            )

        if not blocks:
            return ""

        return f"""
        <p class="small-label">{escape(title)}</p>
        {"".join(blocks)}
        """

    @staticmethod
    def _build_called_functions_block(
            function: dict[str, Any],
    ) -> str:
        called_functions = function.get(
            "called_functions",
            [],
        )

        called_function_previews = function.get(
            "called_functions_preview",
            [],
        )

        if not isinstance(called_functions, list):
            called_functions = []

        if not isinstance(called_function_previews, list):
            called_function_previews = []

        visible_calls = [
            str(call).strip()
            for call in called_functions
            if str(call).strip()
        ]

        visible_previews = [
            str(call).strip()
            for call in called_function_previews
            if str(call).strip()
        ]

        if not visible_calls and not visible_previews:
            return ""

        rows: list[str] = []

        max_rows = max(
            len(visible_calls),
            len(visible_previews),
        )

        for index in range(max_rows):
            call_name = (
                visible_calls[index]
                if index < len(visible_calls)
                else "-"
            )

            call_preview = (
                visible_previews[index]
                if index < len(visible_previews)
                else call_name
            )

            rows.append(
                f"""
                <tr>
                    <td><code>{escape(call_name)}</code></td>
                    <td><code>{escape(call_preview)}</code></td>
                    <td>
                        {escape(DocumentBuilder._describe_called_function(call_name))}
                    </td>
                </tr>
                """
            )

        return f"""
        <p class="small-label">Calls made by this function</p>

        <div class="table-wrap">
            <table>
                <thead>
                    <tr>
                        <th>Called function</th>
                        <th>Call details</th>
                        <th>Why it matters</th>
                    </tr>
                </thead>
                <tbody>
                    {"".join(rows)}
                </tbody>
            </table>
        </div>
        """

    @staticmethod
    def _describe_called_function(
            call_name: str,
    ) -> str:
        clean_call_name = call_name.strip()

        if not clean_call_name or clean_call_name == "-":
            return "Function call used by this workflow."

        readable_name = (
            clean_call_name
            .split(".")[-1]
            .strip("_")
            .replace("_", " ")
        )

        if clean_call_name.startswith("print"):
            return "Writes information to the console or terminal."

        if clean_call_name.startswith("open"):
            return "Opens a file or resource for reading or writing."

        if "read" in readable_name:
            return "Reads input data needed by the workflow."

        if (
            "write" in readable_name
            or "save" in readable_name
            or "store" in readable_name
        ):
            return "Writes or persists output produced by the workflow."

        if "load" in readable_name:
            return "Loads data or configuration needed for processing."

        if "process" in readable_name:
            return "Runs the main processing logic for this workflow."

        if "generate" in readable_name:
            return "Generates output data, files, reports, or documentation."

        if "build" in readable_name:
            return "Builds an intermediate structure or final output."

        if "parse" in readable_name:
            return "Parses input content into structured data."

        if "extract" in readable_name:
            return "Extracts useful information from the input data."

        if "scan" in readable_name:
            return "Scans files, folders, or project structure."

        if "validate" in readable_name:
            return "Validates input before the workflow continues."

        if "compare" in readable_name:
            return "Compares two inputs or project states."

        return (
            f"Calls {clean_call_name}, which appears to support the "
            f"{readable_name} step in this function."
        )

    @staticmethod
    def _build_function_purpose_sentence(
            name: str,
            signature: str,
            returns: str,
            called_functions: Any | None = None,
            called_functions_preview: Any | None = None,
    ) -> str:
        clean_name = name.strip()
        readable_name = clean_name.strip("_").replace("_", " ")

        calls = (
            called_functions
            if isinstance(called_functions, list)
            else []
        )

        call_previews = (
            called_functions_preview
            if isinstance(called_functions_preview, list)
            else []
        )

        visible_calls = [
            str(call).strip()
            for call in calls
            if str(call).strip()
        ]

        visible_previews = [
            str(call).strip()
            for call in call_previews
            if str(call).strip()
        ]

        if clean_name == "main":
            if visible_previews:
                first_call = visible_previews[0]
                first_call_name = (
                    visible_calls[0]
                    if visible_calls
                    else first_call
                )

                return (
                    "This function is the script entrypoint. "
                    "When this file is executed directly, it starts the "
                    "actual workflow by calling "
                    f"{first_call_name}. "
                    f"The call is made as {first_call}. "
                    "Review the called function next to understand the "
                    "main business logic executed by this script."
                )

            if visible_calls:
                return (
                    "This function is the script entrypoint. "
                    "When this file is executed directly, it starts the "
                    "actual workflow by calling "
                    f"{', '.join(visible_calls[:3])}. "
                    "Review these called functions next to understand what "
                    "the script really does."
                )

            return (
                "This function is the script entrypoint for this module. "
                "No function-call metadata was available in the current "
                "documentation payload. Regenerate the scan after enabling "
                "called function parsing to show the workflow started by "
                "this main function."
            )

        if visible_previews:
            first_call = visible_previews[0]
            first_call_name = (
                visible_calls[0]
                if visible_calls
                else first_call
            )

            return (
                f"Implements the {readable_name} operation for this module. "
                "It coordinates the workflow by calling "
                f"{first_call_name}. "
                f"The call is made as {first_call}. "
                f"It returns {returns or 'a result'} used by the surrounding "
                "workflow."
            )

        if visible_calls:
            return (
                f"Implements the {readable_name} operation for this module. "
                "It coordinates work through internal or imported calls such as "
                f"{', '.join(visible_calls[:3])}. "
                f"It returns {returns or 'a result'} used by the surrounding "
                "workflow."
            )

        if clean_name.startswith("_build_"):
            subject = clean_name.replace("_build_", "").replace("_", " ")

            return (
                f"Builds the {subject} section or data structure used by "
                f"the documentation generator. It returns "
                f"{returns or 'a computed value'} for later rendering."
            )

        if clean_name.startswith("_extract_"):
            subject = clean_name.replace("_extract_", "").replace("_", " ")

            return (
                f"Extracts {subject} information from parsed source-code "
                f"metadata. This helper supports scanner, analyzer, or "
                f"documentation reference generation."
            )

        if clean_name.startswith("_get_"):
            subject = clean_name.replace("_get_", "").replace("_", " ")

            return (
                f"Retrieves {subject} from the provided input data and "
                f"returns {returns or 'the resolved value'}."
            )

        if clean_name.startswith("_validate_"):
            subject = clean_name.replace("_validate_", "").replace("_", " ")

            return (
                f"Validates {subject} before the workflow continues. "
                f"This helps catch invalid input early and keeps downstream "
                f"processing safe."
            )

        if clean_name.startswith("_compact_"):
            subject = clean_name.replace("_compact_", "").replace("_", " ")

            return (
                f"Compacts {subject} metadata into a smaller structure "
                f"suitable for context building or documentation rendering."
            )

        if clean_name.startswith("_normalize_"):
            subject = clean_name.replace("_normalize_", "").replace("_", " ")

            return (
                f"Normalizes {subject} into a consistent representation "
                f"used by the rest of the workflow."
            )

        if clean_name.startswith("_sanitize_"):
            subject = clean_name.replace("_sanitize_", "").replace("_", " ")

            return (
                f"Sanitizes {subject} so it can be safely used in generated "
                f"paths, file names, or rendered output."
            )

        if clean_name.startswith("_read_"):
            subject = clean_name.replace("_read_", "").replace("_", " ")

            return (
                f"Reads {subject} from storage or input files and returns "
                f"the parsed result for later processing."
            )

        if clean_name.startswith("_compare_"):
            subject = clean_name.replace("_compare_", "").replace("_", " ")

            return (
                f"Compares {subject} between two project states and returns "
                f"the detected changes."
            )

        if clean_name.startswith("_is_"):
            subject = clean_name.replace("_is_", "").replace("_", " ")

            return (
                f"Checks whether the provided value matches the {subject} "
                f"condition and returns a boolean result."
            )

        if clean_name.startswith("_should_"):
            subject = clean_name.replace("_should_", "").replace("_", " ")

            return (
                f"Determines whether the workflow should {subject} for the "
                f"provided input."
            )

        return (
            f"Implements the {readable_name} operation for this module. "
            f"It uses the provided parameters and returns "
            f"{returns or 'a result'} used by the surrounding workflow."
        )

    @staticmethod
    def _build_class_blocks(
            classes: Any,
    ) -> str:
        if not isinstance(classes, list) or not classes:
            return ""

        blocks: list[str] = []

        for class_item in classes:
            if not isinstance(class_item, dict):
                continue

            class_name = str(class_item.get("name") or "UnknownClass")
            signature = str(class_item.get("signature") or f"class {class_name}:")
            docstring = DocumentBuilder._clean_llm_text(
                str(class_item.get("docstring") or "")
            )

            attributes_html = DocumentBuilder._build_attributes_table(
                class_item.get("attributes", []),
            )

            methods_html = DocumentBuilder._build_function_blocks(
                title="Methods",
                functions=class_item.get("methods", []),
            )

            blocks.append(
                f"""
                <div class="sub-reference">
                    <h4><code>{escape(class_name)}</code></h4>
                    <code class="signature">{escape(signature)}</code>

                    {
                f"<p>{escape(docstring)}</p>"
                if docstring
                else ""
                }

                    {attributes_html}
                    {methods_html}
                </div>
                """
            )

        if not blocks:
            return ""

        return f"""
        <p class="small-label">Classes</p>
        {"".join(blocks)}
        """

    @staticmethod
    def _build_attributes_table(
            attributes: Any,
    ) -> str:
        if not isinstance(attributes, list) or not attributes:
            return ""

        rows: list[str] = []

        for attribute in attributes:
            if not isinstance(attribute, dict):
                continue

            name = str(attribute.get("name") or "")
            annotation = str(attribute.get("annotation") or "")
            value = str(attribute.get("value") or "")

            rows.append(
                f"""
                <tr>
                    <td><code>{escape(name)}</code></td>
                    <td>{escape(annotation or "-")}</td>
                    <td><code>{escape(value or "-")}</code></td>
                </tr>
                """
            )

        if not rows:
            return ""

        return f"""
        <p class="small-label">Attributes</p>
        <div class="table-wrap">
            <table>
                <thead>
                    <tr>
                        <th>Name</th>
                        <th>Type</th>
                        <th>Default / Value</th>
                    </tr>
                </thead>
                <tbody>
                    {"".join(rows)}
                </tbody>
            </table>
        </div>
        """

    @staticmethod
    def _build_module_routes_table(
            routes: Any,
    ) -> str:
        if not isinstance(routes, list) or not routes:
            return ""

        rows: list[str] = []

        for route in routes:
            if not isinstance(route, dict):
                continue

            method = str(route.get("method") or "")
            path = str(route.get("path") or "")
            handler = str(
                route.get("handler")
                or route.get("function_name")
                or ""
            )

            rows.append(
                f"""
                <tr>
                    <td><code>{escape(method)}</code></td>
                    <td><code>{escape(path)}</code></td>
                    <td><code>{escape(handler)}</code></td>
                </tr>
                """
            )

        if not rows:
            return ""

        return f"""
        <p class="small-label">Local routes</p>
        <div class="table-wrap">
            <table>
                <thead>
                    <tr>
                        <th>Method</th>
                        <th>Local path</th>
                        <th>Handler</th>
                    </tr>
                </thead>
                <tbody>
                    {"".join(rows)}
                </tbody>
            </table>
        </div>
        """

    @staticmethod
    def _build_parameters_table(
            arguments: Any,
    ) -> str:
        if not isinstance(arguments, list) or not arguments:
            return (
                '<p class="empty">'
                "No parameters discovered."
                "</p>"
            )

        rows: list[str] = []

        for argument in arguments:
            if not isinstance(argument, dict):
                continue

            name = str(argument.get("name") or "")
            annotation = str(argument.get("annotation") or "")
            default = argument.get("default")
            required = argument.get("required")

            if name in {"self", "cls"}:
                continue

            default_text = "-" if default is None else str(default)

            required_text = (
                "Yes"
                if required is True
                else "No"
            )

            rows.append(
                f"""
                <tr>
                    <td><code>{escape(name)}</code></td>
                    <td>{escape(annotation or "Any")}</td>
                    <td>{escape(required_text)}</td>
                    <td><code>{escape(default_text)}</code></td>
                </tr>
                """
            )

        if not rows:
            return (
                '<p class="empty">'
                "No parameters discovered."
                "</p>"
            )

        return f"""
        <div class="table-wrap">
            <table>
                <thead>
                    <tr>
                        <th>Parameter</th>
                        <th>Type</th>
                        <th>Required</th>
                        <th>Default</th>
                    </tr>
                </thead>
                <tbody>
                    {"".join(rows)}
                </tbody>
            </table>
        </div>
        """

    @staticmethod
    def _build_returns_block(
            returns: str,
            response_model: str,
            status_code: str,
    ) -> str:
        rows: list[str] = []

        if returns:
            rows.append(
                f"""
                <tr>
                    <td>Return annotation</td>
                    <td><code>{escape(returns)}</code></td>
                </tr>
                """
            )

        if response_model:
            rows.append(
                f"""
                <tr>
                    <td>Response model</td>
                    <td><code>{escape(response_model)}</code></td>
                </tr>
                """
            )

        if status_code:
            rows.append(
                f"""
                <tr>
                    <td>Status code</td>
                    <td><code>{escape(status_code)}</code></td>
                </tr>
                """
            )

        if not rows:
            return (
                '<p class="empty">'
                "No return annotation or response model discovered."
                "</p>"
            )

        return f"""
        <div class="table-wrap">
            <table>
                <thead>
                    <tr>
                        <th>Field</th>
                        <th>Value</th>
                    </tr>
                </thead>
                <tbody>
                    {"".join(rows)}
                </tbody>
            </table>
        </div>
        """

    @staticmethod
    def _build_optional_signature(
            label: str,
            signature: str,
    ) -> str:
        if not signature:
            return ""

        return f"""
        <p class="small-label">{escape(label)}</p>
        <code class="signature">{escape(signature)}</code>
        """

    @staticmethod
    def _build_execution_flow(
            execution_flow: Any,
    ) -> str:
        if not isinstance(execution_flow, list) or not execution_flow:
            return (
                '<p class="empty">'
                "No execution flow available."
                "</p>"
            )

        cards: list[str] = []

        for index, item in enumerate(execution_flow, start=1):
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

            description = DocumentBuilder._clean_llm_text(
                str(
                    item.get(
                        "description",
                        "",
                    )
                )
            )

            related_modules = item.get(
                "related_modules",
                [],
            )

            cards.append(
                f"""
                <article class="flow-step">
                    <div class="step-number">
                        {escape(str(step))}
                    </div>

                    <div>
                        <h3>{escape(title)}</h3>

                        <p>{escape(description)}</p>

                        {DocumentBuilder._build_pills(related_modules)}
                    </div>
                </article>
                """
            )

        if not cards:
            return (
                '<p class="empty">'
                "No execution flow available."
                "</p>"
            )

        return (
                '<div class="flow-list">'
                + "\n".join(cards)
                + "</div>"
        )

    @staticmethod
    def _build_dependencies(
            dependencies: Any,
    ) -> str:
        if not isinstance(dependencies, list) or not dependencies:
            return (
                '<p class="empty">'
                "No dependency information available."
                "</p>"
            )

        cards: list[str] = []

        for dependency in dependencies:
            if not isinstance(dependency, dict):
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

            imported_name = str(
                dependency.get(
                    "imported_name",
                    "",
                )
                or ""
            )

            purpose = DocumentBuilder._clean_llm_text(
                str(
                    dependency.get(
                        "purpose",
                        "",
                    )
                )
            )

            imported_html = ""

            if imported_name:
                imported_html = (
                    f"<p>Imported: "
                    f"<code>{escape(imported_name)}</code></p>"
                )

            cards.append(
                f"""
                <article class="mini-card">
                    <h3>
                        <code>{escape(source)}</code>
                        →
                        <code>{escape(target)}</code>
                    </h3>

                    <p>
                        {escape(purpose)}
                    </p>

                    {imported_html}
                </article>
                """
            )

        if not cards:
            return (
                '<p class="empty">'
                "No dependency information available."
                "</p>"
            )

        return (
                '<div class="dependency-grid">'
                + "\n".join(cards)
                + "</div>"
        )

    @staticmethod
    def _build_runtime_context(
            runtime_context: dict[str, Any] | None,
    ) -> str:
        """
        Build the Runtime and Tooling Context section.

        Preferred format:
        - runtime_understanding generated by the vision LLM.

        Fallback format:
        - raw context blocks and screenshots.
        """

        if not isinstance(runtime_context, dict):
            return (
                """
                <div class="callout warning">
                    No runtime or tooling context was provided.
                    Add notes and screenshots from Docker, Temporal,
                    APIs, dashboards, or internal tools to document
                    how the system works outside the codebase.
                </div>
                """
            )

        runtime_understanding = runtime_context.get(
            "runtime_understanding"
        )

        if isinstance(runtime_understanding, dict):
            analyzed_html = (
                DocumentBuilder
                ._build_runtime_understanding(
                    runtime_understanding=(
                        runtime_understanding
                    ),
                )
            )

            supporting_images_html = (
                DocumentBuilder
                ._build_supporting_runtime_screenshots(
                    runtime_context=runtime_context,
                )
            )

            return (
                    analyzed_html
                    + supporting_images_html
            )

        return (
            DocumentBuilder
            ._build_raw_runtime_context_fallback(
                runtime_context=runtime_context,
            )
        )

    @staticmethod
    def _build_runtime_understanding(
            runtime_understanding: dict[str, Any],
    ) -> str:
        """
        Render LLM-analyzed runtime understanding.
        """

        runtime_summary = str(
            runtime_understanding.get(
                "runtime_summary",
                "",
            )
            or ""
        ).strip()

        tooling_stack = runtime_understanding.get(
            "tooling_stack",
            [],
        )

        runtime_flow = runtime_understanding.get(
            "runtime_flow",
            [],
        )

        screenshot_insights = (
            runtime_understanding.get(
                "screenshot_insights",
                [],
            )
        )

        operational_notes = (
            runtime_understanding.get(
                "operational_notes",
                [],
            )
        )

        risks_or_gaps = runtime_understanding.get(
            "risks_or_gaps",
            [],
        )

        parts: list[str] = []

        if runtime_summary:
            parts.append(
                f"""
                <article class="runtime-context-card">
                    <h3>Runtime summary</h3>

                    <div class="runtime-notes">
                        {escape(runtime_summary)}
                    </div>
                </article>
                """
            )

        parts.append(
            DocumentBuilder
            ._build_runtime_tooling_stack(
                tooling_stack=tooling_stack,
            )
        )

        parts.append(
            DocumentBuilder
            ._build_analyzed_runtime_flow(
                runtime_flow=runtime_flow,
            )
        )

        parts.append(
            DocumentBuilder
            ._build_screenshot_insights(
                screenshot_insights=(
                    screenshot_insights
                ),
            )
        )

        parts.append(
            DocumentBuilder
            ._build_operational_notes(
                operational_notes=(
                    operational_notes
                ),
            )
        )

        parts.append(
            DocumentBuilder
            ._build_runtime_risks_or_gaps(
                risks_or_gaps=risks_or_gaps,
            )
        )

        html = "\n".join(
            part
            for part in parts
            if part.strip()
        )

        if html.strip():
            return html

        return (
            """
            <div class="callout warning">
                Runtime context was analyzed, but the LLM did not
                return enough usable information to render this section.
            </div>
            """
        )

    @staticmethod
    def _build_runtime_tooling_stack(
            tooling_stack: Any,
    ) -> str:
        if not isinstance(tooling_stack, list) or not tooling_stack:
            return ""

        cards: list[str] = []

        for item in tooling_stack:
            if not isinstance(item, dict):
                continue

            tool = str(
                item.get(
                    "tool",
                    "Unknown tool",
                )
            )

            purpose = str(
                item.get(
                    "purpose",
                    "",
                )
                or ""
            ).strip()

            evidence = str(
                item.get(
                    "evidence",
                    "",
                )
                or ""
            ).strip()

            evidence_html = ""

            if evidence:
                evidence_html = f"""
                <p>
                    <strong>Evidence:</strong>
                    {escape(evidence)}
                </p>
                """

            cards.append(
                f"""
                <article class="mini-card">
                    <h3>{escape(tool)}</h3>

                    <p>{escape(purpose)}</p>

                    {evidence_html}
                </article>
                """
            )

        if not cards:
            return ""

        return f"""
        <article class="runtime-context-card">
            <h3>Tooling stack</h3>

            <div class="dependency-grid">
                {"".join(cards)}
            </div>
        </article>
        """

    @staticmethod
    def _build_analyzed_runtime_flow(
            runtime_flow: Any,
    ) -> str:
        if not isinstance(runtime_flow, list) or not runtime_flow:
            return ""

        cards: list[str] = []

        for index, item in enumerate(
                runtime_flow,
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
                    f"Runtime step {index}",
                )
            )

            description = str(
                item.get(
                    "description",
                    "",
                )
                or ""
            ).strip()

            evidence = str(
                item.get(
                    "evidence",
                    "",
                )
                or ""
            ).strip()

            evidence_html = ""

            if evidence:
                evidence_html = f"""
                <p>
                    <strong>Evidence:</strong>
                    {escape(evidence)}
                </p>
                """

            cards.append(
                f"""
                <article class="flow-step">
                    <div class="step-number">
                        {escape(str(step))}
                    </div>

                    <div>
                        <h3>{escape(title)}</h3>

                        <p>{escape(description)}</p>

                        {evidence_html}
                    </div>
                </article>
                """
            )

        if not cards:
            return ""

        return f"""
        <article class="runtime-context-card">
            <h3>Runtime flow</h3>

            <div class="flow-list">
                {"".join(cards)}
            </div>
        </article>
        """

    @staticmethod
    def _build_screenshot_insights(
            screenshot_insights: Any,
    ) -> str:
        if (
                not isinstance(
                    screenshot_insights,
                    list,
                )
                or not screenshot_insights
        ):
            return ""

        cards: list[str] = []

        for item in screenshot_insights:
            if not isinstance(item, dict):
                continue

            title = str(
                item.get(
                    "title",
                    "Screenshot insight",
                )
            )

            what_it_shows = str(
                item.get(
                    "what_it_shows",
                    "",
                )
                or ""
            ).strip()

            why_it_matters = str(
                item.get(
                    "why_it_matters",
                    "",
                )
                or ""
            ).strip()

            cards.append(
                f"""
                <article class="mini-card">
                    <h3>{escape(title)}</h3>

                    <p>
                        <strong>What it shows:</strong>
                        {escape(what_it_shows)}
                    </p>

                    <p>
                        <strong>Why it matters:</strong>
                        {escape(why_it_matters)}
                    </p>
                </article>
                """
            )

        if not cards:
            return ""

        return f"""
        <article class="runtime-context-card">
            <h3>Screenshot insights</h3>

            <div class="dependency-grid">
                {"".join(cards)}
            </div>
        </article>
        """

    @staticmethod
    def _build_operational_notes(
            operational_notes: Any,
    ) -> str:
        if (
                not isinstance(
                    operational_notes,
                    list,
                )
                or not operational_notes
        ):
            return ""

        items = "".join(
            f"<li>{escape(str(note))}</li>"
            for note in operational_notes
            if str(note).strip()
        )

        if not items:
            return ""

        return f"""
        <article class="runtime-context-card">
            <h3>Operational notes</h3>

            <ul>
                {items}
            </ul>
        </article>
        """

    @staticmethod
    def _build_runtime_risks_or_gaps(
            risks_or_gaps: Any,
    ) -> str:
        if (
                not isinstance(
                    risks_or_gaps,
                    list,
                )
                or not risks_or_gaps
        ):
            return ""

        cards: list[str] = []

        for item in risks_or_gaps:
            if not isinstance(item, dict):
                continue

            title = str(
                item.get(
                    "title",
                    "Runtime risk or gap",
                )
            )

            description = str(
                item.get(
                    "description",
                    "",
                )
                or ""
            ).strip()

            severity = str(
                item.get(
                    "severity",
                    "low",
                )
                or "low"
            ).lower()

            if severity not in {
                "low",
                "medium",
                "high",
            }:
                severity = "low"

            cards.append(
                f"""
                <article class="mini-card">
                    <span class="severity severity-{escape(severity)}">
                        {escape(severity)}
                    </span>

                    <h3>{escape(title)}</h3>

                    <p>{escape(description)}</p>
                </article>
                """
            )

        if not cards:
            return ""

        return f"""
        <article class="runtime-context-card">
            <h3>Runtime risks and gaps</h3>

            <div class="risk-grid">
                {"".join(cards)}
            </div>
        </article>
        """

    @staticmethod
    def _build_supporting_runtime_screenshots(
            runtime_context: dict[str, Any],
    ) -> str:
        """
        Render screenshots as supporting evidence after
        the LLM-generated explanation.
        """

        screenshots: list[dict[str, Any]] = []

        context_blocks = runtime_context.get(
            "context_blocks",
            [],
        )

        if isinstance(context_blocks, list):
            for block in context_blocks:
                if not isinstance(block, dict):
                    continue

                screenshot = block.get(
                    "screenshot"
                )

                if isinstance(screenshot, dict):
                    screenshots.append(
                        screenshot
                    )

        if not screenshots:
            raw_screenshots = runtime_context.get(
                "screenshots",
                [],
            )

            if isinstance(raw_screenshots, list):
                screenshots = [
                    screenshot
                    for screenshot in raw_screenshots
                    if isinstance(
                        screenshot,
                        dict,
                    )
                ]

        if not screenshots:
            return ""

        cards: list[str] = []

        for index, screenshot in enumerate(
                screenshots,
                start=1,
        ):
            html_src = str(
                screenshot.get(
                    "html_src",
                    "",
                )
                or screenshot.get(
                    "relative_path",
                    "",
                )
            ).strip()

            if not html_src:
                continue

            original_filename = str(
                screenshot.get(
                    "original_filename",
                    f"Screenshot {index}",
                )
            )

            cards.append(
                f"""
                <article class="screenshot-card">
                    <img
                        src="{escape(html_src)}"
                        alt="{escape(original_filename)}"
                    >

                    <div class="screenshot-caption">
                        <strong>
                            Evidence screenshot {index}:
                            {escape(original_filename)}
                        </strong>

                        Screenshot used by the LLM to analyze
                        the runtime/tooling flow.
                    </div>
                </article>
                """
            )

        if not cards:
            return ""

        return f"""
        <article class="runtime-context-card">
            <h3>Supporting screenshots</h3>

            <p>
                These screenshots were analyzed together with the
                project scan and user notes to generate the runtime
                understanding above.
            </p>

            <div class="screenshot-grid">
                {"".join(cards)}
            </div>
        </article>
        """

    @staticmethod
    def _build_raw_runtime_context_fallback(
            runtime_context: dict[str, Any],
    ) -> str:
        """
        Fallback renderer used only when runtime_understanding
        is missing.
        """

        context_blocks = runtime_context.get(
            "context_blocks",
            [],
        )

        if isinstance(context_blocks, list) and context_blocks:
            block_cards: list[str] = []

            for index, block in enumerate(
                    context_blocks,
                    start=1,
            ):
                if not isinstance(block, dict):
                    continue

                title = str(
                    block.get(
                        "title",
                        f"Runtime context {index}",
                    )
                    or f"Runtime context {index}"
                ).strip()

                text = str(
                    block.get(
                        "text",
                        "",
                    )
                    or ""
                ).strip()

                screenshot = block.get(
                    "screenshot"
                )

                screenshot_html = ""

                if isinstance(screenshot, dict):
                    html_src = str(
                        screenshot.get(
                            "html_src",
                            "",
                        )
                        or screenshot.get(
                            "relative_path",
                            "",
                        )
                    ).strip()

                    original_filename = str(
                        screenshot.get(
                            "original_filename",
                            f"Screenshot {index}",
                        )
                    )

                    if html_src:
                        screenshot_html = f"""
                        <article class="screenshot-card">
                            <img
                                src="{escape(html_src)}"
                                alt="{escape(original_filename)}"
                            >

                            <div class="screenshot-caption">
                                <strong>
                                    Screenshot:
                                    {escape(original_filename)}
                                </strong>

                                Visual reference attached to this
                                runtime context block.
                            </div>
                        </article>
                        """

                text_html = ""

                if text:
                    text_html = f"""
                    <div class="runtime-notes">
                        {escape(text)}
                    </div>
                    """

                if not text_html and not screenshot_html:
                    continue

                block_cards.append(
                    f"""
                    <article class="runtime-context-card">
                        <h3>
                            {escape(str(index))}. {escape(title)}
                        </h3>

                        {text_html}

                        {
                    f'<div class="screenshot-grid">{screenshot_html}</div>'
                    if screenshot_html
                    else ""
                    }
                    </article>
                    """
                )

            if block_cards:
                return "\n".join(block_cards)

        additional_context = str(
            runtime_context.get(
                "additional_context",
                "",
            )
            or ""
        ).strip()

        if additional_context:
            return f"""
            <article class="runtime-context-card">
                <h3>Project runtime notes</h3>

                <div class="runtime-notes">
                    {escape(additional_context)}
                </div>
            </article>
            """

        return (
            """
            <div class="callout warning">
                No runtime or tooling context was provided.
                Add notes and screenshots from Docker, Temporal,
                APIs, dashboards, or internal tools to document
                how the system works outside the codebase.
            </div>
            """
        )

    @staticmethod
    def _build_troubleshooting(
            risks: Any,
    ) -> str:
        if not isinstance(risks, list) or not risks:
            return (
                """
                <div class="callout warning">
                    No troubleshooting notes were generated for this
                    project. For production use, document authentication,
                    error handling, retries, logging, and backup strategy.
                </div>
                """
            )

        cards: list[str] = []

        for risk in risks:
            if not isinstance(risk, dict):
                continue

            title = str(
                risk.get(
                    "title",
                    "Untitled note",
                )
            )

            description = DocumentBuilder._clean_llm_text(
                str(
                    risk.get(
                        "description",
                        "",
                    )
                )
            )

            severity = str(
                risk.get(
                    "severity",
                    "low",
                )
            ).lower()

            if severity not in {"high", "medium", "low"}:
                severity = "low"

            cards.append(
                f"""
                <article class="mini-card">
                    <span class="severity severity-{escape(severity)}">
                        {escape(severity)}
                    </span>

                    <h3>{escape(title)}</h3>

                    <p>
                        {escape(description)}
                    </p>
                </article>
                """
            )

        if not cards:
            return (
                '<p class="empty">'
                "No troubleshooting notes available."
                "</p>"
            )

        return (
                '<div class="risk-grid">'
                + "\n".join(cards)
                + "</div>"
        )

    @staticmethod
    def _build_meta_chip(
            label: str,
            value: str,
    ) -> str:
        if not value:
            value = "Not available"

        return f"""
        <span class="meta-chip">
            {escape(label)}:
            <strong>{escape(value)}</strong>
        </span>
        """

    @staticmethod
    def _build_pills(
            values: Any,
    ) -> str:
        if not isinstance(values, list) or not values:
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
            if str(value).strip()
        )

        if not pills:
            return (
                '<p class="empty">'
                "None listed."
                "</p>"
            )

        return (
                '<div class="pill-list">'
                + pills
                + "</div>"
        )

    @staticmethod
    def _get_method_class(
            method: str,
    ) -> str:
        method = method.lower()

        if method == "get":
            return "method-get"

        if method == "post":
            return "method-post"

        if method == "put":
            return "method-put"

        if method == "patch":
            return "method-patch"

        if method == "delete":
            return "method-delete"

        return "method-post"

    @staticmethod
    def _build_endpoint_example_json(
            path: str,
    ) -> str:
        normalized_path = path.strip()

        if not normalized_path:
            normalized_path = "/api/projects/example"

        example_path = normalized_path.replace(
            "{project_name}",
            "AutoDocX",
        )

        if "scan" in normalized_path:
            payload = """{
    "project_path": "C:\\\\path\\\\to\\\\project"
}"""
        elif "documentation/sync" in normalized_path:
            payload = """{
    "project_path": "C:\\\\path\\\\to\\\\project"
}"""
        elif "compare" in normalized_path:
            payload = """{
    "base_scan_id": "previous_scan_id",
    "target_scan_id": "latest_scan_id"
}"""
        elif "context" in normalized_path:
            payload = """{
    "scan_id": "scan_id",
    "mode": "detailed"
}"""
        elif "understand" in normalized_path:
            payload = """{
    "scan_id": "scan_id"
}"""
        else:
            payload = "{}"

        return f"""import requests

response = requests.post(
    "http://127.0.0.1:8000{example_path}",
    json={payload},
    timeout=900,
)

response.raise_for_status()
print(response.json())"""

    @staticmethod
    def _build_import_example(
            module_name: str,
            symbols: Any,
    ) -> str:
        safe_module = module_name.strip()

        if not safe_module:
            safe_module = "app.module"

        if isinstance(symbols, list) and symbols:
            first_symbol = str(symbols[0]).strip()

            if "." in first_symbol:
                first_symbol = first_symbol.split(".")[-1]

            if first_symbol:
                return (
                    f"from {safe_module} import {first_symbol}\n\n"
                    f"# Use {first_symbol} based on the module API."
                )

        return (
            f"import {safe_module}\n\n"
            f"# Inspect {safe_module} for available classes and functions."
        )

    @staticmethod
    def _build_line_text(
            line: str,
    ) -> str:
        if not line:
            return ""

        return f" · line {escape(line)}"

    @staticmethod
    def _clean_llm_text(
            text: str,
    ) -> str:
        cleaned = text.strip()

        replacements = {
            "Confirmed:": "",
            "Reasonable inferences:": "",
            "Reasonable inference:": "",
            "Confirmed": "",
            "Reasonable inferences": "",
        }

        for old, new in replacements.items():
            cleaned = cleaned.replace(old, new)

        lines = []

        for line in cleaned.splitlines():
            stripped = line.strip()

            if stripped.startswith("- "):
                stripped = "• " + stripped[2:]

            lines.append(stripped)

        return "\n".join(lines).strip()


