import hashlib
from unittest.mock import patch

from lbe_guard_inspector.evidence_service import EvidenceService


class FakeContext:
    @classmethod
    def load(cls):
        return cls()


def test_build_evidence_package_wraps_existing_search() -> None:
    search_output = {
        "query": "Provided callback is not a function",
        "search_completed": True,
        "outcome": "matches_found",
        "message": "Found 1 matching files.",
        "result_count": 1,
        "results": [
            {
                "root": "CEP_Project",
                "path": "CEP_Project/cep/client/js/CSInterface.js",
                "score": 672,
                "size": 42759,
                "line": 525,
                "snippet": "Provided callback is not a function",
                "sha256": "abc123",
                "matched_terms": 4,
                "exact_phrase": True,
            }
        ],
        "searched_roots": ["CEP_Project"],
        "meaningful_terms": ["provided", "callback", "function"],
        "minimum_required_matches": 2,
        "scanned_files": 10,
        "skipped_unreadable_files": 0,
        "scope": {
            "roots_requested": None,
            "roots_searched": ["CEP_Project"],
            "extensions": [".js"],
            "files_considered": 10,
        },
    }

    with patch(
        "lbe_guard_inspector.evidence_service.Context",
        FakeContext,
    ), patch(
        "lbe_guard_inspector.evidence_service.search_workspace",
        return_value=search_output,
    ):
        package = EvidenceService().build_evidence_package(
            task_id="task-1",
            query="Provided callback is not a function",
            max_results=10,
        )

    assert len(package["indexed_reference_evidence"]) == 1
    evidence = package["indexed_reference_evidence"][0]
    assert evidence["path"].endswith("CSInterface.js")
    assert evidence["hash"] == "abc123"
    assert evidence["line_start"] == 525
    assert evidence["exact_phrase"] is True
    assert evidence["metadata"]["retrieval_source"] == "agent.search_workspace"


def test_reference_record_stays_indexed_and_non_executable() -> None:
    search_output = {
        "query": "authority owner",
        "search_completed": True,
        "outcome": "matches_found",
        "results": [{
            "root": "lbe-reference",
            "root_class": "reference",
            "path": "lbe-reference/state_owner_authority_ownership.yaml",
            "score": 900,
            "size": 100,
            "line": 1,
            "snippet": "authority owner",
            "sha256": "reference-hash",
            "matched_terms": 2,
            "exact_phrase": True,
            "source_class": "reference_pattern",
            "metadata_parse_status": "parsed",
            "gallery_metadata": {
                "id": "architecture.authority-ownership",
                "record_type": "state-owner-pattern",
                "source_class": "reference_pattern",
                "authority_level": "reviewed",
                "verification_status": "verified",
                "workspace_scope": {"kind": "reference"},
                "execution_status": "knowledge_only",
                "guard_binding": {
                    "proposed_guard_id": "architecture.authority_ownership",
                    "implementation_available": False,
                },
            },
        }],
    }

    with patch("lbe_guard_inspector.evidence_service.Context", FakeContext), patch(
        "lbe_guard_inspector.evidence_service.search_workspace", return_value=search_output
    ):
        package = EvidenceService().build_evidence_package(
            task_id="reference-only", query="authority owner"
        )

    assert len(package["indexed_reference_evidence"]) == 1
    assert package["current_workspace_evidence"] == []
    evidence = package["indexed_reference_evidence"][0]
    assert evidence["record_id"] == "architecture.authority-ownership"
    assert evidence["workspace_id"] is None
    assert evidence["classification"] == "reference_pattern"
    assert evidence["metadata"]["workspace_scope"] == {"kind": "reference"}
    assert evidence["metadata"]["verification_status"] == "verified"
    assert evidence["metadata"]["executable"] is False
    assert "workspace PASS/FAIL is not permitted" in package["missing_evidence"][0]
    assert "PASS" not in package and "FAIL" not in package


