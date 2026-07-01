import ast
from pathlib import Path
from typing import Any


class PythonCodeParser:
    """
    Reads a Python file and extracts its code structure.

    Extracted information:
    - imports
    - functions
    - async functions
    - classes
    - class methods
    - FastAPI routes
    - syntax errors
    """

    FASTAPI_METHODS = {
        "get",
        "post",
        "put",
        "patch",
        "delete",
        "options",
        "head",
        "websocket",
    }

    def parse_file(
        self,
        project_root: Path,
        relative_file_path: str,
    ) -> dict[str, Any]:
        file_path = project_root / relative_file_path

        result: dict[str, Any] = {
            "path": relative_file_path,
            "language": "python",
            "imports": [],
            "functions": [],
            "async_functions": [],
            "classes": [],
            "routes": [],
            "syntax_error": None,
        }

        try:
            source_code = file_path.read_text(
                encoding="utf-8",
                errors="replace",
            )

            syntax_tree = ast.parse(
                source_code,
                filename=str(file_path),
            )

        except SyntaxError as error:
            result["syntax_error"] = {
                "message": error.msg,
                "line": error.lineno,
                "column": error.offset,
            }
            return result

        except OSError as error:
            result["syntax_error"] = {
                "message": f"Unable to read file: {error}",
                "line": None,
                "column": None,
            }
            return result

        for node in syntax_tree.body:
            if isinstance(node, ast.Import):
                result["imports"].extend(
                    self._extract_import(node)
                )

            elif isinstance(node, ast.ImportFrom):
                result["imports"].extend(
                    self._extract_import_from(node)
                )

            elif isinstance(node, ast.FunctionDef):
                function_data = self._extract_function(node)
                result["functions"].append(function_data)

                route_data = self._extract_fastapi_routes(node)
                result["routes"].extend(route_data)

            elif isinstance(node, ast.AsyncFunctionDef):
                function_data = self._extract_function(node)
                result["async_functions"].append(function_data)

                route_data = self._extract_fastapi_routes(node)
                result["routes"].extend(route_data)

            elif isinstance(node, ast.ClassDef):
                class_data = self._extract_class(node)
                result["classes"].append(class_data)

        return result

    @staticmethod
    def _extract_import(
        node: ast.Import,
    ) -> list[dict[str, Any]]:
        imports: list[dict[str, Any]] = []

        for imported_name in node.names:
            imports.append(
                {
                    "type": "import",
                    "module": imported_name.name,
                    "name": None,
                    "alias": imported_name.asname,
                    "line": node.lineno,
                }
            )

        return imports

    @staticmethod
    def _extract_import_from(
        node: ast.ImportFrom,
    ) -> list[dict[str, Any]]:
        imports: list[dict[str, Any]] = []

        module_name = node.module or ""

        if node.level:
            module_name = f"{'.' * node.level}{module_name}"

        for imported_name in node.names:
            imports.append(
                {
                    "type": "from_import",
                    "module": module_name,
                    "name": imported_name.name,
                    "alias": imported_name.asname,
                    "line": node.lineno,
                }
            )

        return imports

    def _extract_function(
        self,
        node: ast.FunctionDef | ast.AsyncFunctionDef,
    ) -> dict[str, Any]:
        return {
            "name": node.name,
            "line": node.lineno,
            "end_line": node.end_lineno,
            "arguments": self._extract_arguments(node.args),
            "returns": self._node_to_string(node.returns),
            "docstring": ast.get_docstring(node),
            "decorators": [
                self._node_to_string(decorator)
                for decorator in node.decorator_list
            ],
        }

    def _extract_class(
        self,
        node: ast.ClassDef,
    ) -> dict[str, Any]:
        methods: list[dict[str, Any]] = []

        for child_node in node.body:
            if isinstance(
                child_node,
                (ast.FunctionDef, ast.AsyncFunctionDef),
            ):
                method_data = self._extract_function(child_node)

                method_data["is_async"] = isinstance(
                    child_node,
                    ast.AsyncFunctionDef,
                )

                methods.append(method_data)

        return {
            "name": node.name,
            "line": node.lineno,
            "end_line": node.end_lineno,
            "bases": [
                self._node_to_string(base)
                for base in node.bases
            ],
            "docstring": ast.get_docstring(node),
            "decorators": [
                self._node_to_string(decorator)
                for decorator in node.decorator_list
            ],
            "methods": methods,
        }

    def _extract_fastapi_routes(
        self,
        node: ast.FunctionDef | ast.AsyncFunctionDef,
    ) -> list[dict[str, Any]]:
        routes: list[dict[str, Any]] = []

        for decorator in node.decorator_list:
            if not isinstance(decorator, ast.Call):
                continue

            if not isinstance(decorator.func, ast.Attribute):
                continue

            http_method = decorator.func.attr.lower()

            if http_method not in self.FASTAPI_METHODS:
                continue

            route_path = None

            if decorator.args:
                route_path = self._get_literal_value(
                    decorator.args[0]
                )

            route_name = None
            response_model = None
            status_code = None

            for keyword in decorator.keywords:
                if keyword.arg == "name":
                    route_name = self._get_literal_value(
                        keyword.value
                    )

                elif keyword.arg == "response_model":
                    response_model = self._node_to_string(
                        keyword.value
                    )

                elif keyword.arg == "status_code":
                    status_code = self._get_literal_value(
                        keyword.value
                    )

            routes.append(
                {
                    "function_name": node.name,
                    "method": http_method.upper(),
                    "path": route_path,
                    "line": node.lineno,
                    "is_async": isinstance(
                        node,
                        ast.AsyncFunctionDef,
                    ),
                    "router_name": self._node_to_string(
                        decorator.func.value
                    ),
                    "route_name": route_name,
                    "response_model": response_model,
                    "status_code": status_code,
                }
            )

        return routes

    def _extract_arguments(
        self,
        arguments: ast.arguments,
    ) -> list[dict[str, Any]]:
        extracted_arguments: list[dict[str, Any]] = []

        positional_arguments = (
            list(arguments.posonlyargs)
            + list(arguments.args)
        )

        positional_defaults = (
            [None]
            * (
                len(positional_arguments)
                - len(arguments.defaults)
            )
            + list(arguments.defaults)
        )

        for argument, default_value in zip(
            positional_arguments,
            positional_defaults,
        ):
            extracted_arguments.append(
                {
                    "name": argument.arg,
                    "annotation": self._node_to_string(
                        argument.annotation
                    ),
                    "default": self._node_to_string(
                        default_value
                    ),
                }
            )

        for argument, default_value in zip(
            arguments.kwonlyargs,
            arguments.kw_defaults,
        ):
            extracted_arguments.append(
                {
                    "name": argument.arg,
                    "annotation": self._node_to_string(
                        argument.annotation
                    ),
                    "default": self._node_to_string(
                        default_value
                    ),
                }
            )

        if arguments.vararg:
            extracted_arguments.append(
                {
                    "name": f"*{arguments.vararg.arg}",
                    "annotation": self._node_to_string(
                        arguments.vararg.annotation
                    ),
                    "default": None,
                }
            )

        if arguments.kwarg:
            extracted_arguments.append(
                {
                    "name": f"**{arguments.kwarg.arg}",
                    "annotation": self._node_to_string(
                        arguments.kwarg.annotation
                    ),
                    "default": None,
                }
            )

        return extracted_arguments

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
    def _get_literal_value(
        node: ast.AST,
    ) -> Any:
        try:
            return ast.literal_eval(node)
        except Exception:
            try:
                return ast.unparse(node)
            except Exception:
                return None