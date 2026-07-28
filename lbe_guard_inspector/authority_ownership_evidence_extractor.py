"""Read-only, AST-only workspace evidence extraction for authority ownership.

The extractor is deliberately a producer of evidence, not an authority
decision-maker.  It accepts one explicit workspace scope and produces the
input shape consumed by :class:`AuthorityOwnershipInspector`.
"""

from __future__ import annotations

import ast
from copy import deepcopy
import hashlib
from pathlib import Path
from typing import Any, Mapping


EXTRACTOR_ID = "architecture.authority_ownership.evidence_extractor"
EXTRACTOR_VERSION = "1.0.0"
PASS_FAIL_AUTHORIZED = False


class AuthorityOwnershipEvidenceExtractor:
    """Extract conservative, current-workspace evidence without side effects."""

    def extract(self, specification: Mapping[str, Any]) -> dict[str, Any]:
        if not isinstance(specification, Mapping):
            raise ValueError("extractor specification must be a mapping")
        spec = deepcopy(dict(specification))
        self._require_specification_fields(spec)
        root = self._workspace_root(spec)
        operation = self._required_text(spec, "operation")
        canonical = self._required(spec, "canonical_state_or_side_effect")
        files = self._files(root, spec)
        excluded = set(self._string_list(spec.get("exclusions")))
        declarations = self._declarations(spec)
        selector_groups = {
            "mutation": self._selectors(spec, "mutation"),
            "execution": self._selectors(spec, "execution"),
            "persistence": self._selectors(spec, "persistence"),
        }
        allowed_callers = set(self._string_list(spec.get("allowed_caller_selectors")))
        relationships = self._relationships(spec)
        records: list[dict[str, Any]] = []
        symbols: list[dict[str, Any]] = []
        raw_calls: list[dict[str, Any]] = []
        unresolved: list[dict[str, Any]] = []
        for path in files:
            relative = path.relative_to(root).as_posix()
            data = path.read_bytes()
            digest = hashlib.sha256(data).hexdigest()
            item = {"path": relative, "sha256": digest, "byte_length": len(data), "utf8_parse_status": "valid"}
            try:
                text = data.decode("utf-8")
            except UnicodeDecodeError as error:
                item["utf8_parse_status"] = "invalid"
                item["parse_error"] = f"UTF-8 decode error at byte {error.start}"
                records.append(item)
                continue
            try:
                tree = ast.parse(text, filename=relative)
            except SyntaxError as error:
                item["syntax_parse_status"] = "invalid"
                item["parse_error"] = f"syntax error at line {error.lineno}, column {error.offset}: {error.msg}"
                records.append(item)
                continue
            item["syntax_parse_status"] = "valid"
            records.append(item)
            visitor = _SourceVisitor(relative)
            visitor.visit(tree)
            symbols.extend(visitor.symbols)
            raw_calls.extend(visitor.calls)
            unresolved.extend(visitor.unresolved)
        records = self._sorted(records, "path")
        symbols = self._sorted(symbols, "symbol")
        hashes = {item["path"]: item["sha256"] for item in records}
        symbol_names = {path: [] for path in hashes}
        for symbol in symbols:
            symbol_names.setdefault(symbol["source_path"], []).append(symbol["symbol"])
        symbol_names = {key: sorted(set(value)) for key, value in sorted(symbol_names.items())}
        calls = self._sorted(raw_calls, "callsite_ref")
        mutation = self._site_records(calls, selector_groups["mutation"], "mutation", operation, canonical, hashes, excluded)
        execution = self._site_records(calls, selector_groups["execution"], "execution", operation, canonical, hashes, excluded)
        persistence = self._persistence_records(calls, selector_groups["persistence"], hashes, excluded)
        lifecycle = [call for call in calls if call["call_name"].split(".")[-1] in {"register", "subscribe", "add_listener", "add_handler"}]
        call_edges = self._call_edges(calls, symbols)
        caller_paths = self._caller_paths(call_edges, mutation, allowed_callers)
        owners = self._owner_records(declarations, symbols, hashes, excluded)
        relationship_candidates = self._relationship_candidates(relationships, symbols, hashes, excluded)
        missing = self._missing(spec, records, mutation, persistence, owners)
        validation = {
            "checks_run": ["workspace_root_resolution", "explicit_scope_validation", "sha256", "utf8", "python_ast"],
            "checks_passed": ["read_only"], "checks_failed": [],
            "unavailable_checks": ["runtime_confirmation"] if spec.get("runtime_confirmation_required") else [],
            "evidence_refs": [f"workspace:{item['path']}" for item in records],
        }
        inspector_input = self._inspector_input(root, operation, canonical, owners, mutation, caller_paths, persistence,
                                                relationship_candidates, hashes, symbol_names, spec, missing, validation)
        return {
            "extractor_id": EXTRACTOR_ID, "extractor_version": EXTRACTOR_VERSION,
            "workspace_root": str(root), "operation": operation, "canonical_state_or_side_effect": deepcopy(canonical),
            "inspected_files": records, "source_hashes": hashes, "symbols": symbols, "call_edges": call_edges,
            "direct_call_expressions": calls,
            "mutation_sites": mutation, "execution_sites": execution, "caller_paths": caller_paths,
            "persistence_paths": persistence, "relationship_candidates": relationship_candidates,
            "owner_declarations": owners, "unresolved_dynamic_evidence": self._sorted(unresolved, "evidence_ref"),
            "excluded_evidence": sorted(excluded), "missing_evidence": sorted(set(missing)), "validation": validation,
            "inspector_input": inspector_input,
            **_main_contract_payload(inspector_input), "read_only": True, "pass_fail_authorized": PASS_FAIL_AUTHORIZED,
            "lifecycle_registration_candidates": lifecycle,
        }

    def _workspace_root(self, spec: dict[str, Any]) -> Path:
        value = self._required_text(spec, "workspace_root")
        if spec.get("reference_only") is True:
            raise ValueError("reference-only input is not workspace evidence")
        root = Path(value).expanduser().resolve(strict=True)
        if not root.is_dir():
            raise ValueError("workspace_root must be a directory")
        bundled_examples = Path(__file__).resolve().parents[1] / "examples"
        if root == bundled_examples or bundled_examples in root.parents:
            raise ValueError("bundled reference roots are not workspace evidence")
        return root

    @staticmethod
    def _require_specification_fields(spec: dict[str, Any]) -> None:
        required = (
            "operation", "canonical_state_or_side_effect", "workspace_root", "owner_declarations",
            "mutation_call_names", "execution_call_names", "persistence_call_names",
            "allowed_caller_selectors", "relationship_declarations", "runtime_confirmation_required", "exclusions",
        )
        absent = [key for key in required if key not in spec]
        if absent:
            raise ValueError("extractor specification is missing: " + ", ".join(absent))

    def _files(self, root: Path, spec: dict[str, Any]) -> list[Path]:
        candidates = self._string_list(spec.get("candidate_files"))
        patterns = self._string_list(spec.get("include_patterns") or spec.get("bounded_include_patterns"))
        if not candidates and not patterns:
            raise ValueError("candidate_files or bounded include patterns are required")
        result: set[Path] = set()
        for candidate in candidates:
            path = (root / candidate).resolve(strict=False) if not Path(candidate).is_absolute() else Path(candidate).resolve(strict=False)
            self._inside(root, path)
            if not path.is_file():
                raise ValueError(f"candidate file is missing or unreadable: {candidate}")
            try:
                path.read_bytes()
            except OSError as error:
                raise ValueError(f"candidate file is missing or unreadable: {candidate}") from error
            result.add(path)
        for pattern in patterns:
            if Path(pattern).is_absolute() or ".." in Path(pattern).parts or pattern.strip() in {"*", "**", "**/*"}:
                raise ValueError("include patterns must be explicit and bounded within workspace_root")
            matches = [item.resolve() for item in root.glob(pattern) if item.is_file()]
            if not matches:
                raise ValueError(f"include pattern matched no files: {pattern}")
            for item in matches:
                self._inside(root, item)
                result.add(item)
        return sorted(result, key=lambda item: item.relative_to(root).as_posix())

    @staticmethod
    def _inside(root: Path, path: Path) -> None:
        try:
            path.relative_to(root)
        except ValueError as error:
            raise ValueError("candidate file escapes workspace_root") from error

    @staticmethod
    def _required(spec: dict[str, Any], key: str) -> Any:
        if key not in spec or spec[key] in (None, ""):
            raise ValueError(f"{key} is required")
        return spec[key]

    def _required_text(self, spec: dict[str, Any], key: str) -> str:
        value = self._required(spec, key)
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{key} must be non-empty text")
        return value.strip()

    @staticmethod
    def _string_list(value: Any) -> list[str]:
        if value is None: return []
        if not isinstance(value, list) or not all(isinstance(item, str) and item for item in value):
            raise ValueError("file lists and selectors must be lists of non-empty strings")
        return value

    def _selectors(self, spec: dict[str, Any], kind: str) -> set[str]:
        return set(self._string_list(spec.get(f"{kind}_call_names") or spec.get(f"{kind}_symbol_selectors")))

    def _declarations(self, spec: dict[str, Any]) -> list[dict[str, Any]]:
        value = spec.get("owner_declarations", [])
        if not isinstance(value, list) or not all(isinstance(item, Mapping) for item in value): raise ValueError("owner_declarations must be a list of mappings")
        return [dict(item) for item in value]

    def _relationships(self, spec: dict[str, Any]) -> list[dict[str, Any]]:
        value = spec.get("relationship_declarations", [])
        if not isinstance(value, list) or not all(isinstance(item, Mapping) for item in value): raise ValueError("relationship_declarations must be a list of mappings")
        return [dict(item) for item in value]

    def _site_records(self, calls, selectors, kind, operation, canonical, hashes, excluded):
        output = []
        for call in calls:
            if call["callsite_ref"] in excluded or not self._matches(call["call_name"], selectors): continue
            output.append({"component_id": call["source_path"], "source_path": call["source_path"], "symbol": call["caller"],
                           "operation": operation if kind == "mutation" else kind, "target_identifier": self._target_id(canonical),
                           "callsite_ref": call["callsite_ref"], "source_hash": hashes[call["source_path"]], "verified": True,
                           "classification": f"static_{kind}_candidate", "evidence_source": "current_workspace"})
        return self._sorted(output, "callsite_ref")

    def _persistence_records(self, calls, selectors, hashes, excluded):
        output = []
        for call in calls:
            static = call.get("static_effect")
            if call["callsite_ref"] in excluded or not (static in {"file_write", "sqlite_write"} or self._matches(call["call_name"], selectors)): continue
            output.append({"component_id": call["source_path"], "storage_kind": "sqlite" if static == "sqlite_write" else "file",
                           "storage_location": call.get("storage_location", "unresolved"), "write_symbol": call["caller"],
                           "read_symbol": None, "canonical": True, "evidence_refs": [call["callsite_ref"]],
                           "source_hash": hashes[call["source_path"]], "verified": bool(static or selectors)})
        return self._sorted(output, "storage_location")

    @staticmethod
    def _matches(name: str, selectors: set[str]) -> bool:
        return name in selectors or name.split(".")[-1] in selectors

    @staticmethod
    def _target_id(canonical: Any) -> str:
        return str(canonical.get("identifier", canonical.get("target", "unspecified"))) if isinstance(canonical, Mapping) else str(canonical)

    def _call_edges(self, calls, symbols):
        known = {item["symbol"] for item in symbols if item["kind"] in {"function", "async_function"}}
        output = []
        for call in calls:
            candidates = [symbol for symbol in known if symbol == call["call_name"] or symbol.endswith("." + call["call_name"].split(".")[-1])]
            for callee in sorted(candidates): output.append({"caller": call["caller"], "callee": callee, "source_path": call["source_path"], "callsite_ref": call["callsite_ref"]})
        return self._sorted(output, "callsite_ref")

    def _caller_paths(self, edges, mutations, allowed):
        terminals = {item["callsite_ref"]: item for item in mutations}
        output = []
        for edge in edges:
            for ref, site in terminals.items():
                if edge["callee"] == site["symbol"] and (not allowed or edge["caller"] in allowed):
                    output.append({"entrypoint": edge["caller"], "caller_chain": [edge["caller"], edge["callee"]], "terminal_mutation_site": ref,
                                   "authority_source": None, "evidence_refs": [edge["callsite_ref"], ref]})
        return self._sorted(output, "entrypoint")

    def _owner_records(self, declarations, symbols, hashes, excluded):
        available = {(item["source_path"], item["symbol"]) for item in symbols}
        output = []
        for declaration in declarations:
            path, symbol = declaration.get("source_path"), declaration.get("symbol")
            if not isinstance(path, str) or not isinstance(symbol, str) or f"workspace:{path}:{symbol}" in excluded: continue
            if (path, symbol) not in available: continue
            output.append({"component_id": str(declaration.get("component_id", path)), "source_path": path, "symbol": symbol,
                           "declared_role": str(declaration.get("declared_role", "authoritative_owner")), "declaration_source": "explicit_extractor_specification",
                           "evidence_ref": f"workspace:{path}:{symbol}", "source_hash": hashes[path], "verified": True})
        return self._sorted(output, "component_id")

    def _relationship_candidates(self, relationships, symbols, hashes, excluded):
        paths = {item["source_path"] for item in symbols}
        output = []
        for item in relationships:
            path = item.get("source_path")
            if not isinstance(path, str) or path not in paths or f"workspace:{path}" in excluded: continue
            record = dict(item); record.update({"source_hash": hashes[path], "evidence_source": "current_workspace", "verified": False})
            output.append(record)
        return self._sorted(output, "component_id")

    def _missing(self, spec, records, mutation, persistence, owners):
        missing = []
        if any(item.get("utf8_parse_status") != "valid" or item.get("syntax_parse_status") != "valid" for item in records): missing.append("parseable_source_coverage")
        if not owners: missing.append("owner_declarations")
        if not mutation: missing.append("mutation_site_coverage")
        if not persistence: missing.append("persistence_evidence")
        if spec.get("runtime_confirmation_required"): missing.append("runtime_confirmation")
        return missing

    def _inspector_input(self, root, operation, canonical, owners, mutation, paths, persistence, relationships, hashes, symbols, spec, missing, validation):
        target = dict(canonical) if isinstance(canonical, Mapping) else {"kind": "state", "identifier": str(canonical)}
        target.setdefault("kind", "state"); target.setdefault("identifier", self._target_id(canonical))
        return {"workspace_id": str(root), "authoritative_operation": operation, "canonical_target": target,
                "owner_declarations": deepcopy(owners), "mutation_sites": deepcopy(mutation), "call_paths": deepcopy(paths),
                "persistence_paths": deepcopy(persistence), "relationships": deepcopy(relationships), "runtime_observations": [],
                "validation": deepcopy(validation), "current_source_hashes": deepcopy(hashes), "current_symbols": deepcopy(symbols),
                "requires_runtime_confirmation": bool(spec.get("runtime_confirmation_required")), "reference_only": False,
                "missing_evidence": sorted(set(missing))}

    @staticmethod
    def _sorted(items, key):
        return sorted((deepcopy(item) for item in items), key=lambda item: (str(item.get(key, "")), str(item)))