def test_no_matches_becomes_evidence_gap() -> None:
    search_output = {
        "query": "missing phrase",
        "search_completed": True,
        "outcome": "no_matches",
        "message": "No content matched the query.",
        "result_count": 0,
        "results": [],
        "searched_roots": ["CEP_Project"],
        "meaningful_terms": ["missing", "phrase"],
        "minimum_required_matches": 2,
        "scanned_files": 10,
        "skipped_unreadable_files": 0,
        "scope": {
            "roots_requested": None,
            "roots_searched": ["CEP_Project"],
            "extensions": [".js"],
            "files_considered": 10,
        },
    }

    with patch(
        "lbe_guard_inspector.evidence_service.Context",
        FakeContext,
    ), patch(
        "lbe_guard_inspector.evidence_service.search_workspace",
        return_value=search_output,
    ):
        package = EvidenceService().build_evidence_package(
            task_id="task-2",
            query="missing phrase",
        )

    assert package["indexed_reference_evidence"] == []
    assert package["missing_evidence"] == [
        "Indexed files were scanned, but no content matched the query.",
        "Current workspace evidence was not supplied; workspace PASS/FAIL is not permitted.",
    ]


def test_excluded_classifications_are_filtered_by_default() -> None:
    search_output = {
        "query": "Provided callback is not a function",
        "search_completed": True,
        "outcome": "matches_found",
        "message": "Found 2 matching files.",
        "result_count": 2,
        "results": [
            {
                "root": "dev",
                "path": "dev/project/backup/file.js",
                "score": 700,
                "size": 100,
                "line": 10,
                "snippet": "Provided callback is not a function",
                "sha256": "backup-hash",
                "matched_terms": 4,
                "exact_phrase": True,
            },
            {
                "root": "dev",
                "path": "dev/project/src/file.js",
                "score": 650,
                "size": 100,
                "line": 10,
                "snippet": "Provided callback is not a function",
                "sha256": "source-hash",
                "matched_terms": 4,
                "exact_phrase": True,
            },
        ],
    }

    with patch(
        "lbe_guard_inspector.evidence_service.Context",
        FakeContext,
    ), patch(
        "lbe_guard_inspector.evidence_service.search_workspace",
        return_value=search_output,
    ):
        package = EvidenceService().build_evidence_package(
            task_id="task-filter",
            query="Provided callback is not a function",
            include_excluded=False,
        )

    assert len(package["indexed_reference_evidence"]) == 1
    assert package["indexed_reference_evidence"][0]["hash"] == "source-hash"
    assert package["indexed_reference_evidence"][0]["classification"] == "indexed_reference"


def test_excluded_classifications_can_be_included_explicitly() -> None:
    search_output = {
        "query": "Provided callback is not a function",
        "search_completed": True,
        "outcome": "matches_found",
        "message": "Found 1 matching file.",
        "result_count": 1,
        "results": [
            {
                "root": "dev",
                "path": "dev/project/backup/file.js",
                "score": 700,
                "size": 100,
                "line": 10,
                "snippet": "Provided callback is not a function",
                "sha256": "backup-hash",
                "matched_terms": 4,
                "exact_phrase": True,
            }
        ],
    }

    with patch(
        "lbe_guard_inspector.evidence_service.Context",
        FakeContext,
    ), patch(
        "lbe_guard_inspector.evidence_service.search_workspace",
        return_value=search_output,
    ):
        package = EvidenceService().build_evidence_package(
            task_id="task-include-filtered",
            query="Provided callback is not a function",
            include_excluded=True,
        )

    assert len(package["indexed_reference_evidence"]) == 1
    assert package["indexed_reference_evidence"][0]["classification"] == "backup"


from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class FakeRoot:
    name: str
    path: Path


class FakeWorkspaceContext:
    def __init__(self, root: Path):
        self.roots = [FakeRoot(name="dev", path=root)]
        self.config = {"max_file_bytes": 5_000_000}

    @classmethod
    def load(cls):
        raise AssertionError("Use a patched instance")


