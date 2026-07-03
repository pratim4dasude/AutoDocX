import ast
import hashlib
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
    - function content hashes
    - method content hashes
    - class content hashes
    - syntax errors
    """

    HTTP_METHODS = {
        "get",
        "post",
        "put",
        "patch",
        "delete",
        "options",
        "head",
        "trace",
        "websocket",
    }

    def parse_file(
        self,
        project_root: Path,
        relative_file_path: str,
    ) -> dict[str, Any]:
        file_path = (
            project_root / relative_file_path
        )

        parsed_result: dict[str, Any] = {
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
                encoding="utf-8"
            )

        except UnicodeDecodeError:
            try:
                source_code = file_path.read_text(
                    encoding="utf-8-sig"
                )
            except (
                OSError,
                UnicodeDecodeError,
            ) as error:
                parsed_result["syntax_error"] = {
                    "message": (
                        "Unable to read Python file: "
                        f"{error}"
                    ),
                    "line": None,
                    "offset": None,
                }

                return parsed_result

        except OSError as error:
            parsed_result["syntax_error"] = {
                "message": (
                    "Unable to read Python file: "
                    f"{error}"
                ),
                "line": None,
                "offset": None,
            }

            return parsed_result

        try:
            syntax_tree = ast.parse(
                source_code,
                filename=str(file_path),
            )

        except SyntaxError as error:
            parsed_result["syntax_error"] = {
                "message": error.msg,
                "line": error.lineno,
                "offset": error.offset,
            }

            return parsed_result

        for node in syntax_tree.body:
            if isinstance(node, ast.Import):
                parsed_result["imports"].extend(
                    self._extract_import(node)
                )

            elif isinstance(node, ast.ImportFrom):
                parsed_result["imports"].extend(
                    self._extract_import_from(node)
                )

            elif isinstance(
                node,
                ast.AsyncFunctionDef,
            ):
                parsed_result[
                    "async_functions"
                ].append(
                    self._extract_function(node)
                )

                parsed_result["routes"].extend(
                    self._extract_fastapi_routes(
                        node
                    )
                )

            elif isinstance(
                node,
                ast.FunctionDef,
            ):
                parsed_result["functions"].append(
                    self._extract_function(node)
                )

                parsed_result["routes"].extend(
                    self._extract_fastapi_routes(
                        node
                    )
                )

            elif isinstance(node, ast.ClassDef):
                parsed_result["classes"].append(
                    self._extract_class(node)
                )

        return parsed_result

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
                    "line": getattr(
                        node,
                        "lineno",
                        None,
                    ),
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
            module_name = (
                ("." * node.level)
                + module_name
            )

        for imported_name in node.names:
            imports.append(
                {
                    "type": "from_import",
                    "module": module_name,
                    "name": imported_name.name,
                    "alias": imported_name.asname,
                    "line": getattr(
                        node,
                        "lineno",
                        None,
                    ),
                }
            )

        return imports

    def _extract_function(
        self,
        node: (
            ast.FunctionDef
            | ast.AsyncFunctionDef
        ),
    ) -> dict[str, Any]:
        return {
            "name": node.name,
            "line": getattr(
                node,
                "lineno",
                None,
            ),
            "end_line": getattr(
                node,
                "end_lineno",
                None,
            ),
            "arguments": self._extract_arguments(
                node.args
            ),
            "returns": self._node_to_string(
                node.returns
            ),
            "docstring": ast.get_docstring(
                node
            ),
            "decorators": [
                decorator
                for decorator in (
                    self._node_to_string(
                        decorator_node
                    )
                    for decorator_node
                    in node.decorator_list
                )
                if decorator is not None
            ],
            "content_hash": (
                self._calculate_node_hash(node)
            ),
        }

    def _extract_class(
        self,
        node: ast.ClassDef,
    ) -> dict[str, Any]:
        methods: list[dict[str, Any]] = []

        for class_node in node.body:
            if isinstance(
                class_node,
                (
                    ast.FunctionDef,
                    ast.AsyncFunctionDef,
                ),
            ):
                method_data = (
                    self._extract_function(
                        class_node
                    )
                )

                method_data["is_async"] = (
                    isinstance(
                        class_node,
                        ast.AsyncFunctionDef,
                    )
                )

                methods.append(method_data)

        return {
            "name": node.name,
            "line": getattr(
                node,
                "lineno",
                None,
            ),
            "end_line": getattr(
                node,
                "end_lineno",
                None,
            ),
            "bases": [
                base_name
                for base_name in (
                    self._node_to_string(base)
                    for base in node.bases
                )
                if base_name is not None
            ],
            "docstring": ast.get_docstring(
                node
            ),
            "decorators": [
                decorator
                for decorator in (
                    self._node_to_string(
                        decorator_node
                    )
                    for decorator_node
                    in node.decorator_list
                )
                if decorator is not None
            ],
            "content_hash": (
                self._calculate_node_hash(node)
            ),
            "methods": methods,
        }

    def _extract_fastapi_routes(
        self,
        node: (
            ast.FunctionDef
            | ast.AsyncFunctionDef
        ),
    ) -> list[dict[str, Any]]:
        routes: list[dict[str, Any]] = []

        for decorator in node.decorator_list:
            if not isinstance(
                decorator,
                ast.Call,
            ):
                continue

            if not isinstance(
                decorator.func,
                ast.Attribute,
            ):
                continue

            method_name = (
                decorator.func.attr.lower()
            )

            if (
                method_name
                not in self.HTTP_METHODS
            ):
                continue

            router_name = self._node_to_string(
                decorator.func.value
            )

            route_path = None

            if decorator.args:
                route_path = (
                    self._get_literal_value(
                        decorator.args[0]
                    )
                )

            if not isinstance(
                route_path,
                str,
            ):
                route_path = None

            route_name = (
                self._get_call_keyword_value(
                    decorator,
                    "name",
                )
            )

            response_model = (
                self._get_call_keyword_string(
                    decorator,
                    "response_model",
                )
            )

            status_code = (
                self._get_call_keyword_string(
                    decorator,
                    "status_code",
                )
            )

            routes.append(
                {
                    "function_name": node.name,
                    "method": (
                        method_name.upper()
                    ),
                    "path": route_path,
                    "line": getattr(
                        node,
                        "lineno",
                        None,
                    ),
                    "is_async": isinstance(
                        node,
                        ast.AsyncFunctionDef,
                    ),
                    "router_name": router_name,
                    "route_name": (
                        route_name
                        if isinstance(
                            route_name,
                            str,
                        )
                        else None
                    ),
                    "response_model": (
                        response_model
                    ),
                    "status_code": status_code,
                }
            )

        return routes

    def _extract_arguments(
        self,
        arguments: ast.arguments,
    ) -> list[dict[str, Any]]:
        extracted_arguments: list[
            dict[str, Any]
        ] = []

        positional_arguments = [
            *arguments.posonlyargs,
            *arguments.args,
        ]

        positional_defaults: list[
            ast.expr | None
        ] = [
            None
        ] * (
            len(positional_arguments)
            - len(arguments.defaults)
        ) + list(arguments.defaults)

        for argument, default_value in zip(
            positional_arguments,
            positional_defaults,
            strict=True,
        ):
            extracted_arguments.append(
                {
                    "name": argument.arg,
                    "annotation": (
                        self._node_to_string(
                            argument.annotation
                        )
                    ),
                    "default": (
                        self._node_to_string(
                            default_value
                        )
                        if default_value
                        is not None
                        else None
                    ),
                }
            )

        if arguments.vararg is not None:
            extracted_arguments.append(
                {
                    "name": (
                        f"*{arguments.vararg.arg}"
                    ),
                    "annotation": (
                        self._node_to_string(
                            arguments
                            .vararg
                            .annotation
                        )
                    ),
                    "default": None,
                }
            )

        for keyword_argument, default_value in zip(
            arguments.kwonlyargs,
            arguments.kw_defaults,
            strict=True,
        ):
            extracted_arguments.append(
                {
                    "name": (
                        keyword_argument.arg
                    ),
                    "annotation": (
                        self._node_to_string(
                            keyword_argument
                            .annotation
                        )
                    ),
                    "default": (
                        self._node_to_string(
                            default_value
                        )
                        if default_value
                        is not None
                        else None
                    ),
                }
            )

        if arguments.kwarg is not None:
            extracted_arguments.append(
                {
                    "name": (
                        f"**{arguments.kwarg.arg}"
                    ),
                    "annotation": (
                        self._node_to_string(
                            arguments
                            .kwarg
                            .annotation
                        )
                    ),
                    "default": None,
                }
            )

        return extracted_arguments

    @staticmethod
    def _calculate_node_hash(
        node: ast.AST,
    ) -> str:
        """
        Creates a stable SHA-256 hash from an AST node.

        The hash changes when the actual Python structure
        changes, including:

        - function body
        - method body
        - arguments
        - decorators
        - return annotation
        - class bases
        - class methods

        Formatting-only changes generally do not change
        this hash.
        """

        normalized_node = ast.dump(
            node,
            annotate_fields=True,
            include_attributes=False,
        )

        return hashlib.sha256(
            normalized_node.encode("utf-8")
        ).hexdigest()

    def _get_call_keyword_value(
        self,
        call_node: ast.Call,
        keyword_name: str,
    ) -> Any:
        for keyword in call_node.keywords:
            if keyword.arg != keyword_name:
                continue

            return self._get_literal_value(
                keyword.value
            )

        return None

    def _get_call_keyword_string(
        self,
        call_node: ast.Call,
        keyword_name: str,
    ) -> str | None:
        for keyword in call_node.keywords:
            if keyword.arg != keyword_name:
                continue

            literal_value = (
                self._get_literal_value(
                    keyword.value
                )
            )

            if isinstance(
                literal_value,
                (
                    str,
                    int,
                    float,
                    bool,
                ),
            ):
                return str(literal_value)

            return self._node_to_string(
                keyword.value
            )

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
    def _get_literal_value(
        node: ast.AST,
    ) -> Any:
        try:
            return ast.literal_eval(node)

        except (
            ValueError,
            TypeError,
        ):
            return None