class _SourceVisitor(ast.NodeVisitor):
    def __init__(self, source_path: str):
        self.source_path, self.scope, self.symbols, self.calls, self.unresolved = source_path, [], [], [], []

    def _name(self) -> str: return ".".join(self.scope) or "<module>"
    def _symbol(self, name: str) -> str: return ".".join([*self.scope, name])
    def visit_FunctionDef(self, node): self._function(node, "function")
    def visit_AsyncFunctionDef(self, node): self._function(node, "async_function")
    def _function(self, node, kind):
        symbol = self._symbol(node.name); self.symbols.append({"source_path": self.source_path, "symbol": symbol, "kind": kind, "line": node.lineno})
        self.scope.append(node.name); self.generic_visit(node); self.scope.pop()
    def visit_ClassDef(self, node):
        symbol = self._symbol(node.name); self.symbols.append({"source_path": self.source_path, "symbol": symbol, "kind": "class", "line": node.lineno})
        self.scope.append(node.name); self.generic_visit(node); self.scope.pop()
    def visit_Assign(self, node):
        for target in node.targets: self._assignment(target, node.lineno)
        self.generic_visit(node)
    def visit_AnnAssign(self, node): self._assignment(node.target, node.lineno); self.generic_visit(node)
    def _assignment(self, target, line):
        if isinstance(target, ast.Name): self.symbols.append({"source_path": self.source_path, "symbol": self._name(), "kind": "assignment_target", "target": target.id, "line": line})
        elif isinstance(target, ast.Attribute): self.symbols.append({"source_path": self.source_path, "symbol": self._name(), "kind": "attribute_assignment_target", "target": self._expr(target), "line": line})
    def visit_Call(self, node):
        name = self._expr(node.func)
        ref = f"workspace:{self.source_path}:{node.lineno}:{node.col_offset}"
        if name is None:
            self.unresolved.append({"evidence_ref": ref, "source_path": self.source_path, "caller": self._name(), "line": node.lineno, "reason": "dynamic_call_target"})
        else:
            call = {"call_name": name, "caller": self._name(), "source_path": self.source_path, "callsite_ref": ref, "line": node.lineno}
            self._effect(call, node); self.calls.append(call)
        self.generic_visit(node)
    def _effect(self, call, node):
        leaf = call["call_name"].split(".")[-1]
        mode = self._literal(node.args[1]) if call["call_name"] == "open" and len(node.args) > 1 else self._keyword(node, "mode")
        if (call["call_name"] == "open" and isinstance(mode, str) and any(flag in mode for flag in "wax")) or leaf in {"write_text", "write_bytes"}:
            call["static_effect"] = "file_write"; call["storage_location"] = str(self._literal(node.args[0])) if node.args else "unresolved"
        if leaf in {"execute", "executemany"} and isinstance(self._literal(node.args[0]) if node.args else None, str) and self._literal(node.args[0]).lstrip().upper().startswith(("INSERT", "UPDATE", "DELETE", "REPLACE", "CREATE", "DROP", "ALTER")):
            call["static_effect"] = "sqlite_write"; call["storage_location"] = "sqlite:unresolved"
        if call["call_name"].startswith("subprocess.") or call["call_name"] in {"os.system", "os.popen"}: call["static_effect"] = "command_execution"
    @staticmethod
    def _literal(node): return node.value if isinstance(node, ast.Constant) else None
    def _keyword(self, node, name): return next((self._literal(item.value) for item in node.keywords if item.arg == name), None)
    def _expr(self, node):
        if isinstance(node, ast.Name): return node.id
        if isinstance(node, ast.Attribute):
            base = self._expr(node.value); return f"{base}.{node.attr}" if base else None
        return None