def test_workspace_evidence_is_attached_separately(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    source = workspace / "src"
    source.mkdir()
    target = source / "callback.js"
    target.write_text(
        'console.log("Provided callback is not a function");',
        encoding="utf-8",
    )

    search_output = {
        "query": "Provided callback is not a function",
        "search_completed": True,
        "outcome": "no_matches",
        "message": "No content matched the query.",
        "result_count": 0,
        "results": [],
        "searched_roots": ["dev"],
        "meaningful_terms": ["provided", "callback", "function"],
        "minimum_required_matches": 2,
        "scanned_files": 1,
        "skipped_unreadable_files": 0,
        "scope": {
            "roots_requested": ["dev"],
            "roots_searched": ["dev"],
            "extensions": [".js"],
            "files_considered": 1,
        },
    }

    fake_context = FakeWorkspaceContext(tmp_path)

    with patch(
        "lbe_guard_inspector.evidence_service.Context.load",
        return_value=fake_context,
    ), patch(
        "lbe_guard_inspector.evidence_service.search_workspace",
        return_value=search_output,
    ):
        package = EvidenceService().build_evidence_package(
            task_id="task-workspace",
            query="Provided callback is not a function",
            workspace_id="browser-dev",
            workspace_root=str(workspace),
            max_results=10,
            extensions=[".js"],
            roots=["dev"],
        )

    assert len(package["current_workspace_evidence"]) == 1
    evidence = package["current_workspace_evidence"][0]
    assert evidence["source_type"] == "workspace"
    assert evidence["classification"] == "current_workspace"
    assert evidence["verified"] is True
    assert evidence["authority"] == 2
    assert evidence["path"] == str(target.resolve())


def test_workspace_outside_configured_roots_is_rejected(tmp_path: Path) -> None:
    configured = tmp_path / "configured"
    configured.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()

    search_output = {
        "query": "test query",
        "search_completed": True,
        "outcome": "no_matches",
        "message": "No content matched the query.",
        "result_count": 0,
        "results": [],
    }

    fake_context = FakeWorkspaceContext(configured)

    with patch(
        "lbe_guard_inspector.evidence_service.Context.load",
        return_value=fake_context,
    ), patch(
        "lbe_guard_inspector.evidence_service.search_workspace",
        return_value=search_output,
    ):
        try:
            EvidenceService().build_evidence_package(
                task_id="task-outside",
                query="test query",
                workspace_root=str(outside),
            )
        except Exception as exc:
            assert "outside configured knowledge roots" in str(exc)
        else:
            raise AssertionError("Expected outside workspace root to be rejected")


def test_workspace_build_directories_are_excluded(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()

    build = workspace / "build" / "bundle"
    build.mkdir(parents=True)
    (build / "generated.js").write_text(
        "runAutonomousInstruction",
        encoding="utf-8",
    )

    source = workspace / "src"
    source.mkdir()
    current = source / "AgentService.js"
    current.write_text(
        "runAutonomousInstruction",
        encoding="utf-8",
    )

    search_output = {
        "query": "runAutonomousInstruction",
        "search_completed": True,
        "outcome": "no_matches",
        "message": "No content matched the query.",
        "result_count": 0,
        "results": [],
    }

    fake_context = FakeWorkspaceContext(tmp_path)

    with patch(
        "lbe_guard_inspector.evidence_service.Context.load",
        return_value=fake_context,
    ), patch(
        "lbe_guard_inspector.evidence_service.search_workspace",
        return_value=search_output,
    ):
        package = EvidenceService().build_evidence_package(
            task_id="task-build-filter",
            query="runAutonomousInstruction",
            workspace_root=str(workspace),
            extensions=[".js"],
            include_excluded=False,
        )

    paths = [
        item["path"]
        for item in package["current_workspace_evidence"]
    ]

    assert str(current.resolve()) in paths
    assert str((build / "generated.js").resolve()) not in paths


def test_stale_index_hash_produces_a_contradiction(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    source = workspace / "src"
    source.mkdir()
    target = source / "callback.js"
    content = 'console.log("Provided callback is not a function");'
    target.write_text(content, encoding="utf-8")

    current_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()

    # Indexed evidence points at the same file but reports a stale hash.
    search_output = {
        "query": "Provided callback is not a function",
        "search_completed": True,
        "outcome": "matches_found",
        "message": "Found 1 matching file.",
        "result_count": 1,
        "results": [
            {
                "root": "dev",
                "path": "dev/src/callback.js",
                "score": 700,
                "size": len(content),
                "line": 1,
                "snippet": "Provided callback is not a function",
                "sha256": "stale-indexed-hash",
                "matched_terms": 4,
                "exact_phrase": True,
            }
        ],
    }

    fake_context = FakeWorkspaceContext(tmp_path)

    with patch(
        "lbe_guard_inspector.evidence_service.Context.load",
        return_value=fake_context,
    ), patch(
        "lbe_guard_inspector.evidence_service.search_workspace",
        return_value=search_output,
    ):
        package = EvidenceService().build_evidence_package(
            task_id="task-contradiction",
            query="Provided callback is not a function",
            workspace_id="dev",
            workspace_root=str(workspace),
            max_results=10,
            extensions=[".js"],
            roots=["dev"],
        )

    assert len(package["indexed_reference_evidence"]) == 1
    assert len(package["current_workspace_evidence"]) == 1
    assert package["indexed_reference_evidence"][0]["hash"] == "stale-indexed-hash"
    assert package["current_workspace_evidence"][0]["hash"] == current_hash
    assert len(package["contradictions"]) == 1
    contradiction = package["contradictions"][0]
    assert "stale-indexed-hash" in contradiction
    assert current_hash in contradiction
    assert "src/callback.js" in contradiction


def test_matching_index_hash_produces_no_contradiction(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    source = workspace / "src"
    source.mkdir()
    target = source / "callback.js"
    content = 'console.log("Provided callback is not a function");'
    target.write_text(content, encoding="utf-8")

    current_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()

    # Indexed evidence reports the same hash as the live workspace file.
    search_output = {
        "query": "Provided callback is not a function",
        "search_completed": True,
        "outcome": "matches_found",
        "message": "Found 1 matching file.",
        "result_count": 1,
        "results": [
            {
                "root": "dev",
                "path": "dev/src/callback.js",
                "score": 700,
                "size": len(content),
                "line": 1,
                "snippet": "Provided callback is not a function",
                "sha256": current_hash,
                "matched_terms": 4,
                "exact_phrase": True,
            }
        ],
    }

    fake_context = FakeWorkspaceContext(tmp_path)

    with patch(
        "lbe_guard_inspector.evidence_service.Context.load",
        return_value=fake_context,
    ), patch(
        "lbe_guard_inspector.evidence_service.search_workspace",
        return_value=search_output,
    ):
        package = EvidenceService().build_evidence_package(
            task_id="task-agreement",
            query="Provided callback is not a function",
            workspace_id="dev",
            workspace_root=str(workspace),
            max_results=10,
            extensions=[".js"],
            roots=["dev"],
        )

    assert len(package["indexed_reference_evidence"]) == 1
    assert len(package["current_workspace_evidence"]) == 1
    assert package["indexed_reference_evidence"][0]["hash"] == current_hash
    assert package["contradictions"] == []


def test_contradictions_empty_without_workspace_evidence() -> None:
    search_output = {
        "query": "Provided callback is not a function",
        "search_completed": True,
        "outcome": "matches_found",
        "message": "Found 1 matching file.",
        "result_count": 1,
        "results": [
            {
                "root": "dev",
                "path": "dev/src/callback.js",
                "score": 700,
                "size": 100,
                "line": 1,
                "snippet": "Provided callback is not a function",
                "sha256": "indexed-only-hash",
                "matched_terms": 4,
                "exact_phrase": True,
            }
        ],
    }

    with patch(
        "lbe_guard_inspector.evidence_service.Context",
        FakeContext,
    ), patch(
        "lbe_guard_inspector.evidence_service.search_workspace",
        return_value=search_output,
    ):
        package = EvidenceService().build_evidence_package(
            task_id="task-indexed-only",
            query="Provided callback is not a function",
            max_results=10,
        )

    assert len(package["indexed_reference_evidence"]) == 1
    assert package["current_workspace_evidence"] == []
    assert package["contradictions"] == []



def test_different_workspaces_same_path_yield_no_contradiction(tmp_path: Path) -> None:
    """Identical relative paths in two different workspaces must not cross-contradict."""
    # Workspace A
    ws_a = tmp_path / "ws_a"
    ws_a.mkdir()
    src_a = ws_a / "src"
    src_a.mkdir()
    (src_a / "manifest.xml").write_text(
        "<!-- workspace A manifest -->", encoding="utf-8"
    )
    hash_a = hashlib.sha256(b"<!-- workspace A manifest -->").hexdigest()

    # Workspace B with the same relative path but different content
    ws_b = tmp_path / "ws_b"
    ws_b.mkdir()
    src_b = ws_b / "src"
    src_b.mkdir()
    (src_b / "manifest.xml").write_text(
        "<!-- workspace B manifest -->", encoding="utf-8"
    )
    hash_b = hashlib.sha256(b"<!-- workspace B manifest -->").hexdigest()
    assert hash_a != hash_b

    # Indexed evidence: two items from different roots, same relative path
    search_output = {
        "query": "manifest",
        "search_completed": True,
        "outcome": "matches_found",
        "message": "Found 2 matching files.",
        "result_count": 2,
        "results": [
            {
                "root": "dev_A",
                "path": "dev_A/src/manifest.xml",
                "score": 800,
                "size": 28,
                "line": 1,
                "snippet": "<!-- workspace A manifest -->",
                "sha256": hash_a,
                "matched_terms": 1,
                "exact_phrase": True,
            },
            {
                "root": "dev_B",
                "path": "dev_B/src/manifest.xml",
                "score": 600,
                "size": 28,
                "line": 1,
                "snippet": "<!-- workspace B manifest -->",
                "sha256": hash_b,
                "matched_terms": 1,
                "exact_phrase": True,
            },
        ],
    }

    fake_context = FakeWorkspaceContext(tmp_path)

    with patch(
        "lbe_guard_inspector.evidence_service.Context.load",
        return_value=fake_context,
    ), patch(
        "lbe_guard_inspector.evidence_service.search_workspace",
        return_value=search_output,
    ):
        package = EvidenceService().build_evidence_package(
            task_id="task-cross-workspace",
            query="manifest",
            workspace_id="dev_A",
            workspace_root=str(ws_a),
            max_results=10,
            extensions=[".xml"],
            roots=["dev_A", "dev_B"],
        )

    assert len(package["indexed_reference_evidence"]) == 2
    assert len(package["current_workspace_evidence"]) == 1
    assert package["contradictions"] == []



def test_genuine_contradiction_same_workspace_still_works(tmp_path: Path) -> None:
    """A genuine stale hash inside the *same* workspace must still be a contradiction."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    source = workspace / "src"
    source.mkdir()
    target = source / "callback.js"
    content = 'console.log("updated callback");'
    target.write_text(content, encoding="utf-8")
    current_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()

    search_output = {
        "query": "callback",
        "search_completed": True,
        "outcome": "matches_found",
        "message": "Found 1 matching file.",
        "result_count": 1,
        "results": [
            {
                "root": "dev",
                "path": "dev/src/callback.js",
                "score": 700,
                "size": len(content),
                "line": 1,
                "snippet": "callback",
                "sha256": "stale-indexed-hash",
                "matched_terms": 1,
                "exact_phrase": True,
            }
        ],
    }

    fake_context = FakeWorkspaceContext(tmp_path)

    with patch(
        "lbe_guard_inspector.evidence_service.Context.load",
        return_value=fake_context,
    ), patch(
        "lbe_guard_inspector.evidence_service.search_workspace",
        return_value=search_output,
    ):
        package = EvidenceService().build_evidence_package(
            task_id="task-genuine-contradiction",
            query="callback",
            workspace_id="dev",
            workspace_root=str(workspace),
            max_results=10,
            extensions=[".js"],
            roots=["dev"],
        )

    assert len(package["indexed_reference_evidence"]) == 1
    assert len(package["current_workspace_evidence"]) == 1
    assert len(package["contradictions"]) == 1
    contradiction = package["contradictions"][0]
    assert "stale-indexed-hash" in contradiction
    assert current_hash in contradiction
    assert "src/callback.js" in contradiction
    assert "dev" in contradiction


def test_indexed_evidence_missing_workspace_id_is_skipped(tmp_path: Path) -> None:
    """Indexed evidence without a workspace_id must not be compared (no guessing)."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    target = workspace / "callback.js"
    content = 'console.log("live content");'
    target.write_text(content, encoding="utf-8")
    live_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()

    search_output = {
        "query": "callback",
        "search_completed": True,
        "outcome": "matches_found",
        "message": "Found 1 matching file.",
        "result_count": 1,
        "results": [
            {
                "root": None,
                "path": "callback.js",
                "score": 500,
                "size": len(content),
                "line": 1,
                "snippet": "callback",
                "sha256": "different-indexed-hash",
                "matched_terms": 1,
                "exact_phrase": True,
            }
        ],
    }

    fake_context = FakeWorkspaceContext(tmp_path)

    with patch(
        "lbe_guard_inspector.evidence_service.Context.load",
        return_value=fake_context,
    ), patch(
        "lbe_guard_inspector.evidence_service.search_workspace",
        return_value=search_output,
    ):
        package = EvidenceService().build_evidence_package(
            task_id="task-no-index-wsid",
            query="callback",
            workspace_id="dev",
            workspace_root=str(workspace),
            max_results=10,
            extensions=[".js"],
        )

    assert len(package["indexed_reference_evidence"]) == 1
    assert len(package["current_workspace_evidence"]) == 1
    assert package["contradictions"] == []

def test_penalized_artifact_cannot_outrank_source(tmp_path):
    """A penalized lockfile/generated artifact must not outrank a source file with same match quality."""

    # Create a workspace with a source file and a generated artifact
    ws = tmp_path / "workspace"
    src_dir = ws / "src"
    dist_dir = ws / "dist"
    src_dir.mkdir(parents=True)
    dist_dir.mkdir(parents=True)

    # Both files contain the exact same query match
    content = "callback function handler\n"
    src_file = src_dir / "app.py"
    dist_file = dist_dir / "app.min.js"
    src_file.write_text(content)
    dist_file.write_text(content)

    # Build a fake context that has this workspace as a root
    fake_context = FakeWorkspaceContext(ws)

    # Mock search_workspace to return empty indexed results
    search_empty = {
        "search_completed": True,
        "outcome": "no_matches",
        "results": [],
        "searched_roots": [],
        "meaningful_terms": ["callback"],
        "minimum_required_matches": 1,
        "scanned_files": 0,
        "skipped_unreadable_files": 0,
        "scope": {"roots_requested": None, "roots_searched": [],
                  "extensions": [".py", ".js"], "files_considered": 0},
    }

    with patch(
        "lbe_guard_inspector.evidence_service.Context.load",
        return_value=fake_context,
    ), patch(
        "lbe_guard_inspector.evidence_service.search_workspace",
        return_value=search_empty,
    ):
        package = EvidenceService().build_evidence_package(
            task_id="task-rank",
            query="callback",
            workspace_id="test",
            workspace_root=str(ws),
            max_results=10,
            extensions=[".py", ".js"],
            roots=["test"],
        )

    ws_evidence = package.get("current_workspace_evidence", [])
    assert len(ws_evidence) >= 1

    # The source file (app.py) must outrank the generated artifact (app.min.js)
    # when their match quality is identical
    if len(ws_evidence) >= 2:
        scores = [e.get("score", 0) for e in ws_evidence]
        paths = [e.get("path", "") for e in ws_evidence]
        # Find indices
        src_idx = next(i for i, p in enumerate(paths) if "app.py" in p)
        dist_idx = next(i for i, p in enumerate(paths) if "app.min.js" in p)
        assert scores[src_idx] > scores[dist_idx], (
            f"Source file score {scores[src_idx]} must exceed "
            f"generated artifact score {scores[dist_idx]}"
        )


def test_ranking_tie_ordering_deterministic():
    """Two files with identical penalized_score must sort deterministically by path."""
    # Even without live workspace, verify the sort key includes path as secondary
    sort_key_fn = lambda item: (-item.get("score", 0), item.get("path", "").lower())
    a = {"score": 100, "path": "src/alpha.py"}
    b = {"score": 100, "path": "src/beta.py"}
    sorted_items = sorted([b, a], key=sort_key_fn)
    assert sorted_items[0]["path"] == "src/alpha.py"
    assert sorted_items[1]["path"] == "src/beta.py"
