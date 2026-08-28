from __future__ import annotations

import json
import os
import subprocess
import sys
from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from catalysis_workbench._canonical_json import canonical_json_bytes
from catalysis_workbench.workflow.batch import BatchRunRecord
from catalysis_workbench.workflow.execution import WorkflowRun
from catalysis_workbench.workflow.qa import QAFinding, QAReport, QAStatus
from catalysis_workbench.workflow.recipe import RecipeStep, WorkflowRecipe
from catalysis_workbench.workspace import create_workspace
from catalysis_workbench.workspace.assets import import_asset
from catalysis_workbench.workspace.evidence import (
    EvidenceLedger,
    EvidenceRecord,
    append_evidence,
    create_evidence_ledger,
    open_evidence_ledger,
    record_evidence,
    save_evidence_ledger,
)
from catalysis_workbench.workspace.manifest import WorkspaceError


def _record(
    *,
    record_id: str = "record",
    kind: str = "artifact",
    digest: str = "0" * 64,
    asset_ids: tuple[str, ...] = (),
    related_record_ids: tuple[str, ...] = (),
) -> EvidenceRecord:
    return EvidenceRecord(
        record_id=record_id,
        kind=kind,
        evidence_sha256=digest,
        asset_ids=asset_ids,
        related_record_ids=related_record_ids,
    )


def _recipe() -> WorkflowRecipe:
    return WorkflowRecipe(
        schema_version=1,
        inputs=("source",),
        steps=(
            RecipeStep(
                step_id="step",
                operation_id="explicit.test.operation",
                inputs={"series": "source"},
                outputs={"series": "result"},
                parameters={},
            ),
        ),
        outputs={"result": "result"},
    )


def test_evidence_record_and_ledger_are_frozen_and_ordered() -> None:
    first = _record(record_id="first", digest="1" * 64)
    second = _record(record_id="second", digest="2" * 64)
    source = [first, second]
    ledger = EvidenceLedger(schema_version=1, records=source)
    source.reverse()

    assert ledger.records == (first, second)
    with pytest.raises(FrozenInstanceError):
        first.record_id = "changed"  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        ledger.records = ()  # type: ignore[misc]


def test_evidence_identity_is_order_sensitive() -> None:
    first = _record(record_id="first", digest="1" * 64)
    second = _record(record_id="second", digest="2" * 64)
    left = EvidenceLedger(schema_version=1, records=(first, second))
    right = EvidenceLedger(schema_version=1, records=(second, first))
    assert left.ledger_sha256 != right.ledger_sha256


@pytest.mark.parametrize("kind", ["", "run", "figure", "WORKFLOW_RUN"])
def test_evidence_kind_is_closed(kind: str) -> None:
    with pytest.raises(WorkspaceError, match="kind"):
        _record(kind=kind)


@pytest.mark.parametrize("digest", ["", "0" * 63, "0" * 65, "G" * 64, "A" * 64])
def test_evidence_digest_is_strict_sha256(digest: str) -> None:
    with pytest.raises(WorkspaceError, match="SHA-256"):
        _record(digest=digest)


def test_evidence_association_ids_are_unique_and_not_self_related() -> None:
    with pytest.raises(WorkspaceError, match="unique"):
        _record(asset_ids=("asset", "asset"))
    with pytest.raises(WorkspaceError, match="itself"):
        _record(record_id="same", related_record_ids=("same",))


def test_ledger_rejects_duplicate_ids_and_unknown_relations() -> None:
    with pytest.raises(WorkspaceError, match="unique"):
        EvidenceLedger(
            schema_version=1,
            records=(
                _record(record_id="same", digest="1" * 64),
                _record(record_id="same", digest="2" * 64),
            ),
        )
    with pytest.raises(WorkspaceError, match="unknown records"):
        EvidenceLedger(
            schema_version=1,
            records=(
                _record(record_id="child", related_record_ids=("missing",)),
            ),
        )


