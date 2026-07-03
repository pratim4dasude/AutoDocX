import ast
from pathlib import Path, PurePosixPath
from typing import Any


class ProjectAnalyzer:
    """
    Builds project-level relationships from parsed Python files.

    The analyzer:
    - maps project modules
    - detects internal module dependencies
    - collects functions, classes and methods
    - discovers FastAPI router prefixes
    - discovers include_router relationships
    - builds complete FastAPI endpoint paths
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

        internal_dependencies = (
            self._build_internal_dependencies(
                parsed_files=parsed_files,
                module_map=module_map,
            )
        )

        symbols = self._collect_symbols(
            parsed_files=parsed_files,
        )

        router_definitions = (
            self._discover_router_definitions(
                project_root=project_root,
                parsed_files=parsed_files,
            )
        )

        router_inclusions = (
            self._discover_router_inclusions(
                project_root=project_root,
                parsed_files=parsed_files,
            )
        )

        routes = self._collect_routes(
            parsed_files=parsed_files,
            router_definitions=router_definitions,
            router_inclusions=router_inclusions,
            internal_dependencies=internal_dependencies,
        )

        statistics = self._build_statistics(
            parsed_files=parsed_files,
            symbols=symbols,
            routes=routes,
            internal_dependencies=internal_dependencies,
        )

        return {
            "statistics": statistics,
            "modules": [
                {
                    "module": module_name,
                    "file": file_path,
                }
                for module_name, file_path in sorted(
                    module_map.items()
                )
            ],
            "symbols": symbols,
            "internal_dependencies": (
                internal_dependencies
            ),
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
                imported_module = imported_item.get(
                    "module"
                )

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
                        "target_file": module_map[
                            target_module
                        ],
                        "target_module": target_module,
                        "import_type": imported_item.get(
                            "type"
                        ),
                        "imported_name": imported_item.get(
                            "name"
                        ),
                        "alias": imported_item.get(
                            "alias"
                        ),
                        "line": imported_item.get(
                            "line"
                        ),
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
        functions: list[dict[str, Any]] = []
        async_functions: list[dict[str, Any]] = []
        classes: list[dict[str, Any]] = []
        methods: list[dict[str, Any]] = []

        for parsed_file in parsed_files:
            file_path = parsed_file.get("path")

            if not isinstance(file_path, str):
                continue

            for function in parsed_file.get(
                "functions",
                [],
            ):
                functions.append(
                    {
                        "file": file_path,
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
                        **async_function,
                    }
                )

            for class_item in parsed_file.get(
                "classes",
                [],
            ):
                class_without_methods = {
                    key: value
                    for key, value in class_item.items()
                    if key != "methods"
                }

                classes.append(
                    {
                        "file": file_path,
                        **class_without_methods,
                    }
                )

                for method in class_item.get(
                    "methods",
                    [],
                ):
                    methods.append(
                        {
                            "file": file_path,
                            "class_name": class_item.get(
                                "name"
                            ),
                            **method,
                        }
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
            "functions": functions,
            "async_functions": async_functions,
            "classes": classes,
            "methods": methods,
        }

    def _discover_router_definitions(
        self,
        project_root: Path,
        parsed_files: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        router_definitions: list[dict[str, Any]] = []

        for parsed_file in parsed_files:
            relative_file_path = parsed_file.get("path")

            if not isinstance(
                relative_file_path,
                str,
            ):
                continue

            absolute_file_path = (
                project_root / relative_file_path
            )

            syntax_tree = self._read_syntax_tree(
                file_path=absolute_file_path,
            )

            if syntax_tree is None:
                continue

            for node in syntax_tree.body:
                if not isinstance(
                    node,
                    ast.Assign,
                ):
                    continue

                router_call = node.value

                if not isinstance(router_call, ast.Call):
                    continue

                callable_name = self._node_to_string(
                    router_call.func
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

                for target in node.targets:
                    if not isinstance(target, ast.Name):
                        continue

                    router_definitions.append(
                        {
                            "file": relative_file_path,
                            "module": self._path_to_module(
                                relative_file_path
                            ),
                            "variable_name": target.id,
                            "router_type": router_type,
                            "prefix": (
                                prefix
                                if isinstance(prefix, str)
                                else ""
                            ),
                            "line": getattr(
                                node,
                                "lineno",
                                None,
                            ),
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

            if not isinstance(
                relative_file_path,
                str,
            ):
                continue

            absolute_file_path = (
                project_root / relative_file_path
            )

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

                if not isinstance(
                    node.func,
                    ast.Attribute,
                ):
                    continue

                if node.func.attr != "include_router":
                    continue

                parent_application = (
                    self._node_to_string(
                        node.func.value
                    )
                )

                if not node.args:
                    continue

                included_expression = (
                    self._node_to_string(
                        node.args[0]
                    )
                )

                included_module = None
                included_variable = None

                if included_expression:
                    included_module, included_variable = (
                        self._resolve_router_reference(
                            expression=included_expression,
                            import_aliases=import_aliases,
                        )
                    )

                prefix = self._get_keyword_literal(
                    call=node,
                    keyword_name="prefix",
                )

                router_inclusions.append(
                    {
                        "file": relative_file_path,
                        "module": self._path_to_module(
                            relative_file_path
                        ),
                        "application_variable": (
                            parent_application
                        ),
                        "included_expression": (
                            included_expression
                        ),
                        "included_module": (
                            included_module
                        ),
                        "included_variable": (
                            included_variable
                        ),
                        "prefix": (
                            prefix
                            if isinstance(prefix, str)
                            else ""
                        ),
                        "line": getattr(
                            node,
                            "lineno",
                            None,
                        ),
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

        module_definition_lookup = {
            (
                definition["module"],
                definition["variable_name"],
            ): definition
            for definition in router_definitions
        }

        imported_router_lookup = (
            self._build_imported_router_lookup(
                internal_dependencies=(
                    internal_dependencies
                ),
            )
        )

        inclusion_prefix_lookup: dict[
            tuple[str, str],
            str,
        ] = {}

        for inclusion in router_inclusions:
            included_module = inclusion.get(
                "included_module"
            )
            included_variable = inclusion.get(
                "included_variable"
            )

            if not included_module:
                expression = inclusion.get(
                    "included_expression"
                )

                source_file = inclusion.get("file")

                if expression and source_file:
                    imported_reference = (
                        imported_router_lookup.get(
                            (
                                source_file,
                                expression,
                            )
                        )
                    )

                    if imported_reference:
                        included_module = (
                            imported_reference.get(
                                "module"
                            )
                        )
                        included_variable = (
                            imported_reference.get(
                                "variable"
                            )
                        )

            if (
                included_module
                and included_variable
            ):
                inclusion_prefix_lookup[
                    (
                        included_module,
                        included_variable,
                    )
                ] = inclusion.get("prefix", "")

        for parsed_file in parsed_files:
            file_path = parsed_file.get("path")

            if not isinstance(file_path, str):
                continue

            module_name = self._path_to_module(
                file_path=file_path,
            )

            for route in parsed_file.get(
                "routes",
                [],
            ):
                router_name = route.get(
                    "router_name"
                )

                definition = definition_lookup.get(
                    (
                        file_path,
                        router_name,
                    )
                )

                local_prefix = ""

                if definition:
                    local_prefix = definition.get(
                        "prefix",
                        "",
                    )

                inclusion_prefix = (
                    inclusion_prefix_lookup.get(
                        (
                            module_name,
                            router_name,
                        ),
                        "",
                    )
                )

                route_path = route.get("path") or ""

                full_path = self._join_paths(
                    inclusion_prefix,
                    local_prefix,
                    route_path,
                )

                routes.append(
                    {
                        "file": file_path,
                        "module": module_name,
                        **route,
                        "include_router_prefix": (
                            inclusion_prefix or None
                        ),
                        "router_prefix": (
                            local_prefix or None
                        ),
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
        internal_dependencies: list[
            dict[str, Any]
        ],
    ) -> dict[
        tuple[str, str],
        dict[str, str],
    ]:
        lookup: dict[
            tuple[str, str],
            dict[str, str],
        ] = {}

        for dependency in internal_dependencies:
            imported_name = dependency.get(
                "imported_name"
            )

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
                "module": dependency[
                    "target_module"
                ],
                "variable": imported_name,
            }

        return lookup

    def _build_statistics(
        self,
        parsed_files: list[dict[str, Any]],
        symbols: dict[str, list[dict[str, Any]]],
        routes: list[dict[str, Any]],
        internal_dependencies: list[
            dict[str, Any]
        ],
    ) -> dict[str, int]:
        files_with_syntax_errors = sum(
            1
            for parsed_file in parsed_files
            if parsed_file.get("syntax_error")
            is not None
        )

        return {
            "parsed_python_files": len(
                parsed_files
            ),
            "functions": len(
                symbols["functions"]
            ),
            "async_functions": len(
                symbols["async_functions"]
            ),
            "classes": len(
                symbols["classes"]
            ),
            "methods": len(
                symbols["methods"]
            ),
            "routes": len(routes),
            "internal_dependencies": len(
                internal_dependencies
            ),
            "files_with_syntax_errors": (
                files_with_syntax_errors
            ),
        }

    @staticmethod
    def _read_syntax_tree(
        file_path: Path,
    ) -> ast.Module | None:
        try:
            source_code = file_path.read_text(
                encoding="utf-8"
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
        aliases: dict[
            str,
            tuple[str, str | None],
        ] = {}

        for node in syntax_tree.body:
            if isinstance(node, ast.ImportFrom):
                module_name = node.module

                if not module_name:
                    continue

                for imported_name in node.names:
                    local_name = (
                        imported_name.asname
                        or imported_name.name
                    )

                    aliases[local_name] = (
                        module_name,
                        imported_name.name,
                    )

            elif isinstance(node, ast.Import):
                for imported_module in node.names:
                    local_name = (
                        imported_module.asname
                        or imported_module.name
                    )

                    aliases[local_name] = (
                        imported_module.name,
                        None,
                    )

        return aliases

    @staticmethod
    def _resolve_router_reference(
        expression: str,
        import_aliases: dict[
            str,
            tuple[str, str | None],
        ],
    ) -> tuple[str | None, str | None]:
        if expression in import_aliases:
            module_name, imported_name = (
                import_aliases[expression]
            )

            return (
                module_name,
                imported_name or expression,
            )

        expression_parts = expression.split(".")

        first_part = expression_parts[0]

        if first_part not in import_aliases:
            return None, None

        module_name, imported_name = (
            import_aliases[first_part]
        )

        if imported_name:
            variable_name = imported_name
        elif len(expression_parts) > 1:
            variable_name = expression_parts[-1]
        else:
            variable_name = first_part

        return module_name, variable_name

    @staticmethod
    def _get_keyword_literal(
        call: ast.Call,
        keyword_name: str,
    ) -> Any:
        for keyword in call.keywords:
            if keyword.arg != keyword_name:
                continue

            try:
                return ast.literal_eval(
                    keyword.value
                )
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
            module_parts = (
                path.with_suffix("").parts
            )

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
                module_name.startswith(
                    f"{imported_module}."
                )
                or imported_module.startswith(
                    f"{module_name}."
                )
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
            if isinstance(part, str)
            and part.strip("/")
        ]

        if not valid_parts:
            return "/"

        return "/" + "/".join(valid_parts)