def _main_contract_payload(inspector_input: Mapping[str, Any]) -> dict[str, Any]:
    workspace_id = str(
        inspector_input.get("workspace_id") or "unknown-workspace"
    ).strip()
    operation_id = str(
        inspector_input.get("operation")
        or inspector_input.get("authoritative_operation")
        or "unknown-operation"
    ).strip()
    canonical_state = str(
        inspector_input.get("canonical_state_or_side_effect")
        or inspector_input.get("canonical_target")
        or "unknown-canonical-target"
    ).strip()
    canonical_target = (
        canonical_state
        if "://" in canonical_state
        else (
            f"workspace://{_contract_token(workspace_id)}/authority/"
            f"{_contract_token(canonical_state)}"
        )
    )

    request = {
        "request_id": (
            f"authority-extraction-{_contract_token(workspace_id)}-"
            f"{_contract_token(operation_id)}"
        ),
        "workspace_id": workspace_id,
        "operation_id": operation_id,
        "canonical_target": canonical_target,
        "ownership_sensitive": True,
    }

    owners = list(inspector_input.get("owner_declarations") or [])
    owner_name = _owner_name(owners[0]) if owners else "unresolved-owner"

    package = {
        "request": {
            "operation_id": operation_id,
            "canonical_target": canonical_target,
        },
        "registry": _evidence_items(
            inspector_input.get("registry")
            or inspector_input.get("inspected_files")
            or [],
            prefix="registry",
            default_kind="current_source",
        ),
        "lifecycle": _evidence_items(
            inspector_input.get("lifecycle")
            or inspector_input.get("lifecycle_registration_candidates")
            or [],
            prefix="lifecycle",
            default_kind="current_source",
        ),
        "canonical_state": _evidence_items(
            inspector_input.get("canonical_state")
            or inspector_input.get("inspected_files")
            or [{"detail": canonical_state}],
            prefix="state",
            default_kind="current_source",
        ),
        "owner_declarations": [
            {
                "ref": f"owner:{_contract_token(_owner_name(record))}:{index}",
                "kind": "current_declaration",
                "detail": f"owner={_owner_name(record)}",
            }
            for index, record in enumerate(owners)
        ],
        "mutation_sites": [
            {
                "ref": f"mutation:{_contract_token(owner_name)}:{index}",
                "kind": "current_source",
                "detail": (
                    f"mutator={owner_name} "
                    f"capability={_record_detail(record, operation_id)}"
                ),
            }
            for index, record in enumerate(
                list(inspector_input.get("mutation_sites") or [])
            )
        ],
        "call_paths": _evidence_items(
            inspector_input.get("call_paths")
            or inspector_input.get("caller_paths")
            or [],
            prefix="call",
            default_kind="current_source",
        ),
        "persistence": _evidence_items(
            inspector_input.get("persistence")
            or inspector_input.get("persistence_paths")
            or [],
            prefix="persistence",
            default_kind="current_source",
        ),
        "runtime_confirmation": _evidence_items(
            inspector_input.get("runtime_confirmation")
            or inspector_input.get("runtime_observations")
            or [],
            prefix="runtime",
            default_kind="runtime_receipt",
        ),
        "contradictions": _contradiction_items(inspector_input),
    }

    return {
        "inspector_request": request,
        "evidence_package": package,
    }


