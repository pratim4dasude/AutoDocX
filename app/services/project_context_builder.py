from collections import defaultdict
from pathlib import PurePosixPath
from typing import Any


class ProjectContextBuilder:
    """
    Converts a complete AutoDocX scan into structured project context.

    Supported modes:

    detailed
        Keeps complete module, symbol, route, import, dependency,
        and content-hash information.

    llm
        Produces a smaller context intended for LLM documentation
        generation.
    """

    SUPPORTED_MODES = {
        "detailed",
        "llm",
    }

    ENTRY_POINT_NAMES = {
        "main.py",
        "app.py",
        "server.py",
        "manage.py",
        "cli.py",
        "__main__.py",
    }

    CONFIG_FILE_NAMES = {
        "requirements.txt",
        "pyproject.toml",
        "setup.py",
        "setup.cfg",
        "tox.ini",
        "pytest.ini",
        "dockerfile",
        "docker-compose.yml",
        "docker-compose.yaml",
        ".env.example",
        ".gitignore",
        "package.json",
        "tsconfig.json",
        "alembic.ini",
    }

    DOCUMENTATION_FILE_NAMES = {
        "readme.md",
        "readme.txt",
        "contributing.md",
        "changelog.md",
        "license",
        "license.txt",
    }

    SCRIPT_EXTENSIONS = {
        ".bat",
        ".ps1",
        ".sh",
        ".cmd",
    }

    STANDARD_LIBRARY_MODULES = {
        "ast",
        "collections",
        "datetime",
        "hashlib",
        "json",
        "os",
        "pathlib",
        "re",
        "sys",
        "typing",
        "uuid",
    }

    def build_context(
        self,
        stored_scan: dict[str, Any],
        mode: str = "detailed",
    ) -> dict[str, Any]:
        normalized_mode = mode.strip().lower()

        if normalized_mode not in self.SUPPORTED_MODES:
            raise ValueError(
                "Unsupported context mode. "
                "Use 'detailed' or 'llm'."
            )

        scan_result = stored_scan.get(
            "scan_result",
            {},
        )

        self._validate_scan_result(
            scan_result=scan_result,
        )

        project_analysis = scan_result.get(
            "project_analysis",
            {},
        )

        parsed_files = scan_result.get(
            "parsed_files",
            [],
        )

        files = scan_result.get(
            "files",
            [],
        )

        project_statistics = project_analysis.get(
            "statistics",
            {},
        )

        modules = self._build_modules(
            parsed_files=parsed_files,
            project_analysis=project_analysis,
            mode=normalized_mode,
        )

        api_routes = self._build_api_routes(
            routes=project_analysis.get(
                "routes",
                [],
            )
        )

        dependencies = self._build_dependencies(
            dependencies=project_analysis.get(
                "internal_dependencies",
                [],
            )
        )

        important_files = self._build_important_files(
            files=files,
        )

        context_statistics = self._build_context_statistics(
            modules=modules,
            api_routes=api_routes,
            dependencies=dependencies,
            project_statistics=project_statistics,
        )

        context = {
            "context_mode": normalized_mode,
            "project": {
                "name": scan_result.get(
                    "project_name"
                ),
                "path": scan_result.get(
                    "project_path"
                ),
                "scan_id": stored_scan.get(
                    "scan_id"
                ),
                "scan_created_at": stored_scan.get(
                    "created_at"
                ),
                "total_files": scan_result.get(
                    "total_files",
                    0,
                ),
                "total_directories": (
                    scan_result.get(
                        "total_directories",
                        0,
                    )
                ),
                "total_size_bytes": (
                    scan_result.get(
                        "total_size_bytes",
                        0,
                    )
                ),
                "file_types": scan_result.get(
                    "file_types",
                    {},
                ),
            },
            "statistics": context_statistics,
            "important_files": important_files,
            "modules": modules,
            "api_routes": api_routes,
            "internal_dependencies": dependencies,
        }

        if normalized_mode == "llm":
            context = self._optimize_for_llm(
                context=context,
            )

        return context

    def _build_modules(
        self,
        parsed_files: list[dict[str, Any]],
        project_analysis: dict[str, Any],
        mode: str,
    ) -> list[dict[str, Any]]:
        module_lookup = {
            module.get("file"): module.get("module")
            for module in project_analysis.get(
                "modules",
                [],
            )
            if isinstance(module, dict)
        }

        dependency_lookup: dict[
            str,
            list[str],
        ] = defaultdict(list)

        for dependency in project_analysis.get(
            "internal_dependencies",
            [],
        ):
            if not isinstance(dependency, dict):
                continue

            source_file = dependency.get(
                "source_file"
            )

            target_module = dependency.get(
                "target_module"
            )

            imported_name = dependency.get(
                "imported_name"
            )

            if not source_file or not target_module:
                continue

            dependency_name = target_module

            if imported_name:
                dependency_name = (
                    f"{target_module}.{imported_name}"
                )

            if (
                dependency_name
                not in dependency_lookup[source_file]
            ):
                dependency_lookup[
                    source_file
                ].append(dependency_name)

        modules: list[dict[str, Any]] = []

        for parsed_file in parsed_files:
            if not isinstance(parsed_file, dict):
                continue

            file_path = parsed_file.get("path")

            if not file_path:
                continue

            functions = [
                self._compact_function(
                    function=function,
                    include_hash=(
                        mode == "detailed"
                    ),
                )
                for function in parsed_file.get(
                    "functions",
                    [],
                )
                if isinstance(function, dict)
            ]

            async_functions = [
                self._compact_function(
                    function=function,
                    include_hash=(
                        mode == "detailed"
                    ),
                )
                for function in parsed_file.get(
                    "async_functions",
                    [],
                )
                if isinstance(function, dict)
            ]

            classes = [
                self._compact_class(
                    class_data=class_data,
                    include_hash=(
                        mode == "detailed"
                    ),
                    include_private_methods=(
                        mode == "detailed"
                    ),
                )
                for class_data in parsed_file.get(
                    "classes",
                    [],
                )
                if isinstance(class_data, dict)
            ]

            routes = [
                self._compact_local_route(
                    route=route,
                )
                for route in parsed_file.get(
                    "routes",
                    [],
                )
                if isinstance(route, dict)
            ]

            imports = self._compact_imports(
                imports=parsed_file.get(
                    "imports",
                    [],
                ),
                mode=mode,
            )

            module_data = {
                "file": file_path,
                "module": module_lookup.get(
                    file_path
                ),
                "purpose_hint": (
                    self._build_module_purpose_hint(
                        file_path=file_path,
                        functions=functions,
                        classes=classes,
                        routes=routes,
                    )
                ),
                "imports": imports,
                "internal_dependencies": sorted(
                    dependency_lookup.get(
                        file_path,
                        [],
                    )
                ),
                "functions": functions,
                "async_functions": (
                    async_functions
                ),
                "classes": classes,
                "routes": routes,
                "syntax_error": parsed_file.get(
                    "syntax_error"
                ),
            }

            modules.append(module_data)

        return sorted(
            modules,
            key=lambda module: (
                module.get("file") or ""
            ),
        )

    @staticmethod
    def _compact_function(
        function: dict[str, Any],
        include_hash: bool,
    ) -> dict[str, Any]:
        function_data = {
            "name": function.get("name"),
            "arguments": function.get(
                "arguments",
                [],
            ),
            "returns": function.get(
                "returns"
            ),
            "docstring": function.get(
                "docstring"
            ),
            "decorators": function.get(
                "decorators",
                [],
            ),
        }

        if include_hash:
            function_data["content_hash"] = (
                function.get("content_hash")
            )

        return function_data

    def _compact_class(
        self,
        class_data: dict[str, Any],
        include_hash: bool,
        include_private_methods: bool,
    ) -> dict[str, Any]:
        methods: list[dict[str, Any]] = []

        for method in class_data.get(
            "methods",
            [],
        ):
            if not isinstance(method, dict):
                continue

            method_name = method.get(
                "name"
            )

            if (
                not include_private_methods
                and self._is_private_method(
                    method_name
                )
            ):
                continue

            method_data = {
                "name": method_name,
                "arguments": method.get(
                    "arguments",
                    [],
                ),
                "returns": method.get(
                    "returns"
                ),
                "docstring": method.get(
                    "docstring"
                ),
                "decorators": method.get(
                    "decorators",
                    [],
                ),
                "is_async": method.get(
                    "is_async",
                    False,
                ),
            }

            if include_hash:
                method_data["content_hash"] = (
                    method.get("content_hash")
                )

            methods.append(method_data)

        compact_class = {
            "name": class_data.get("name"),
            "bases": class_data.get(
                "bases",
                [],
            ),
            "docstring": class_data.get(
                "docstring"
            ),
            "decorators": class_data.get(
                "decorators",
                [],
            ),
            "methods": methods,
        }

        if include_hash:
            compact_class["content_hash"] = (
                class_data.get("content_hash")
            )

        return compact_class

    def _compact_imports(
        self,
        imports: list[dict[str, Any]],
        mode: str,
    ) -> list[dict[str, Any]]:
        compact_imports: list[
            dict[str, Any]
        ] = []

        for imported_item in imports:
            if not isinstance(
                imported_item,
                dict,
            ):
                continue

            module_name = imported_item.get(
                "module"
            )

            if (
                mode == "llm"
                and self._is_standard_library_import(
                    module_name
                )
            ):
                continue

            compact_imports.append(
                {
                    "type": imported_item.get(
                        "type"
                    ),
                    "module": module_name,
                    "name": imported_item.get(
                        "name"
                    ),
                    "alias": imported_item.get(
                        "alias"
                    ),
                }
            )

        return compact_imports

    @staticmethod
    def _compact_local_route(
        route: dict[str, Any],
    ) -> dict[str, Any]:
        return {
            "method": route.get("method"),
            "path": route.get("path"),
            "function_name": route.get(
                "function_name"
            ),
            "router_name": route.get(
                "router_name"
            ),
            "response_model": route.get(
                "response_model"
            ),
            "status_code": route.get(
                "status_code"
            ),
            "is_async": route.get(
                "is_async",
                False,
            ),
        }

    @staticmethod
    def _build_api_routes(
        routes: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        compact_routes: list[
            dict[str, Any]
        ] = []

        for route in routes:
            if not isinstance(route, dict):
                continue

            compact_routes.append(
                {
                    "method": route.get(
                        "method"
                    ),
                    "full_path": route.get(
                        "full_path"
                    ),
                    "local_path": route.get(
                        "path"
                    ),
                    "function_name": route.get(
                        "function_name"
                    ),
                    "file": route.get("file"),
                    "module": route.get(
                        "module"
                    ),
                    "router_name": route.get(
                        "router_name"
                    ),
                    "response_model": route.get(
                        "response_model"
                    ),
                    "status_code": route.get(
                        "status_code"
                    ),
                    "is_async": route.get(
                        "is_async",
                        False,
                    ),
                }
            )

        return sorted(
            compact_routes,
            key=lambda route: (
                route.get("full_path") or "",
                route.get("method") or "",
            ),
        )

    @staticmethod
    def _build_dependencies(
        dependencies: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        compact_dependencies: list[
            dict[str, Any]
        ] = []

        seen_dependencies: set[
            tuple[Any, ...]
        ] = set()

        for dependency in dependencies:
            if not isinstance(dependency, dict):
                continue

            compact_dependency = {
                "source_file": dependency.get(
                    "source_file"
                ),
                "source_module": dependency.get(
                    "source_module"
                ),
                "target_file": dependency.get(
                    "target_file"
                ),
                "target_module": dependency.get(
                    "target_module"
                ),
                "imported_name": dependency.get(
                    "imported_name"
                ),
                "alias": dependency.get(
                    "alias"
                ),
                "import_type": dependency.get(
                    "import_type"
                ),
            }

            identity = (
                compact_dependency[
                    "source_module"
                ],
                compact_dependency[
                    "target_module"
                ],
                compact_dependency[
                    "imported_name"
                ],
                compact_dependency["alias"],
            )

            if identity in seen_dependencies:
                continue

            seen_dependencies.add(identity)

            compact_dependencies.append(
                compact_dependency
            )

        return sorted(
            compact_dependencies,
            key=lambda dependency: (
                dependency.get(
                    "source_module"
                )
                or "",
                dependency.get(
                    "target_module"
                )
                or "",
                dependency.get(
                    "imported_name"
                )
                or "",
            ),
        )

    def _optimize_for_llm(
        self,
        context: dict[str, Any],
    ) -> dict[str, Any]:
        optimized_modules: list[
            dict[str, Any]
        ] = []

        for module in context.get(
            "modules",
            [],
        ):
            if not isinstance(module, dict):
                continue

            if self._is_empty_package_module(
                module=module,
            ):
                continue

            optimized_module = {
                "file": module.get("file"),
                "module": module.get("module"),
                "purpose_hint": module.get(
                    "purpose_hint"
                ),
                "imports": module.get(
                    "imports",
                    [],
                ),
                "functions": module.get(
                    "functions",
                    [],
                ),
                "async_functions": (
                    module.get(
                        "async_functions",
                        [],
                    )
                ),
                "classes": module.get(
                    "classes",
                    [],
                ),
                "syntax_error": module.get(
                    "syntax_error"
                ),
            }

            optimized_modules.append(
                self._remove_empty_values(
                    optimized_module
                )
            )

        optimized_dependencies = [
            {
                "source_module": dependency.get(
                    "source_module"
                ),
                "target_module": dependency.get(
                    "target_module"
                ),
                "imported_name": dependency.get(
                    "imported_name"
                ),
                "alias": dependency.get(
                    "alias"
                ),
            }
            for dependency in context.get(
                "internal_dependencies",
                [],
            )
            if isinstance(dependency, dict)
        ]

        optimized_context = {
            "context_mode": "llm",
            "project": context.get(
                "project",
                {},
            ),
            "statistics": context.get(
                "statistics",
                {},
            ),
            "important_files": context.get(
                "important_files",
                {},
            ),
            "modules": optimized_modules,
            "api_routes": context.get(
                "api_routes",
                [],
            ),
            "internal_dependencies": (
                optimized_dependencies
            ),
        }

        return self._remove_empty_values(
            optimized_context
        )

    def _build_important_files(
        self,
        files: list[str],
    ) -> dict[str, list[str]]:
        entry_points: list[str] = []
        configuration_files: list[str] = []
        documentation_files: list[str] = []
        scripts: list[str] = []

        for file_path in files:
            normalized_path = (
                PurePosixPath(file_path)
            )

            file_name = (
                normalized_path.name.lower()
            )

            file_extension = (
                normalized_path.suffix.lower()
            )

            if (
                file_name
                in self.ENTRY_POINT_NAMES
            ):
                entry_points.append(file_path)

            if (
                file_name
                in self.CONFIG_FILE_NAMES
            ):
                configuration_files.append(
                    file_path
                )

            if (
                file_name
                in self.DOCUMENTATION_FILE_NAMES
            ):
                documentation_files.append(
                    file_path
                )

            if (
                file_extension
                in self.SCRIPT_EXTENSIONS
            ):
                scripts.append(file_path)

        return {
            "entry_points": sorted(
                entry_points
            ),
            "configuration_files": sorted(
                configuration_files
            ),
            "documentation_files": sorted(
                documentation_files
            ),
            "scripts": sorted(scripts),
        }

    @staticmethod
    def _build_context_statistics(
        modules: list[dict[str, Any]],
        api_routes: list[dict[str, Any]],
        dependencies: list[dict[str, Any]],
        project_statistics: dict[str, Any],
    ) -> dict[str, int]:
        modules_with_syntax_errors = sum(
            1
            for module in modules
            if module.get("syntax_error")
        )

        return {
            "python_modules": len(modules),
            "functions": int(
                project_statistics.get(
                    "functions",
                    0,
                )
            ),
            "async_functions": int(
                project_statistics.get(
                    "async_functions",
                    0,
                )
            ),
            "classes": int(
                project_statistics.get(
                    "classes",
                    0,
                )
            ),
            "methods": int(
                project_statistics.get(
                    "methods",
                    0,
                )
            ),
            "api_routes": len(api_routes),
            "internal_dependencies": len(
                dependencies
            ),
            "modules_with_syntax_errors": (
                modules_with_syntax_errors
            ),
        }

    @staticmethod
    def _build_module_purpose_hint(
        file_path: str,
        functions: list[dict[str, Any]],
        classes: list[dict[str, Any]],
        routes: list[dict[str, Any]],
    ) -> str:
        path_lower = file_path.lower()

        if file_path.endswith("__init__.py"):
            return (
                "Python package initialization module."
            )

        if (
            PurePosixPath(file_path)
            .name
            .lower()
            == "main.py"
        ):
            return (
                "Application entry point and "
                "FastAPI startup module."
            )

        if routes:
            return (
                "Defines API routes and request handlers."
            )

        if "/models/" in f"/{path_lower}":
            return (
                "Defines application data models "
                "and validation schemas."
            )

        if "/services/" in f"/{path_lower}":
            class_names = [
                class_data.get("name")
                for class_data in classes
                if class_data.get("name")
            ]

            if class_names:
                return (
                    "Provides application service logic "
                    f"through {', '.join(class_names)}."
                )

            return (
                "Provides application service logic."
            )

        if "/core/" in f"/{path_lower}":
            return (
                "Contains core application configuration "
                "or shared infrastructure."
            )

        function_names = [
            function.get("name")
            for function in functions
            if function.get("name")
        ]

        class_names = [
            class_data.get("name")
            for class_data in classes
            if class_data.get("name")
        ]

        if class_names:
            return (
                "Defines classes: "
                + ", ".join(class_names)
                + "."
            )

        if function_names:
            return (
                "Defines functions: "
                + ", ".join(function_names)
                + "."
            )

        return (
            "Python module with no discovered "
            "functions or classes."
        )

    @staticmethod
    def _is_private_method(
        method_name: Any,
    ) -> bool:
        if not isinstance(method_name, str):
            return False

        if method_name in {
            "__init__",
            "__call__",
            "__enter__",
            "__exit__",
        }:
            return False

        return method_name.startswith("_")

    def _is_standard_library_import(
        self,
        module_name: Any,
    ) -> bool:
        if not isinstance(module_name, str):
            return False

        top_level_module = (
            module_name.lstrip(".").split(".")[0]
        )

        return (
            top_level_module
            in self.STANDARD_LIBRARY_MODULES
        )

    @staticmethod
    def _is_empty_package_module(
        module: dict[str, Any],
    ) -> bool:
        file_path = module.get("file")

        if not isinstance(file_path, str):
            return False

        if not file_path.endswith("__init__.py"):
            return False

        return not any(
            [
                module.get("functions"),
                module.get("async_functions"),
                module.get("classes"),
                module.get("imports"),
                module.get("syntax_error"),
            ]
        )

    def _remove_empty_values(
        self,
        value: Any,
    ) -> Any:
        if isinstance(value, dict):
            cleaned_dictionary = {}

            for key, item in value.items():
                cleaned_item = (
                    self._remove_empty_values(
                        item
                    )
                )

                if cleaned_item in (
                    None,
                    "",
                    [],
                    {},
                ):
                    continue

                cleaned_dictionary[
                    key
                ] = cleaned_item

            return cleaned_dictionary

        if isinstance(value, list):
            cleaned_list = []

            for item in value:
                cleaned_item = (
                    self._remove_empty_values(
                        item
                    )
                )

                if cleaned_item in (
                    None,
                    "",
                    [],
                    {},
                ):
                    continue

                cleaned_list.append(
                    cleaned_item
                )

            return cleaned_list

        return value

    @staticmethod
    def _validate_scan_result(
        scan_result: Any,
    ) -> None:
        if not isinstance(scan_result, dict):
            raise ValueError(
                "Stored scan result is invalid."
            )

        if not scan_result.get("project_name"):
            raise ValueError(
                "Stored scan does not contain "
                "a project name."
            )

        if not isinstance(
            scan_result.get("parsed_files"),
            list,
        ):
            raise ValueError(
                "Stored scan does not contain "
                "valid parsed Python files."
            )

        if not isinstance(
            scan_result.get(
                "project_analysis"
            ),
            dict,
        ):
            raise ValueError(
                "Stored scan does not contain "
                "valid project analysis."
            )