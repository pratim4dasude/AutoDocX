import ast
from pathlib import Path, PurePosixPath
from typing import Any


class ProjectAnalyzer:
    """
    Builds project-level relationships from parsed Python files.

    The analyzer:
    - maps project modules
    - detects internal module dependencies
    - collects functions, async functions, classes, methods and constants
    - preserves signatures, arguments, returns, docstrings and source previews
    - discovers FastAPI router prefixes
    - discovers include_router relationships
    - builds complete FastAPI endpoint paths
    - creates developer documentation references
    - creates project-level statistics
    """

    def analyze_project(
        self,
        project_root: Path,
        parsed_files: list[dict[str, Any]],
    ) -> dict[str, Any]:
        module_map = self._build_module_map(
            parsed_files=parsed_files,
        )

        internal_dependencies = self._build_internal_dependencies(
            parsed_files=parsed_files,
            module_map=module_map,
        )

        symbols = self._collect_symbols(
            parsed_files=parsed_files,
        )

        router_definitions = self._discover_router_definitions(
            project_root=project_root,
            parsed_files=parsed_files,
        )

        router_inclusions = self._discover_router_inclusions(
            project_root=project_root,
            parsed_files=parsed_files,
        )

        routes = self._collect_routes(
            parsed_files=parsed_files,
            router_definitions=router_definitions,
            router_inclusions=router_inclusions,
            internal_dependencies=internal_dependencies,
        )

        module_references = self._build_module_references(
            parsed_files=parsed_files,
            module_map=module_map,
            internal_dependencies=internal_dependencies,
            routes=routes,
        )

        api_reference = self._build_api_reference(
            routes=routes,
        )

        statistics = self._build_statistics(
            parsed_files=parsed_files,
            symbols=symbols,
            routes=routes,
            internal_dependencies=internal_dependencies,
            module_references=module_references,
        )

        return {
            "statistics": statistics,
            "modules": [
                {
                    "module": module_name,
                    "file": file_path,
                }
                for module_name, file_path in sorted(
                    module_map.items(),
                )
            ],
            "module_references": module_references,
            "symbols": symbols,
            "api_reference": api_reference,
            "internal_dependencies": internal_dependencies,
            "router_definitions": router_definitions,
            "router_inclusions": router_inclusions,
            "routes": routes,
        }

    def _build_module_map(
        self,
        parsed_files: list[dict[str, Any]],
    ) -> dict[str, str]:
        module_map: dict[str, str] = {}

        for parsed_file in parsed_files:
            file_path = parsed_file.get("path")

            if (
                not isinstance(file_path, str)
                or not file_path.endswith(".py")
            ):
                continue

            module_name = self._path_to_module(
                file_path=file_path,
            )

            module_map[module_name] = file_path

        return module_map

    def _build_internal_dependencies(
        self,
        parsed_files: list[dict[str, Any]],
        module_map: dict[str, str],
    ) -> list[dict[str, Any]]:
        dependencies: list[dict[str, Any]] = []

        project_modules = set(module_map.keys())

        for parsed_file in parsed_files:
            source_file = parsed_file.get("path")

            if not isinstance(source_file, str):
                continue

            source_module = self._path_to_module(
                file_path=source_file,
            )

            for imported_item in parsed_file.get(
                "imports",
                [],
            ):
                imported_module = imported_item.get("module")

                if not imported_module:
                    continue

                target_module = self._find_project_module(
                    imported_module=imported_module,
                    project_modules=project_modules,
                )

                if target_module is None:
                    continue

                dependencies.append(
                    {
                        "source_file": source_file,
                        "source_module": source_module,
                        "target_file": module_map[target_module],
                        "target_module": target_module,
                        "import_type": imported_item.get("type"),
                        "imported_name": imported_item.get("name"),
                        "alias": imported_item.get("alias"),
                        "statement": imported_item.get("statement"),
                        "line": imported_item.get("line"),
                    }
                )

        dependencies.sort(
            key=lambda dependency: (
                dependency.get("source_file", ""),
                dependency.get("target_file", ""),
                dependency.get("line") or 0,
            )
        )

        return dependencies

    def _collect_symbols(
        self,
        parsed_files: list[dict[str, Any]],
    ) -> dict[str, list[dict[str, Any]]]:
        constants: list[dict[str, Any]] = []
        functions: list[dict[str, Any]] = []
        async_functions: list[dict[str, Any]] = []
        classes: list[dict[str, Any]] = []
        methods: list[dict[str, Any]] = []

        for parsed_file in parsed_files:
            file_path = parsed_file.get("path")

            if not isinstance(file_path, str):
                continue

            module_name = self._path_to_module(
                file_path=file_path,
            )

            for constant in parsed_file.get("constants", []):
                constants.append(
                    {
                        "file": file_path,
                        "module": module_name,
                        **constant,
                    }
                )

            for function in parsed_file.get("functions", []):
                functions.append(
                    {
                        "file": file_path,
                        "module": module_name,
                        **function,
                    }
                )

            for async_function in parsed_file.get(
                "async_functions",
                [],
            ):
                async_functions.append(
                    {
                        "file": file_path,
                        "module": module_name,
                        **async_function,
                    }
                )

            for class_item in parsed_file.get("classes", []):
                class_without_methods = {
                    key: value
                    for key, value in class_item.items()
                    if key != "methods"
                }

                classes.append(
                    {
                        "file": file_path,
                        "module": module_name,
                        **class_without_methods,
                    }
                )

                for method in class_item.get("methods", []):
                    methods.append(
                        {
                            "file": file_path,
                            "module": module_name,
                            "class_name": class_item.get("name"),
                            **method,
                        }
                    )

        constants.sort(
            key=lambda item: (
                item.get("file", ""),
                item.get("line") or 0,
            )
        )

        functions.sort(
            key=lambda item: (
                item.get("file", ""),
                item.get("line") or 0,
            )
        )

        async_functions.sort(
            key=lambda item: (
                item.get("file", ""),
                item.get("line") or 0,
            )
        )

        classes.sort(
            key=lambda item: (
                item.get("file", ""),
                item.get("line") or 0,
            )
        )

        methods.sort(
            key=lambda item: (
                item.get("file", ""),
                item.get("class_name", ""),
                item.get("line") or 0,
            )
        )

        return {
            "constants": constants,
            "functions": functions,
            "async_functions": async_functions,
            "classes": classes,
            "methods": methods,
        }

    def _build_module_references(
        self,
        parsed_files: list[dict[str, Any]],
        module_map: dict[str, str],
        internal_dependencies: list[dict[str, Any]],
        routes: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        references: list[dict[str, Any]] = []

        dependencies_by_source: dict[str, list[dict[str, Any]]] = {}
        routes_by_file: dict[str, list[dict[str, Any]]] = {}

        for dependency in internal_dependencies:
            source_file = dependency.get("source_file")

            if not isinstance(source_file, str):
                continue

            dependencies_by_source.setdefault(
                source_file,
                [],
            ).append(dependency)

        for route in routes:
            route_file = route.get("file")

            if not isinstance(route_file, str):
                continue

            routes_by_file.setdefault(
                route_file,
                [],
            ).append(route)

        for parsed_file in parsed_files:
            file_path = parsed_file.get("path")

            if not isinstance(file_path, str):
                continue

            module_name = self._path_to_module(
                file_path=file_path,
            )

            if module_name not in module_map:
                continue

            imports = parsed_file.get("imports", [])
            constants = parsed_file.get("constants", [])
            functions = parsed_file.get("functions", [])
            async_functions = parsed_file.get(
                "async_functions",
                [],
            )
            classes = parsed_file.get("classes", [])

            module_routes = routes_by_file.get(
                file_path,
                [],
            )

            dependencies = dependencies_by_source.get(
                file_path,
                [],
            )

            public_symbols = self._extract_public_symbols(
                constants=constants,
                functions=functions,
                async_functions=async_functions,
                classes=classes,
            )

            references.append(
                {
                    "module": module_name,
                    "file": file_path,
                    "module_docstring": parsed_file.get(
                        "module_docstring",
                    ),
                    "imports": imports,
                    "constants": constants,
                    "functions": functions,
                    "async_functions": async_functions,
                    "classes": classes,
                    "routes": module_routes,
                    "internal_dependencies": dependencies,
                    "public_symbols": public_symbols,
                    "syntax_error": parsed_file.get(
                        "syntax_error",
                    ),
                    "summary": self._build_module_summary(
                        module_name=module_name,
                        constants=constants,
                        functions=functions,
                        async_functions=async_functions,
                        classes=classes,
                        routes=module_routes,
                        dependencies=dependencies,
                    ),
                }
            )

        references.sort(
            key=lambda item: item.get("module", ""),
        )

        return references

    @staticmethod
    def _extract_public_symbols(
        constants: list[dict[str, Any]],
        functions: list[dict[str, Any]],
        async_functions: list[dict[str, Any]],
        classes: list[dict[str, Any]],
    ) -> list[str]:
        public_symbols: list[str] = []

        for constant in constants:
            name = constant.get("name")

            if isinstance(name, str) and not name.startswith("_"):
                public_symbols.append(name)

        for function in functions:
            name = function.get("name")

            if isinstance(name, str) and not name.startswith("_"):
                public_symbols.append(name)

        for async_function in async_functions:
            name = async_function.get("name")

            if isinstance(name, str) and not name.startswith("_"):
                public_symbols.append(name)

        for class_item in classes:
            name = class_item.get("name")

            if isinstance(name, str) and not name.startswith("_"):
                public_symbols.append(name)

        return sorted(set(public_symbols))

    @staticmethod
    def _build_module_summary(
        module_name: str,
        constants: list[dict[str, Any]],
        functions: list[dict[str, Any]],
        async_functions: list[dict[str, Any]],
        classes: list[dict[str, Any]],
        routes: list[dict[str, Any]],
        dependencies: list[dict[str, Any]],
    ) -> str:
        parts = [
            f"`{module_name}` contains",
            f"{len(classes)} class(es)",
            f"{len(functions)} sync function(s)",
            f"{len(async_functions)} async function(s)",
            f"{len(constants)} constant(s)",
            f"{len(routes)} API route(s)",
            f"and {len(dependencies)} internal dependency link(s).",
        ]

        return " ".join(parts)

    def _build_api_reference(
        self,
        routes: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        api_reference: list[dict[str, Any]] = []

        for route in routes:
            handler_signature = route.get("handler_signature")

            if not isinstance(handler_signature, str):
                handler_signature = ""

            full_path = route.get("full_path") or route.get("path")

            api_reference.append(
                {
                    "method": route.get("method"),
                    "path": full_path,
                    "handler": route.get("handler")
                    or route.get("function_name"),
                    "handler_signature": handler_signature,
                    "arguments": route.get("arguments", []),
                    "returns": route.get("returns"),
                    "response_model": route.get("response_model"),
                    "status_code": route.get("status_code"),
                    "summary": route.get("summary"),
                    "description": route.get("description"),
                    "tags": route.get("tags", []),
                    "docstring": route.get("docstring"),
                    "file": route.get("file"),
                    "module": route.get("module"),
                    "line": route.get("line"),
                    "router_name": route.get("router_name"),
                    "router_prefix": route.get("router_prefix"),
                    "include_router_prefix": route.get(
                        "include_router_prefix",
                    ),
                    "source_preview": route.get("source_preview"),
                    "called_functions": route.get(
                        "called_functions",
                        [],
                    ),
                    "called_functions_preview": route.get(
                        "called_functions_preview",
                        [],
                    ),
                }
            )

        api_reference.sort(
            key=lambda item: (
                item.get("path") or "",
                item.get("method") or "",
                item.get("line") or 0,
            )
        )

        return api_reference

    def _discover_router_definitions(
        self,
        project_root: Path,
        parsed_files: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        router_definitions: list[dict[str, Any]] = []

        for parsed_file in parsed_files:
            relative_file_path = parsed_file.get("path")

            if not isinstance(relative_file_path, str):
                continue

            absolute_file_path = project_root / relative_file_path

            syntax_tree = self._read_syntax_tree(
                file_path=absolute_file_path,
            )

            if syntax_tree is None:
                continue

            for node in syntax_tree.body:
                if not isinstance(node, ast.Assign):
                    continue

                router_call = node.value

                if not isinstance(router_call, ast.Call):
                    continue

                callable_name = self._node_to_string(
                    router_call.func,
                )

                if callable_name not in {
                    "APIRouter",
                    "fastapi.APIRouter",
                    "FastAPI",
                    "fastapi.FastAPI",
                }:
                    continue

                router_type = (
                    "FastAPI"
                    if callable_name.endswith("FastAPI")
                    else "APIRouter"
                )

                prefix = self._get_keyword_literal(
                    call=router_call,
                    keyword_name="prefix",
                )

                tags = self._get_keyword_literal(
                    call=router_call,
                    keyword_name="tags",
                )

                title = self._get_keyword_literal(
                    call=router_call,
                    keyword_name="title",
                )

                description = self._get_keyword_literal(
                    call=router_call,
                    keyword_name="description",
                )

                for target in node.targets:
                    if not isinstance(target, ast.Name):
                        continue

                    router_definitions.append(
                        {
                            "file": relative_file_path,
                            "module": self._path_to_module(
                                relative_file_path,
                            ),
                            "variable_name": target.id,
                            "router_type": router_type,
                            "prefix": (
                                prefix
                                if isinstance(prefix, str)
                                else ""
                            ),
                            "tags": tags if isinstance(tags, list) else [],
                            "title": (
                                title
                                if isinstance(title, str)
                                else None
                            ),
                            "description": (
                                description
                                if isinstance(description, str)
                                else None
                            ),
                            "line": getattr(node, "lineno", None),
                        }
                    )

        router_definitions.sort(
            key=lambda item: (
                item.get("file", ""),
                item.get("line") or 0,
            )
        )

        return router_definitions

    def _discover_router_inclusions(
        self,
        project_root: Path,
        parsed_files: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        router_inclusions: list[dict[str, Any]] = []

        for parsed_file in parsed_files:
            relative_file_path = parsed_file.get("path")

            if not isinstance(relative_file_path, str):
                continue

            absolute_file_path = project_root / relative_file_path

            syntax_tree = self._read_syntax_tree(
                file_path=absolute_file_path,
            )

            if syntax_tree is None:
                continue

            import_aliases = self._collect_import_aliases(
                syntax_tree=syntax_tree,
            )

            for node in ast.walk(syntax_tree):
                if not isinstance(node, ast.Call):
                    continue

                if not isinstance(node.func, ast.Attribute):
                    continue

                if node.func.attr != "include_router":
                    continue

                parent_application = self._node_to_string(
                    node.func.value,
                )

                if not node.args:
                    continue

                included_expression = self._node_to_string(
                    node.args[0],
                )

                included_module = None
                included_variable = None

                if included_expression:
                    (
                        included_module,
                        included_variable,
                    ) = self._resolve_router_reference(
                        expression=included_expression,
                        import_aliases=import_aliases,
                    )

                prefix = self._get_keyword_literal(
                    call=node,
                    keyword_name="prefix",
                )

                tags = self._get_keyword_literal(
                    call=node,
                    keyword_name="tags",
                )

                router_inclusions.append(
                    {
                        "file": relative_file_path,
                        "module": self._path_to_module(
                            relative_file_path,
                        ),
                        "application_variable": parent_application,
                        "included_expression": included_expression,
                        "included_module": included_module,
                        "included_variable": included_variable,
                        "prefix": (
                            prefix
                            if isinstance(prefix, str)
                            else ""
                        ),
                        "tags": tags if isinstance(tags, list) else [],
                        "line": getattr(node, "lineno", None),
                    }
                )

        router_inclusions.sort(
            key=lambda item: (
                item.get("file", ""),
                item.get("line") or 0,
            )
        )

        return router_inclusions

    def _collect_routes(
        self,
        parsed_files: list[dict[str, Any]],
        router_definitions: list[dict[str, Any]],
        router_inclusions: list[dict[str, Any]],
        internal_dependencies: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        routes: list[dict[str, Any]] = []

        definition_lookup = {
            (
                definition["file"],
                definition["variable_name"],
            ): definition
            for definition in router_definitions
        }

        imported_router_lookup = self._build_imported_router_lookup(
            internal_dependencies=internal_dependencies,
        )

        inclusion_prefix_lookup: dict[tuple[str, str], str] = {}
        inclusion_tags_lookup: dict[tuple[str, str], list[str]] = {}

        for inclusion in router_inclusions:
            included_module = inclusion.get("included_module")
            included_variable = inclusion.get("included_variable")

            if not included_module:
                expression = inclusion.get("included_expression")
                source_file = inclusion.get("file")

                if expression and source_file:
                    imported_reference = imported_router_lookup.get(
                        (
                            source_file,
                            expression,
                        )
                    )

                    if imported_reference:
                        included_module = imported_reference.get(
                            "module",
                        )
                        included_variable = imported_reference.get(
                            "variable",
                        )

            if included_module and included_variable:
                lookup_key = (
                    included_module,
                    included_variable,
                )

                inclusion_prefix_lookup[lookup_key] = inclusion.get(
                    "prefix",
                    "",
                )

                inclusion_tags_lookup[lookup_key] = inclusion.get(
                    "tags",
                    [],
                )

        for parsed_file in parsed_files:
            file_path = parsed_file.get("path")

            if not isinstance(file_path, str):
                continue

            module_name = self._path_to_module(
                file_path=file_path,
            )

            for route in parsed_file.get("routes", []):
                router_name = route.get("router_name")

                definition = definition_lookup.get(
                    (
                        file_path,
                        router_name,
                    )
                )

                local_prefix = ""
                router_tags: list[str] = []

                if definition:
                    local_prefix = definition.get("prefix", "")
                    router_tags = definition.get("tags", [])

                inclusion_lookup_key = (
                    module_name,
                    router_name,
                )

                inclusion_prefix = inclusion_prefix_lookup.get(
                    inclusion_lookup_key,
                    "",
                )

                inclusion_tags = inclusion_tags_lookup.get(
                    inclusion_lookup_key,
                    [],
                )

                route_path = route.get("path") or ""

                full_path = self._join_paths(
                    inclusion_prefix,
                    local_prefix,
                    route_path,
                )

                route_tags = route.get("tags", [])

                combined_tags = self._merge_tags(
                    inclusion_tags,
                    router_tags,
                    route_tags,
                )

                routes.append(
                    {
                        "file": file_path,
                        "module": module_name,
                        **route,
                        "tags": combined_tags,
                        "include_router_prefix": (
                            inclusion_prefix or None
                        ),
                        "router_prefix": local_prefix or None,
                        "full_path": full_path,
                    }
                )

        routes.sort(
            key=lambda item: (
                item.get("full_path", ""),
                item.get("method", ""),
                item.get("line") or 0,
            )
        )

        return routes

    def _build_imported_router_lookup(
        self,
        internal_dependencies: list[dict[str, Any]],
    ) -> dict[tuple[str, str], dict[str, str]]:
        lookup: dict[tuple[str, str], dict[str, str]] = {}

        for dependency in internal_dependencies:
            imported_name = dependency.get("imported_name")

            if not imported_name:
                continue

            alias = dependency.get("alias")
            local_name = alias or imported_name

            lookup[
                (
                    dependency["source_file"],
                    local_name,
                )
            ] = {
                "module": dependency["target_module"],
                "variable": imported_name,
            }

        return lookup

    def _build_statistics(
        self,
        parsed_files: list[dict[str, Any]],
        symbols: dict[str, list[dict[str, Any]]],
        routes: list[dict[str, Any]],
        internal_dependencies: list[dict[str, Any]],
        module_references: list[dict[str, Any]],
    ) -> dict[str, int]:
        files_with_syntax_errors = sum(
            1
            for parsed_file in parsed_files
            if parsed_file.get("syntax_error") is not None
        )

        files_with_docstrings = sum(
            1
            for parsed_file in parsed_files
            if parsed_file.get("module_docstring")
        )

        documented_functions = sum(
            1
            for function in (
                symbols["functions"]
                + symbols["async_functions"]
                + symbols["methods"]
            )
            if function.get("docstring")
        )

        documented_classes = sum(
            1
            for class_item in symbols["classes"]
            if class_item.get("docstring")
        )

        return {
            "parsed_python_files": len(parsed_files),
            "modules": len(module_references),
            "constants": len(symbols["constants"]),
            "functions": len(symbols["functions"]),
            "async_functions": len(symbols["async_functions"]),
            "classes": len(symbols["classes"]),
            "methods": len(symbols["methods"]),
            "routes": len(routes),
            "internal_dependencies": len(internal_dependencies),
            "files_with_syntax_errors": files_with_syntax_errors,
            "files_with_module_docstrings": files_with_docstrings,
            "documented_functions": documented_functions,
            "documented_classes": documented_classes,
        }

    @staticmethod
    def _read_syntax_tree(
        file_path: Path,
    ) -> ast.Module | None:
        try:
            source_code = file_path.read_text(
                encoding="utf-8",
            )

            return ast.parse(
                source_code,
                filename=str(file_path),
            )

        except (
            OSError,
            UnicodeDecodeError,
            SyntaxError,
        ):
            return None

    @staticmethod
    def _collect_import_aliases(
        syntax_tree: ast.Module,
    ) -> dict[str, tuple[str, str | None]]:
        aliases: dict[str, tuple[str, str | None]] = {}

        for node in syntax_tree.body:
            if isinstance(node, ast.ImportFrom):
                module_name = node.module

                if not module_name:
                    continue

                for imported_name in node.names:
                    local_name = imported_name.asname or imported_name.name

                    aliases[local_name] = (
                        module_name,
                        imported_name.name,
                    )

            elif isinstance(node, ast.Import):
                for imported_module in node.names:
                    local_name = imported_module.asname or imported_module.name

                    aliases[local_name] = (
                        imported_module.name,
                        None,
                    )

        return aliases

    @staticmethod
    def _resolve_router_reference(
        expression: str,
        import_aliases: dict[str, tuple[str, str | None]],
    ) -> tuple[str | None, str | None]:
        if expression in import_aliases:
            module_name, imported_name = import_aliases[expression]

            return (
                module_name,
                imported_name or expression,
            )

        expression_parts = expression.split(".")
        first_part = expression_parts[0]

        if first_part not in import_aliases:
            return None, None

        module_name, imported_name = import_aliases[first_part]

        if imported_name:
            variable_name = imported_name
        elif len(expression_parts) > 1:
            variable_name = expression_parts[-1]
        else:
            variable_name = first_part

        return module_name, variable_name

    @staticmethod
    def _merge_tags(
        *tag_groups: list[str],
    ) -> list[str]:
        tags: list[str] = []

        for tag_group in tag_groups:
            if not isinstance(tag_group, list):
                continue

            for tag in tag_group:
                if isinstance(tag, str) and tag not in tags:
                    tags.append(tag)

        return tags

    @staticmethod
    def _get_keyword_literal(
        call: ast.Call,
        keyword_name: str,
    ) -> Any:
        for keyword in call.keywords:
            if keyword.arg != keyword_name:
                continue

            try:
                return ast.literal_eval(keyword.value)

            except (
                ValueError,
                TypeError,
            ):
                return None

        return None

    @staticmethod
    def _node_to_string(
        node: ast.AST | None,
    ) -> str | None:
        if node is None:
            return None

        try:
            return ast.unparse(node)

        except Exception:
            return None

    @staticmethod
    def _path_to_module(
        file_path: str,
    ) -> str:
        path = PurePosixPath(file_path)

        if path.name == "__init__.py":
            module_parts = path.parent.parts
        else:
            module_parts = path.with_suffix("").parts

        return ".".join(module_parts)

    @staticmethod
    def _find_project_module(
        imported_module: str,
        project_modules: set[str],
    ) -> str | None:
        if imported_module in project_modules:
            return imported_module

        candidates = [
            module_name
            for module_name in project_modules
            if (
                module_name.startswith(f"{imported_module}.")
                or imported_module.startswith(f"{module_name}.")
            )
        ]

        if not candidates:
            return None

        return max(
            candidates,
            key=len,
        )

    @staticmethod
    def _join_paths(
        *path_parts: str,
    ) -> str:
        valid_parts = [
            part.strip("/")
            for part in path_parts
            if isinstance(part, str) and part.strip("/")
        ]

        if not valid_parts:
            return "/"

        return "/" + "/".join(valid_parts)