def test_record_evidence_reuses_existing_authoritative_digests() -> None:
    recipe = _recipe()
    workflow_run = WorkflowRun(
        recipe_sha256=recipe.recipe_sha256,
        content_sha256="1" * 64,
        record_sha256="2" * 64,
        outputs={},
        output_identities={},
        steps=(),
        environment_evidence={},
    )
    batch = BatchRunRecord(
        recipe_sha256=recipe.recipe_sha256,
        error_policy="raise",
        items=(),
        record_sha256="3" * 64,
        environment_evidence={},
    )
    report = QAReport(
        (
            QAFinding(
                check_id="explicit",
                status=QAStatus.PASS,
                code="ok",
            ),
        )
    )

    assert record_evidence("recipe", recipe).evidence_sha256 == recipe.recipe_sha256
    assert record_evidence("run", workflow_run).evidence_sha256 == workflow_run.record_sha256
    assert record_evidence("batch", batch).evidence_sha256 == batch.record_sha256
    assert record_evidence("qa", report).evidence_sha256 == report.report_sha256


def test_record_evidence_rejects_unreviewed_object() -> None:
    with pytest.raises(TypeError, match="evidence must be"):
        record_evidence("bad", object())  # type: ignore[arg-type]


def test_create_and_open_empty_evidence_ledger(tmp_path: Path) -> None:
    root = tmp_path / "workspace"
    create_workspace(root)
    ledger = create_evidence_ledger(root)

    assert ledger.records == ()
    expected = {"schema_version": 1, "records": []}
    assert (root / "workspace-evidence.json").read_bytes() == canonical_json_bytes(expected) + b"\n"
    assert open_evidence_ledger(root) == ledger


