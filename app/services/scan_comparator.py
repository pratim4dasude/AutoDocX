from typing import Any


class ScanComparator:
    """
    Compares two stored AutoDocX project scans.

    The comparator detects:
    - added files
    - deleted files
    - modified files
    - added, removed and modified functions
    - added, removed and modified classes
    - added, removed and modified methods
    - added and removed routes
    - added and removed internal dependencies
    """

    IGNORED_COMPARISON_FIELDS = {
        "line",
        "end_line",
    }

    def compare_scans(
        self,
        old_stored_scan: dict[str, Any],
        new_stored_scan: dict[str, Any],
    ) -> dict[str, Any]:
        old_scan_result = old_stored_scan.get(
            "scan_result",
            {},
        )

        new_scan_result = new_stored_scan.get(
            "scan_result",
            {},
        )

        self._validate_scan_result(
            scan_result=old_scan_result,
            scan_label="old",
        )

        self._validate_scan_result(
            scan_result=new_scan_result,
            scan_label="new",
        )

        old_project_name = old_scan_result.get(
            "project_name"
        )

        new_project_name = new_scan_result.get(
            "project_name"
        )

        if old_project_name != new_project_name:
            raise ValueError(
                "Cannot compare scans from different projects: "
                f"{old_project_name} and {new_project_name}"
            )

        file_changes = self._compare_files(
            old_scan_result=old_scan_result,
            new_scan_result=new_scan_result,
        )

        symbol_changes = self._compare_symbols(
            old_scan_result=old_scan_result,
            new_scan_result=new_scan_result,
        )

        route_changes = self._compare_routes(
            old_scan_result=old_scan_result,
            new_scan_result=new_scan_result,
        )

        dependency_changes = (
            self._compare_dependencies(
                old_scan_result=old_scan_result,
                new_scan_result=new_scan_result,
            )
        )

        summary = self._build_summary(
            file_changes=file_changes,
            symbol_changes=symbol_changes,
            route_changes=route_changes,
            dependency_changes=dependency_changes,
        )

        return {
            "project_name": old_project_name,
            "old_scan": {
                "scan_id": old_stored_scan.get(
                    "scan_id"
                ),
                "created_at": old_stored_scan.get(
                    "created_at"
                ),
            },
            "new_scan": {
                "scan_id": new_stored_scan.get(
                    "scan_id"
                ),
                "created_at": new_stored_scan.get(
                    "created_at"
                ),
            },
            "summary": summary,
            "file_changes": file_changes,
            "symbol_changes": symbol_changes,
            "route_changes": route_changes,
            "dependency_changes": dependency_changes,
        }

    def _compare_files(
        self,
        old_scan_result: dict[str, Any],
        new_scan_result: dict[str, Any],
    ) -> dict[str, Any]:
        old_file_hashes = old_scan_result.get(
            "file_hashes",
            {},
        )

        new_file_hashes = new_scan_result.get(
            "file_hashes",
            {},
        )

        if not isinstance(old_file_hashes, dict):
            old_file_hashes = {}

        if not isinstance(new_file_hashes, dict):
            new_file_hashes = {}

        if not old_file_hashes:
            raise ValueError(
                "The old scan does not contain file hashes. "
                "Create a fresh scan after adding hash support."
            )

        if not new_file_hashes:
            raise ValueError(
                "The new scan does not contain file hashes. "
                "Create a fresh scan after adding hash support."
            )

        old_files = set(old_file_hashes.keys())
        new_files = set(new_file_hashes.keys())

        added_files = sorted(
            new_files - old_files
        )

        deleted_files = sorted(
            old_files - new_files
        )

        common_files = (
            old_files.intersection(new_files)
        )

        modified_files = sorted(
            file_path
            for file_path in common_files
            if (
                old_file_hashes.get(file_path)
                != new_file_hashes.get(file_path)
            )
        )

        unchanged_files = sorted(
            file_path
            for file_path in common_files
            if (
                old_file_hashes.get(file_path)
                == new_file_hashes.get(file_path)
            )
        )

        return {
            "added": added_files,
            "deleted": deleted_files,
            "modified": modified_files,
            "unchanged": unchanged_files,
        }

    def _compare_symbols(
        self,
        old_scan_result: dict[str, Any],
        new_scan_result: dict[str, Any],
    ) -> dict[str, Any]:
        old_symbols = (
            old_scan_result
            .get("project_analysis", {})
            .get("symbols", {})
        )

        new_symbols = (
            new_scan_result
            .get("project_analysis", {})
            .get("symbols", {})
        )

        return {
            "functions": self._compare_symbol_group(
                old_items=old_symbols.get(
                    "functions",
                    [],
                ),
                new_items=new_symbols.get(
                    "functions",
                    [],
                ),
                key_fields=(
                    "file",
                    "name",
                ),
            ),
            "async_functions": (
                self._compare_symbol_group(
                    old_items=old_symbols.get(
                        "async_functions",
                        [],
                    ),
                    new_items=new_symbols.get(
                        "async_functions",
                        [],
                    ),
                    key_fields=(
                        "file",
                        "name",
                    ),
                )
            ),
            "classes": self._compare_symbol_group(
                old_items=old_symbols.get(
                    "classes",
                    [],
                ),
                new_items=new_symbols.get(
                    "classes",
                    [],
                ),
                key_fields=(
                    "file",
                    "name",
                ),
            ),
            "methods": self._compare_symbol_group(
                old_items=old_symbols.get(
                    "methods",
                    [],
                ),
                new_items=new_symbols.get(
                    "methods",
                    [],
                ),
                key_fields=(
                    "file",
                    "class_name",
                    "name",
                ),
            ),
        }

    def _compare_symbol_group(
        self,
        old_items: list[dict[str, Any]],
        new_items: list[dict[str, Any]],
        key_fields: tuple[str, ...],
    ) -> dict[str, Any]:
        old_lookup = self._build_lookup(
            items=old_items,
            key_fields=key_fields,
        )

        new_lookup = self._build_lookup(
            items=new_items,
            key_fields=key_fields,
        )

        old_keys = set(old_lookup.keys())
        new_keys = set(new_lookup.keys())

        added_keys = new_keys - old_keys
        removed_keys = old_keys - new_keys
        common_keys = old_keys.intersection(
            new_keys
        )

        added = [
            new_lookup[key]
            for key in sorted(
                added_keys,
                key=str,
            )
        ]

        removed = [
            old_lookup[key]
            for key in sorted(
                removed_keys,
                key=str,
            )
        ]

        modified: list[dict[str, Any]] = []
        unchanged: list[dict[str, Any]] = []

        for key in sorted(
            common_keys,
            key=str,
        ):
            old_item = old_lookup[key]
            new_item = new_lookup[key]

            normalized_old = (
                self._normalize_for_comparison(
                    old_item
                )
            )

            normalized_new = (
                self._normalize_for_comparison(
                    new_item
                )
            )

            if normalized_old != normalized_new:
                modified.append(
                    {
                        "identity": self._identity_dict(
                            item=new_item,
                            key_fields=key_fields,
                        ),
                        "before": old_item,
                        "after": new_item,
                    }
                )
            else:
                unchanged.append(
                    new_item
                )

        return {
            "added": added,
            "removed": removed,
            "modified": modified,
            "unchanged": unchanged,
        }

    def _compare_routes(
        self,
        old_scan_result: dict[str, Any],
        new_scan_result: dict[str, Any],
    ) -> dict[str, Any]:
        old_routes = (
            old_scan_result
            .get("project_analysis", {})
            .get("routes", [])
        )

        new_routes = (
            new_scan_result
            .get("project_analysis", {})
            .get("routes", [])
        )

        return self._compare_symbol_group(
            old_items=old_routes,
            new_items=new_routes,
            key_fields=(
                "method",
                "full_path",
            ),
        )

    def _compare_dependencies(
        self,
        old_scan_result: dict[str, Any],
        new_scan_result: dict[str, Any],
    ) -> dict[str, Any]:
        old_dependencies = (
            old_scan_result
            .get("project_analysis", {})
            .get(
                "internal_dependencies",
                [],
            )
        )

        new_dependencies = (
            new_scan_result
            .get("project_analysis", {})
            .get(
                "internal_dependencies",
                [],
            )
        )

        return self._compare_symbol_group(
            old_items=old_dependencies,
            new_items=new_dependencies,
            key_fields=(
                "source_module",
                "target_module",
                "imported_name",
                "alias",
            ),
        )

    def _build_summary(
        self,
        file_changes: dict[str, Any],
        symbol_changes: dict[str, Any],
        route_changes: dict[str, Any],
        dependency_changes: dict[str, Any],
    ) -> dict[str, int | bool]:
        added_symbols = 0
        removed_symbols = 0
        modified_symbols = 0

        for symbol_group in symbol_changes.values():
            added_symbols += len(
                symbol_group.get("added", [])
            )

            removed_symbols += len(
                symbol_group.get("removed", [])
            )

            modified_symbols += len(
                symbol_group.get("modified", [])
            )

        total_changes = (
            len(file_changes.get("added", []))
            + len(file_changes.get("deleted", []))
            + len(file_changes.get("modified", []))
            + added_symbols
            + removed_symbols
            + modified_symbols
            + len(route_changes.get("added", []))
            + len(route_changes.get("removed", []))
            + len(route_changes.get("modified", []))
            + len(
                dependency_changes.get(
                    "added",
                    [],
                )
            )
            + len(
                dependency_changes.get(
                    "removed",
                    [],
                )
            )
            + len(
                dependency_changes.get(
                    "modified",
                    [],
                )
            )
        )

        return {
            "has_changes": total_changes > 0,
            "total_changes": total_changes,
            "added_files": len(
                file_changes.get("added", [])
            ),
            "deleted_files": len(
                file_changes.get("deleted", [])
            ),
            "modified_files": len(
                file_changes.get("modified", [])
            ),
            "added_symbols": added_symbols,
            "removed_symbols": removed_symbols,
            "modified_symbols": modified_symbols,
            "added_routes": len(
                route_changes.get("added", [])
            ),
            "removed_routes": len(
                route_changes.get("removed", [])
            ),
            "modified_routes": len(
                route_changes.get("modified", [])
            ),
            "added_dependencies": len(
                dependency_changes.get(
                    "added",
                    [],
                )
            ),
            "removed_dependencies": len(
                dependency_changes.get(
                    "removed",
                    [],
                )
            ),
            "modified_dependencies": len(
                dependency_changes.get(
                    "modified",
                    [],
                )
            ),
        }

    @staticmethod
    def _build_lookup(
        items: list[dict[str, Any]],
        key_fields: tuple[str, ...],
    ) -> dict[tuple[Any, ...], dict[str, Any]]:
        lookup: dict[
            tuple[Any, ...],
            dict[str, Any],
        ] = {}

        for item in items:
            if not isinstance(item, dict):
                continue

            identity = tuple(
                item.get(field_name)
                for field_name in key_fields
            )

            lookup[identity] = item

        return lookup

    def _normalize_for_comparison(
        self,
        value: Any,
    ) -> Any:
        if isinstance(value, dict):
            return {
                key: self._normalize_for_comparison(
                    nested_value
                )
                for key, nested_value in sorted(
                    value.items()
                )
                if (
                    key
                    not in self.IGNORED_COMPARISON_FIELDS
                )
            }

        if isinstance(value, list):
            return [
                self._normalize_for_comparison(
                    item
                )
                for item in value
            ]

        return value

    @staticmethod
    def _identity_dict(
        item: dict[str, Any],
        key_fields: tuple[str, ...],
    ) -> dict[str, Any]:
        return {
            field_name: item.get(field_name)
            for field_name in key_fields
        }

    @staticmethod
    def _validate_scan_result(
        scan_result: Any,
        scan_label: str,
    ) -> None:
        if not isinstance(scan_result, dict):
            raise ValueError(
                f"The {scan_label} scan result is invalid."
            )

        if not scan_result.get("project_name"):
            raise ValueError(
                f"The {scan_label} scan does not "
                "contain a project name."
            )