def _evidence_items(
    records: Any,
    *,
    prefix: str,
    default_kind: str,
) -> list[dict[str, str]]:
    items: list[dict[str, str]] = []
    for index, record in enumerate(list(records or [])):
        items.append(
            {
                "ref": _record_ref(record, f"{prefix}:{index}"),
                "kind": _record_kind(record, default_kind),
                "detail": _record_detail(record, prefix),
            }
        )
    return items


def _contradiction_items(
    inspector_input: Mapping[str, Any],
) -> list[str]:
    values: list[Any] = []
    values.extend(list(inspector_input.get("contradictions") or []))
    values.extend(list(inspector_input.get("missing_evidence") or []))
    values.extend(
        list(inspector_input.get("unresolved_dynamic_evidence") or [])
    )
    contradictions: list[str] = []
    for value in values:
        detail = _record_detail(value, "unresolved evidence").strip()
        if detail and detail not in contradictions:
            contradictions.append(detail)
    return contradictions

def _owner_name(record: Any) -> str:
    if isinstance(record, Mapping):
        for key in ("participant", "owner", "symbol", "module", "name"):
            value = record.get(key)
            if value is not None and str(value).strip():
                return str(value).strip()
    value = str(record).strip()
    return value or "unresolved-owner"


def _record_ref(record: Any, fallback: str) -> str:
    if isinstance(record, Mapping):
        for key in ("ref", "evidence_ref", "source_ref"):
            value = record.get(key)
            if value is not None and str(value).strip():
                return str(value).strip()
    return fallback


def _record_kind(record: Any, fallback: str) -> str:
    if isinstance(record, Mapping):
        value = record.get("kind")
        if value is not None and str(value).strip():
            return str(value).strip()
    return fallback


def _record_detail(record: Any, fallback: str) -> str:
    if isinstance(record, Mapping):
        for key in (
            "detail",
            "expression",
            "qualified_name",
            "symbol",
            "path",
            "relative_path",
            "module",
            "reason",
            "evidence_ref",
        ):
            value = record.get(key)
            if value is not None and str(value).strip():
                return str(value).strip()
        pairs = [
            f"{key}={value}"
            for key, value in sorted(record.items(), key=lambda item: str(item[0]))
            if value not in (None, "", [], {})
        ]
        if pairs:
            return " ".join(pairs)
    value = str(record).strip()
    return value or fallback


def _contract_token(value: Any) -> str:
    text = str(value).strip().lower()
    token = "".join(
        character if character.isalnum() else "-"
        for character in text
    )
    token = "-".join(part for part in token.split("-") if part)
    return token[:96] or "unknown"