def test_create_evidence_ledger_requires_existing_workspace(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        create_evidence_ledger(tmp_path / "missing")


def test_create_evidence_ledger_refuses_existing_path(tmp_path: Path) -> None:
    root = tmp_path / "workspace"
    create_workspace(root)
    create_evidence_ledger(root)
    with pytest.raises(FileExistsError):
        create_evidence_ledger(root)


def test_save_refuses_overwrite_by_default(tmp_path: Path) -> None:
    root = tmp_path / "workspace"
    create_workspace(root)
    create_evidence_ledger(root)
    with pytest.raises(FileExistsError):
        save_evidence_ledger(EvidenceLedger(schema_version=1, records=()), root)


def test_append_persists_asset_and_record_associations_in_literal_order(tmp_path: Path) -> None:
    root = tmp_path / "workspace"
    source = tmp_path / "source.bin"
    source.write_bytes(b"source")
    create_workspace(root)
    manifest = import_asset(
        root,
        source,
        asset_id="source",
        asset_type="source-file",
        policy="reference",
    )
    create_evidence_ledger(root)

    first = _record(
        record_id="artifact",
        digest=manifest.assets[0].content_sha256 or "0" * 64,
        asset_ids=("source",),
    )
    second = _record(
        record_id="analysis",
        kind="qa_report",
        digest="2" * 64,
        asset_ids=("source",),
        related_record_ids=("artifact",),
    )

    append_evidence(root, first)
    ledger = append_evidence(root, second)

    assert tuple(record.record_id for record in ledger.records) == ("artifact", "analysis")
    assert open_evidence_ledger(root) == ledger


def test_append_rejects_unknown_asset_before_mutation(tmp_path: Path) -> None:
    root = tmp_path / "workspace"
    create_workspace(root)
    original = create_evidence_ledger(root)
    with pytest.raises(WorkspaceError, match="unknown assets"):
        append_evidence(root, _record(asset_ids=("missing",)))
    assert open_evidence_ledger(root) == original


def test_append_rejects_unavailable_related_record_before_mutation(tmp_path: Path) -> None:
    root = tmp_path / "workspace"
    create_workspace(root)
    original = create_evidence_ledger(root)
    with pytest.raises(WorkspaceError, match="unavailable records"):
        append_evidence(root, _record(related_record_ids=("future",)))
    assert open_evidence_ledger(root) == original


def test_append_rejects_record_id_collision_before_mutation(tmp_path: Path) -> None:
    root = tmp_path / "workspace"
    create_workspace(root)
    create_evidence_ledger(root)
    append_evidence(root, _record(record_id="same", digest="1" * 64))
    before = open_evidence_ledger(root)
    with pytest.raises(WorkspaceError, match="collision"):
        append_evidence(root, _record(record_id="same", digest="2" * 64))
    assert open_evidence_ledger(root) == before


def test_open_rejects_unknown_fields_and_duplicate_json_keys(tmp_path: Path) -> None:
    root = tmp_path / "workspace"
    create_workspace(root)
    create_evidence_ledger(root)
    path = root / "workspace-evidence.json"

    path.write_text('{"extra":true,"records":[],"schema_version":1}', encoding="utf-8")
    with pytest.raises(WorkspaceError, match="unknown"):
        open_evidence_ledger(root)

    path.write_text(
        '{"records":[],"schema_version":1,"schema_version":1}',
        encoding="utf-8",
    )
    with pytest.raises(WorkspaceError, match="cannot load"):
        open_evidence_ledger(root)


def test_ledger_digest_is_independent_of_workspace_root(tmp_path: Path) -> None:
    first_root = tmp_path / "first"
    second_root = tmp_path / "second"
    create_workspace(first_root)
    create_workspace(second_root)
    create_evidence_ledger(first_root)
    create_evidence_ledger(second_root)

    record = _record(record_id="same", digest="1" * 64)
    first = append_evidence(first_root, record)
    second = append_evidence(second_root, record)
    assert first.ledger_sha256 == second.ledger_sha256


def test_serialized_identity_excludes_runtime_metadata(tmp_path: Path) -> None:
    root = tmp_path / "workspace"
    create_workspace(root)
    create_evidence_ledger(root)
    append_evidence(root, _record())
    text = (root / "workspace-evidence.json").read_text(encoding="utf-8")
    for forbidden in ("timestamp", "hostname", "pid", "traceback", "temporary"):
        assert forbidden not in text.lower()


def test_overwrite_replaces_hardlink_without_mutating_external_target(tmp_path: Path) -> None:
    root = tmp_path / "workspace"
    create_workspace(root)
    create_evidence_ledger(root)
    external = tmp_path / "external.json"
    external.write_text("external-content", encoding="utf-8")
    path = root / "workspace-evidence.json"
    path.unlink()
    try:
        os.link(external, path)
    except (OSError, NotImplementedError) as exc:
        pytest.skip(f"hard links unavailable: {exc}")

    ledger = EvidenceLedger(schema_version=1, records=(_record(),))
    save_evidence_ledger(ledger, root, overwrite=True)

    assert external.read_text(encoding="utf-8") == "external-content"
    assert open_evidence_ledger(root) == ledger


def test_open_rejects_symlink_ledger(tmp_path: Path) -> None:
    root = tmp_path / "workspace"
    outside = tmp_path / "outside.json"
    create_workspace(root)
    outside.write_text('{"records":[],"schema_version":1}', encoding="utf-8")
    path = root / "workspace-evidence.json"
    try:
        path.symlink_to(outside)
    except (OSError, NotImplementedError) as exc:
        pytest.skip(f"symbolic links unavailable: {exc}")
    with pytest.raises(WorkspaceError, match="symbolic link"):
        open_evidence_ledger(root)


def test_evidence_module_import_has_no_presentation_side_effects() -> None:
    code = """
import sys
import catalysis_workbench.workspace.evidence as evidence
assert evidence.__all__ == [
    "EvidenceLedger",
    "EvidenceRecord",
    "append_evidence",
    "create_evidence_ledger",
    "open_evidence_ledger",
    "record_evidence",
    "save_evidence_ledger",
]
for forbidden in ("matplotlib", "pyvista", "vtk"):
    assert not any(name == forbidden or name.startswith(forbidden + ".") for name in sys.modules)
"""
    subprocess.run([sys.executable, "-c", code], check=True, env=os.environ.copy())
