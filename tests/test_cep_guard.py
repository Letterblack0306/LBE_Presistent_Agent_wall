from __future__ import annotations

from agent import Context, KnowledgeRoot
from rules.cep import (
    rule_cep_debug_mode,
    rule_cep_host_version,
    rule_cep_menubar_extension,
    rule_cep_no_zip_in_repo,
)


def _context(root):
    return Context(config={}, governance={}, roots=(KnowledgeRoot("target", root),))


def test_cep_host_version_uses_exact_selected_manifest(tmp_path):
    target = tmp_path / "target"; target.mkdir()
    sibling = tmp_path / "sibling"; sibling.mkdir()
    for project, manifest in (
        (target, "<ExtensionManifest><HostList/></ExtensionManifest>"),
        (sibling, "<ExtensionManifest><Host Version=\"24.0\"/></ExtensionManifest>"),
    ):
        (project / "CSXS").mkdir()
        (project / "CSXS" / "manifest.xml").write_text(manifest, encoding="utf-8")

    result = rule_cep_host_version(_context(target), {"roots": ["target"]})

    assert result.status == "failed"
    assert result.evidence["examined_paths"] == ["target/CSXS/manifest.xml"]


def test_cep_debug_and_archive_guards_do_not_read_sibling_project(tmp_path):
    target = tmp_path / "target"; target.mkdir()
    sibling = tmp_path / "sibling"; sibling.mkdir()
    (sibling / "debug.js").write_text("PlayerDebugMode = 1", encoding="utf-8")
    (sibling / "package.zip").write_bytes(b"archive")
    context = _context(target)

    debug = rule_cep_debug_mode(context, {"roots": ["target"]})
    archives = rule_cep_no_zip_in_repo(context, {"roots": ["target"]})

    assert debug.status == "blocked"
    assert debug.evidence["roots_checked"] == ["target"]
    assert archives.status == "passed"
    assert archives.evidence["evidence_source"] == "current_workspace_bounded_scan"


def test_cep_debug_and_archive_guards_report_exact_target_evidence(tmp_path):
    (tmp_path / "settings.js").write_text("const PlayerDebugMode = 1", encoding="utf-8")
    (tmp_path / "release.zxp").write_bytes(b"archive")
    context = _context(tmp_path)

    debug = rule_cep_debug_mode(context, {"roots": ["target"]})
    archives = rule_cep_no_zip_in_repo(context, {"roots": ["target"]})

    assert debug.status == "passed"
    assert debug.evidence["hits"] == [{"path": "target/settings.js", "score": 1}]
    assert archives.status == "failed"
    assert archives.evidence["hits"] == ["target/release.zxp"]


def test_cep_host_version_requires_valid_host_identity_and_version(tmp_path):
    (tmp_path / "CSXS").mkdir()
    (tmp_path / "CSXS" / "manifest.xml").write_text(
        "<ExtensionManifest><Host Name=\"AEFT\" Version=\"24.1\"/></ExtensionManifest>",
        encoding="utf-8",
    )

    result = rule_cep_host_version(_context(tmp_path), {"roots": ["target"]})

    assert result.status == "passed"
    assert result.evidence["host_name"] == "AEFT"

    (tmp_path / "CSXS" / "manifest.xml").write_text(
        "<ExtensionManifest><Host Name=\"AEFT\" Version=\"[24.1, 25.0]\"/></ExtensionManifest>",
        encoding="utf-8",
    )
    assert rule_cep_host_version(_context(tmp_path), {"roots": ["target"]}).status == "passed"


def test_cep_menubar_requires_registered_extension_ui_type_and_nonempty_menu(tmp_path):
    (tmp_path / "CSXS").mkdir()
    manifest = tmp_path / "CSXS" / "manifest.xml"
    manifest.write_text(
        """<ExtensionManifest>
<ExtensionList><Extension Id="com.example.panel"/></ExtensionList>
<DispatchInfoList><Extension Id="com.example.panel"><DispatchInfo>
<Resources><Menu>Example Menu</Menu></Resources><UI><Type>Panel</Type></UI>
</DispatchInfo></Extension></DispatchInfoList>
</ExtensionManifest>""",
        encoding="utf-8",
    )

    result = rule_cep_menubar_extension(_context(tmp_path), {"roots": ["target"]})

    assert result.status == "passed"
    assert result.evidence["extension_id"] == "com.example.panel"

    manifest.write_text("<ExtensionManifest><Menu>Unrelated</Menu></ExtensionManifest>", encoding="utf-8")
    failed = rule_cep_menubar_extension(_context(tmp_path), {"roots": ["target"]})
    assert failed.status == "failed"
