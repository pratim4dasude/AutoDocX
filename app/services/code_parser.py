import ast
import hashlib
from pathlib import Path
from typing import Any


class PythonCodeParser:
    """
    Reads a Python file and extracts developer-documentation-ready
    structure from it.

    Extracted information:
    - imports
    - module constants
    - functions
    - async functions
    - classes
    - class attributes
    - class methods
    - function/method signatures
    - arguments with annotations/defaults
    - return annotations
    - docstrings
    - decorators
    - FastAPI routes
    - source previews
    - content hashes
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
        file_path = project_root / relative_file_path

        parsed_result: dict[str, Any] = {
            "path": relative_file_path,
            "language": "python",
            "module_docstring": None,
            "imports": [],
            "constants": [],
            "functions": [],
            "async_functions": [],
            "classes": [],
            "routes": [],
            "syntax_error": None,
        }

        try:
            source_code = file_path.read_text(
                encoding="utf-8",
            )

        except UnicodeDecodeError:
            try:
                source_code = file_path.read_text(
                    encoding="utf-8-sig",
                )

            except (OSError, UnicodeDecodeError) as error:
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

        source_lines = source_code.splitlines()

        parsed_result["module_docstring"] = ast.get_docstring(
            syntax_tree,
        )

        for node in syntax_tree.body:
            if isinstance(node, ast.Import):
                parsed_result["imports"].extend(
                    self._extract_import(node),
                )

            elif isinstance(node, ast.ImportFrom):
                parsed_result["imports"].extend(
                    self._extract_import_from(node),
                )

            elif isinstance(node, (ast.Assign, ast.AnnAssign)):
                constant = self._extract_constant(node)

                if constant is not None:
                    parsed_result["constants"].append(
                        constant,
                    )

            elif isinstance(node, ast.AsyncFunctionDef):
                function_data = self._extract_function(
                    node=node,
                    source_lines=source_lines,
                    qualified_prefix=None,
                )

                parsed_result["async_functions"].append(
                    function_data,
                )

                parsed_result["routes"].extend(
                    self._extract_fastapi_routes(
                        node=node,
                        source_lines=source_lines,
                    )
                )

            elif isinstance(node, ast.FunctionDef):
                function_data = self._extract_function(
                    node=node,
                    source_lines=source_lines,
                    qualified_prefix=None,
                )

                parsed_result["functions"].append(
                    function_data,
                )

                parsed_result["routes"].extend(
                    self._extract_fastapi_routes(
                        node=node,
                        source_lines=source_lines,
                    )
                )

            elif isinstance(node, ast.ClassDef):
                class_data = self._extract_class(
                    node=node,
                    source_lines=source_lines,
                )

                parsed_result["classes"].append(
                    class_data,
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
                    "line": getattr(node, "lineno", None),
                    "statement": (
                        f"import {imported_name.name}"
                        if imported_name.asname is None
                        else (
                            f"import {imported_name.name} "
                            f"as {imported_name.asname}"
                        )
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
            module_name = ("." * node.level) + module_name

        for imported_name in node.names:
            imports.append(
                {
                    "type": "from_import",
                    "module": module_name,
                    "name": imported_name.name,
                    "alias": imported_name.asname,
                    "line": getattr(node, "lineno", None),
                    "statement": (
                        f"from {module_name} import "
                        f"{imported_name.name}"
                        if imported_name.asname is None
                        else (
                            f"from {module_name} import "
                            f"{imported_name.name} "
                            f"as {imported_name.asname}"
                        )
                    ),
                }
            )

        return imports

    def _extract_constant(
        self,
        node: ast.Assign | ast.AnnAssign,
    ) -> dict[str, Any] | None:
        if isinstance(node, ast.Assign):
            if not node.targets:
                return None

            target = node.targets[0]
            annotation = None
            value_node = node.value

        else:
            target = node.target
            annotation = self._node_to_string(node.annotation)
            value_node = node.value

        name = self._node_to_string(target)

        if not name:
            return None

        clean_name = name.strip()

        if not clean_name.isupper():
            return None

        return {
            "name": clean_name,
            "annotation": annotation,
            "value": self._node_to_string(value_node),
            "line": getattr(node, "lineno", None),
        }

    def _extract_function(
        self,
        node: ast.FunctionDef | ast.AsyncFunctionDef,
        source_lines: list[str],
        qualified_prefix: str | None,
    ) -> dict[str, Any]:
        is_async = isinstance(node, ast.AsyncFunctionDef)

        qualified_name = (
            f"{qualified_prefix}.{node.name}"
            if qualified_prefix
            else node.name
        )

        arguments = self._extract_arguments(node.args)

        signature = self._build_function_signature(
            name=node.name,
            arguments=arguments,
            returns=self._node_to_string(node.returns),
            is_async=is_async,
        )

        return {
            "name": node.name,
            "qualified_name": qualified_name,
            "line": getattr(node, "lineno", None),
            "end_line": getattr(node, "end_lineno", None),
            "is_async": is_async,
            "signature": signature,
            "arguments": arguments,
            "returns": self._node_to_string(node.returns),
            "docstring": ast.get_docstring(node),
            "decorators": [
                decorator
                for decorator in (
                    self._node_to_string(decorator_node)
                    for decorator_node in node.decorator_list
                )
                if decorator is not None
            ],
            "source_preview": self._get_source_preview(
                source_lines=source_lines,
                node=node,
                max_lines=18,
            ),
            "called_functions": self._extract_called_functions(node),
            "called_functions_preview": self._build_called_functions_preview(node),
            "content_hash": self._calculate_node_hash(node),
        }

    @staticmethod
    def _extract_called_functions(
        node: ast.FunctionDef | ast.AsyncFunctionDef,
    ) -> list[str]:
        called_functions: list[str] = []

        for child in ast.walk(node):
            if not isinstance(child, ast.Call):
                continue

            call_name = PythonCodeParser._get_call_name(
                child.func,
            )

            if call_name and call_name not in called_functions:
                called_functions.append(call_name)

        return called_functions

    @staticmethod
    def _get_call_name(
        node: ast.AST,
    ) -> str:
        if isinstance(node, ast.Name):
            return node.id

        if isinstance(node, ast.Attribute):
            parent_name = PythonCodeParser._get_call_name(
                node.value,
            )

            if parent_name:
                return f"{parent_name}.{node.attr}"

            return node.attr

        if isinstance(node, ast.Call):
            return PythonCodeParser._get_call_name(
                node.func,
            )

        if isinstance(node, ast.Subscript):
            return PythonCodeParser._get_call_name(
                node.value,
            )

        return ""

    @staticmethod
    def _build_called_functions_preview(
        node: ast.FunctionDef | ast.AsyncFunctionDef,
    ) -> list[str]:
        previews: list[str] = []

        for child in ast.walk(node):
            if not isinstance(child, ast.Call):
                continue

            call_name = PythonCodeParser._get_call_name(
                child.func,
            )

            if not call_name:
                continue

            argument_parts: list[str] = []

            for argument in child.args:
                argument_text = PythonCodeParser._node_to_string(
                    argument,
                )

                if argument_text:
                    argument_parts.append(argument_text)

            for keyword in child.keywords:
                if keyword.arg is None:
                    continue

                value_text = PythonCodeParser._node_to_string(
                    keyword.value,
                )

                if not value_text:
                    value_text = "..."

                argument_parts.append(
                    f"{keyword.arg}={value_text}"
                )

            if argument_parts:
                preview = (
                    f"{call_name}("
                    + ", ".join(argument_parts)
                    + ")"
                )
            else:
                preview = f"{call_name}(...)"

            if preview not in previews:
                previews.append(preview)

        return previews

    def _extract_class(
        self,
        node: ast.ClassDef,
        source_lines: list[str],
    ) -> dict[str, Any]:
        methods: list[dict[str, Any]] = []
        attributes: list[dict[str, Any]] = []

        for class_node in node.body:
            if isinstance(
                class_node,
                (ast.FunctionDef, ast.AsyncFunctionDef),
            ):
                method_data = self._extract_function(
                    node=class_node,
                    source_lines=source_lines,
                    qualified_prefix=node.name,
                )

                methods.append(method_data)

            elif isinstance(
                class_node,
                (ast.Assign, ast.AnnAssign),
            ):
                attribute = self._extract_class_attribute(
                    class_node,
                )

                if attribute is not None:
                    attributes.append(attribute)

        bases = [
            base_name
            for base_name in (
                self._node_to_string(base)
                for base in node.bases
            )
            if base_name is not None
        ]

        class_signature = self._build_class_signature(
            class_name=node.name,
            bases=bases,
        )

        return {
            "name": node.name,
            "qualified_name": node.name,
            "line": getattr(node, "lineno", None),
            "end_line": getattr(node, "end_lineno", None),
            "signature": class_signature,
            "bases": bases,
            "docstring": ast.get_docstring(node),
            "decorators": [
                decorator
                for decorator in (
                    self._node_to_string(decorator_node)
                    for decorator_node in node.decorator_list
                )
                if decorator is not None
            ],
            "attributes": attributes,
            "methods": methods,
            "source_preview": self._get_source_preview(
                source_lines=source_lines,
                node=node,
                max_lines=22,
            ),
            "content_hash": self._calculate_node_hash(node),
        }

    def _extract_class_attribute(
        self,
        node: ast.Assign | ast.AnnAssign,
    ) -> dict[str, Any] | None:
        if isinstance(node, ast.Assign):
            if not node.targets:
                return None

            target = node.targets[0]
            annotation = None
            value_node = node.value

        else:
            target = node.target
            annotation = self._node_to_string(node.annotation)
            value_node = node.value

        name = self._node_to_string(target)

        if not name:
            return None

        return {
            "name": name,
            "annotation": annotation,
            "value": self._node_to_string(value_node),
            "line": getattr(node, "lineno", None),
        }

    def _extract_fastapi_routes(
        self,
        node: ast.FunctionDef | ast.AsyncFunctionDef,
        source_lines: list[str],
    ) -> list[dict[str, Any]]:
        routes: list[dict[str, Any]] = []

        function_data = self._extract_function(
            node=node,
            source_lines=source_lines,
            qualified_prefix=None,
        )

        for decorator in node.decorator_list:
            if not isinstance(decorator, ast.Call):
                continue

            if not isinstance(decorator.func, ast.Attribute):
                continue

            method_name = decorator.func.attr.lower()

            if method_name not in self.HTTP_METHODS:
                continue

            router_name = self._node_to_string(
                decorator.func.value,
            )

            route_path = None

            if decorator.args:
                route_path = self._get_literal_value(
                    decorator.args[0],
                )

            if not isinstance(route_path, str):
                route_path = None

            route_name = self._get_call_keyword_value(
                decorator,
                "name",
            )

            summary = self._get_call_keyword_value(
                decorator,
                "summary",
            )

            description = self._get_call_keyword_value(
                decorator,
                "description",
            )

            tags = self._get_call_keyword_value(
                decorator,
                "tags",
            )

            response_model = self._get_call_keyword_string(
                decorator,
                "response_model",
            )

            status_code = self._get_call_keyword_string(
                decorator,
                "status_code",
            )

            responses = self._get_call_keyword_string(
                decorator,
                "responses",
            )

            routes.append(
                {
                    "function_name": node.name,
                    "handler": node.name,
                    "handler_signature": function_data["signature"],
                    "arguments": function_data["arguments"],
                    "returns": function_data["returns"],
                    "method": method_name.upper(),
                    "path": route_path,
                    "line": getattr(node, "lineno", None),
                    "is_async": isinstance(
                        node,
                        ast.AsyncFunctionDef,
                    ),
                    "router_name": router_name,
                    "route_name": (
                        route_name
                        if isinstance(route_name, str)
                        else None
                    ),
                    "summary": (
                        summary
                        if isinstance(summary, str)
                        else None
                    ),
                    "description": (
                        description
                        if isinstance(description, str)
                        else None
                    ),
                    "tags": tags if isinstance(tags, list) else [],
                    "response_model": response_model,
                    "status_code": status_code,
                    "responses": responses,
                    "decorator": self._node_to_string(decorator),
                    "docstring": ast.get_docstring(node),
                    "source_preview": function_data["source_preview"],
                    "called_functions": function_data.get(
                        "called_functions",
                        [],
                    ),
                    "called_functions_preview": function_data.get(
                        "called_functions_preview",
                        [],
                    ),
                    "content_hash": function_data["content_hash"],
                }
            )

        return routes

    def _extract_arguments(
        self,
        arguments: ast.arguments,
    ) -> list[dict[str, Any]]:
        extracted_arguments: list[dict[str, Any]] = []

        positional_arguments = [
            *arguments.posonlyargs,
            *arguments.args,
        ]

        positional_defaults: list[ast.expr | None] = (
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
            strict=True,
        ):
            extracted_arguments.append(
                {
                    "name": argument.arg,
                    "kind": "positional",
                    "annotation": self._node_to_string(
                        argument.annotation,
                    ),
                    "default": (
                        self._node_to_string(default_value)
                        if default_value is not None
                        else None
                    ),
                    "required": default_value is None,
                }
            )

        if arguments.vararg is not None:
            extracted_arguments.append(
                {
                    "name": f"*{arguments.vararg.arg}",
                    "kind": "vararg",
                    "annotation": self._node_to_string(
                        arguments.vararg.annotation,
                    ),
                    "default": None,
                    "required": False,
                }
            )

        for keyword_argument, default_value in zip(
            arguments.kwonlyargs,
            arguments.kw_defaults,
            strict=True,
        ):
            extracted_arguments.append(
                {
                    "name": keyword_argument.arg,
                    "kind": "keyword_only",
                    "annotation": self._node_to_string(
                        keyword_argument.annotation,
                    ),
                    "default": (
                        self._node_to_string(default_value)
                        if default_value is not None
                        else None
                    ),
                    "required": default_value is None,
                }
            )

        if arguments.kwarg is not None:
            extracted_arguments.append(
                {
                    "name": f"**{arguments.kwarg.arg}",
                    "kind": "kwarg",
                    "annotation": self._node_to_string(
                        arguments.kwarg.annotation,
                    ),
                    "default": None,
                    "required": False,
                }
            )

        return extracted_arguments

    @staticmethod
    def _build_function_signature(
        name: str,
        arguments: list[dict[str, Any]],
        returns: str | None,
        is_async: bool,
    ) -> str:
        rendered_arguments: list[str] = []

        for argument in arguments:
            argument_name = str(argument.get("name", ""))
            annotation = argument.get("annotation")
            default = argument.get("default")

            rendered = argument_name

            if annotation:
                rendered = f"{rendered}: {annotation}"

            if default is not None:
                rendered = f"{rendered} = {default}"

            rendered_arguments.append(rendered)

        prefix = "async def" if is_async else "def"

        signature = (
            f"{prefix} {name}("
            + ", ".join(rendered_arguments)
            + ")"
        )

        if returns:
            signature = f"{signature} -> {returns}"

        return f"{signature}:"

    @staticmethod
    def _build_class_signature(
        class_name: str,
        bases: list[str],
    ) -> str:
        if bases:
            return f"class {class_name}({', '.join(bases)}):"

        return f"class {class_name}:"

    @staticmethod
    def _get_source_preview(
        source_lines: list[str],
        node: ast.AST,
        max_lines: int,
    ) -> str:
        start_line = getattr(node, "lineno", None)
        end_line = getattr(node, "end_lineno", None)

        if start_line is None or end_line is None:
            return ""

        start_index = max(start_line - 1, 0)
        end_index = min(end_line, len(source_lines))

        selected_lines = source_lines[start_index:end_index]

        if len(selected_lines) > max_lines:
            selected_lines = selected_lines[:max_lines]
            selected_lines.append("    ...")

        return "\n".join(selected_lines)

    @staticmethod
    def _calculate_node_hash(
        node: ast.AST,
    ) -> str:
        """
        Creates a stable SHA-256 hash from an AST node.

        Formatting-only changes generally do not change this hash.
        """

        normalized_node = ast.dump(
            node,
            annotate_fields=True,
            include_attributes=False,
        )

        return hashlib.sha256(
            normalized_node.encode("utf-8"),
        ).hexdigest()

    def _get_call_keyword_value(
        self,
        call_node: ast.Call,
        keyword_name: str,
    ) -> Any:
        for keyword in call_node.keywords:
            if keyword.arg != keyword_name:
                continue

            return self._get_literal_value(keyword.value)

        return None

    def _get_call_keyword_string(
        self,
        call_node: ast.Call,
        keyword_name: str,
    ) -> str | None:
        for keyword in call_node.keywords:
            if keyword.arg != keyword_name:
                continue

            literal_value = self._get_literal_value(
                keyword.value,
            )

            if isinstance(
                literal_value,
                (str, int, float, bool),
            ):
                return str(literal_value)

            return self._node_to_string(keyword.value)

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

        except (ValueError, TypeError):
            return None