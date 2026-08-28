from __future__ import annotations

import json
import os
import subprocess
import sys
from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from catalysis_workbench._canonical_json import canonical_json_bytes
from catalysis_workbench.workspace import (
    WorkspaceAsset,
    WorkspaceManifest,
    create_workspace,
    save_workspace,
)
from catalysis_workbench.workspace.evidence import (
    EvidenceAssociation,
    EvidenceLedger,
    EvidenceRef,
    WorkspaceEvidenceError,
    append_evidence,
    artifact_evidence,
    batch_run_evidence,
    load_evidence_ledger,
    qa_report_evidence,
    recipe_evidence,
    save_evidence_ledger,
    workflow_run_evidence,
)


def _tracked_workspace(tmp_path: Path) -> tuple[Path, WorkspaceAsset]:
    root = tmp_path / "workspace"
    create_workspace(root)
    data = root / "data"
    data.mkdir()
    (data / "source.bin").write_bytes(b"source")
    asset = WorkspaceAsset(
        asset_id="source",
        asset_type="source-file",
        path="data/source.bin",
        policy="copy",
        content_sha256="a" * 64,
    )
    save_workspace(
        WorkspaceManifest(schema_version=1, assets=(asset,)),
        root,
        overwrite=True,
    )
    return root, asset


def _ref(kind: str = "artifact", digest: str = "a" * 64) -> EvidenceRef:
    return EvidenceRef(kind=kind, sha256=digest)


def _association(
    association_id: str = "record",
    *,
    asset_ids: tuple[str, ...] = ("source",),
    evidence: tuple[EvidenceRef, ...] | None = None,
) -> EvidenceAssociation:
    refs = (_ref(),) if evidence is None else evidence
    return EvidenceAssociation(
        association_id=association_id,
        asset_ids=asset_ids,
        evidence=refs,
    )


def test_evidence_reference_is_strict_and_frozen() -> None:
    ref = _ref()
    assert ref.kind == "artifact"
    with pytest.raises(FrozenInstanceError):
        ref.kind = "recipe"  # type: ignore[misc]


@pytest.mark.parametrize("kind", ["", "unknown", "workflow", "artifact "])
def test_evidence_reference_rejects_unknown_or_ambiguous_kind(kind: str) -> None:
    with pytest.raises(WorkspaceEvidenceError):
        _ref(kind=kind)


@pytest.mark.parametrize("digest", ["", "0" * 63, "0" * 65, "A" * 64, "g" * 64])
def test_evidence_reference_requires_lowercase_sha256(digest: str) -> None:
    with pytest.raises(WorkspaceEvidenceError, match="SHA-256"):
        _ref(digest=digest)


def test_association_preserves_literal_asset_and_evidence_order() -> None:
    first = _ref("recipe", "1" * 64)
    second = _ref("artifact", "2" * 64)
    record = _association(
        asset_ids=("second", "first"),
        evidence=(second, first),
    )
    assert record.asset_ids == ("second", "first")
    assert record.evidence == (second, first)


def test_association_identity_is_order_sensitive() -> None:
    first = _ref("recipe", "1" * 64)
    second = _ref("artifact", "2" * 64)
    left = _association(evidence=(first, second))
    right = _association(evidence=(second, first))
    assert left.association_sha256 != right.association_sha256


@pytest.mark.parametrize("asset_ids", [(), ("source", "source")])
def test_association_requires_nonempty_unique_asset_ids(
    asset_ids: tuple[str, ...],
) -> None:
    with pytest.raises(WorkspaceEvidenceError):
        _association(asset_ids=asset_ids)


def test_association_requires_nonempty_unique_evidence() -> None:
    with pytest.raises(WorkspaceEvidenceError):
        _association(evidence=())
    duplicate = _ref()
    with pytest.raises(WorkspaceEvidenceError, match="unique"):
        _association(evidence=(duplicate, duplicate))


def test_ledger_identity_is_order_sensitive_and_ids_are_unique() -> None:
    first = _association("first")
    second = _association("second", evidence=(_ref("recipe", "2" * 64),))
    left = EvidenceLedger(schema_version=1, records=(first, second))
    right = EvidenceLedger(schema_version=1, records=(second, first))
    assert left.ledger_sha256 != right.ledger_sha256
    with pytest.raises(WorkspaceEvidenceError, match="association_id"):
        EvidenceLedger(schema_version=1, records=(first, first))


def test_recipe_evidence_reuses_recipe_sha256() -> None:
    from catalysis_workbench.workflow.recipe import RecipeStep, WorkflowRecipe

    recipe = WorkflowRecipe(
        schema_version=1,
        inputs=("input",),
        steps=(
            RecipeStep(
                step_id="step",
                operation_id="reviewed.operation",
                inputs={"series": "input"},
                outputs={"series": "processed"},
                parameters={},
            ),
        ),
        outputs={"result": "processed"},
    )
    ref = recipe_evidence(recipe)
    assert ref == EvidenceRef(kind="recipe", sha256=recipe.recipe_sha256)


def test_workflow_run_evidence_reuses_record_sha256() -> None:
    from catalysis_workbench.workflow.execution import WorkflowRun

    run = WorkflowRun(
        recipe_sha256="0" * 64,
        content_sha256="1" * 64,
        record_sha256="2" * 64,
        outputs={},
        output_identities={},
        steps=(),
        environment_evidence={},
    )
    assert workflow_run_evidence(run) == EvidenceRef(
        kind="workflow-run",
        sha256="2" * 64,
    )


def test_batch_run_evidence_reuses_record_sha256() -> None:
    from catalysis_workbench.workflow.batch import BatchRunRecord

    record = BatchRunRecord(
        recipe_sha256="0" * 64,
        error_policy="raise",
        items=(),
        record_sha256="3" * 64,
        environment_evidence={},
    )
    assert batch_run_evidence(record) == EvidenceRef(
        kind="batch-run",
        sha256="3" * 64,
    )


def test_qa_report_evidence_reuses_report_sha256() -> None:
    from catalysis_workbench.workflow.qa import QAFinding, QAReport, QAStatus

    report = QAReport(
        findings=(
            QAFinding(
                check_id="explicit",
                status=QAStatus.PASS,
                code="ok",
            ),
        )
    )
    assert qa_report_evidence(report) == EvidenceRef(
        kind="qa-report",
        sha256=report.report_sha256,
    )


def test_artifact_evidence_reuses_workspace_content_digest(tmp_path: Path) -> None:
    _, asset = _tracked_workspace(tmp_path)
    assert artifact_evidence(asset) == EvidenceRef(
        kind="artifact",
        sha256="a" * 64,
    )


def test_artifact_evidence_rejects_legacy_asset_without_content_digest() -> None:
    asset = WorkspaceAsset(
        asset_id="legacy",
        asset_type="source-file",
        path="data/legacy.txt",
    )
    with pytest.raises(WorkspaceEvidenceError, match="content_sha256"):
        artifact_evidence(asset)


def test_save_and_load_canonical_ledger(tmp_path: Path) -> None:
    root, _ = _tracked_workspace(tmp_path)
    ledger = EvidenceLedger(schema_version=1, records=(_association(),))
    save_evidence_ledger(ledger, root)
    restored = load_evidence_ledger(root)
    assert restored == ledger
    payload = json.loads((root / "evidence.json").read_text(encoding="utf-8"))
    assert (root / "evidence.json").read_bytes() == canonical_json_bytes(payload) + b"\n"


def test_save_refuses_overwrite_by_default(tmp_path: Path) -> None:
    root, _ = _tracked_workspace(tmp_path)
    ledger = EvidenceLedger(schema_version=1, records=(_association(),))
    save_evidence_ledger(ledger, root)
    with pytest.raises(FileExistsError):
        save_evidence_ledger(ledger, root)


def test_save_requires_bool_overwrite(tmp_path: Path) -> None:
    root, _ = _tracked_workspace(tmp_path)
    ledger = EvidenceLedger(schema_version=1, records=())
    with pytest.raises(TypeError):
        save_evidence_ledger(ledger, root, overwrite=1)  # type: ignore[arg-type]


def test_overwrite_replaces_hardlink_without_mutating_external_target(
    tmp_path: Path,
) -> None:
    root, _ = _tracked_workspace(tmp_path)
    first = EvidenceLedger(schema_version=1, records=(_association("first"),))
    save_evidence_ledger(first, root)
    external = tmp_path / "external.txt"
    external.write_text("external-content", encoding="utf-8")
    path = root / "evidence.json"
    path.unlink()
    try:
        os.link(external, path)
    except (OSError, NotImplementedError) as exc:
        pytest.skip(f"hard links unavailable: {exc}")

    second = EvidenceLedger(schema_version=1, records=(_association("second"),))
    save_evidence_ledger(second, root, overwrite=True)

    assert external.read_text(encoding="utf-8") == "external-content"
    assert load_evidence_ledger(root) == second


def test_append_initializes_ledger_and_preserves_literal_record_order(
    tmp_path: Path,
) -> None:
    root, _ = _tracked_workspace(tmp_path)
    first = append_evidence(
        root,
        association_id="first",
        asset_ids=("source",),
        evidence=(_ref("recipe", "1" * 64),),
    )
    assert tuple(item.association_id for item in first.records) == ("first",)
    second = append_evidence(
        root,
        association_id="second",
        asset_ids=("source",),
        evidence=(_ref("artifact", "2" * 64),),
    )
    assert tuple(item.association_id for item in second.records) == ("first", "second")


def test_append_collision_fails_before_persistent_mutation(tmp_path: Path) -> None:
    root, _ = _tracked_workspace(tmp_path)
    append_evidence(
        root,
        association_id="same",
        asset_ids=("source",),
        evidence=(_ref(),),
    )
    before = (root / "evidence.json").read_bytes()
    with pytest.raises(WorkspaceEvidenceError, match="collision"):
        append_evidence(
            root,
            association_id="same",
            asset_ids=("source",),
            evidence=(_ref("recipe", "1" * 64),),
        )
    assert (root / "evidence.json").read_bytes() == before


def test_unknown_asset_id_fails_before_persistent_mutation(tmp_path: Path) -> None:
    root, _ = _tracked_workspace(tmp_path)
    with pytest.raises(WorkspaceEvidenceError, match="unknown workspace assets"):
        append_evidence(
            root,
            association_id="unknown",
            asset_ids=("missing",),
            evidence=(_ref(),),
        )
    assert not (root / "evidence.json").exists()


def test_save_unknown_asset_id_does_not_replace_existing_ledger(
    tmp_path: Path,
) -> None:
    root, _ = _tracked_workspace(tmp_path)
    valid = EvidenceLedger(schema_version=1, records=(_association("valid"),))
    save_evidence_ledger(valid, root)
    before = (root / "evidence.json").read_bytes()
    invalid = EvidenceLedger(
        schema_version=1,
        records=(
            _association(
                "invalid",
                asset_ids=("missing",),
            ),
        ),
    )
    with pytest.raises(WorkspaceEvidenceError, match="unknown workspace assets"):
        save_evidence_ledger(invalid, root, overwrite=True)
    assert (root / "evidence.json").read_bytes() == before


def test_existing_workspace_asset_named_evidence_json_blocks_ledger_mutation(
    tmp_path: Path,
) -> None:
    root = tmp_path / "workspace"
    create_workspace(root)
    path = root / "evidence.json"
    path.write_bytes(b"user-asset")
    asset = WorkspaceAsset(
        asset_id="reserved-collision",
        asset_type="source-file",
        path="evidence.json",
        policy="copy",
        content_sha256="a" * 64,
    )
    save_workspace(
        WorkspaceManifest(schema_version=1, assets=(asset,)),
        root,
        overwrite=True,
    )
    with pytest.raises(WorkspaceEvidenceError, match="conflicts"):
        save_evidence_ledger(EvidenceLedger(schema_version=1, records=()), root)
    assert path.read_bytes() == b"user-asset"


def _symlink_or_skip(target: Path, link: Path) -> None:
    try:
        link.symlink_to(target)
    except (OSError, NotImplementedError) as exc:
        pytest.skip(f"symbolic links unavailable: {exc}")


def test_load_rejects_evidence_file_symlink(tmp_path: Path) -> None:
    root, _ = _tracked_workspace(tmp_path)
    external = tmp_path / "external.json"
    external.write_text('{"records":[],"schema_version":1}', encoding="utf-8")
    _symlink_or_skip(external, root / "evidence.json")
    with pytest.raises(WorkspaceEvidenceError, match="symbolic link"):
        load_evidence_ledger(root)


def test_load_rejects_unknown_fields(tmp_path: Path) -> None:
    root, _ = _tracked_workspace(tmp_path)
    (root / "evidence.json").write_text(
        '{"extra":true,"records":[],"schema_version":1}',
        encoding="utf-8",
    )
    with pytest.raises(WorkspaceEvidenceError, match="unknown"):
        load_evidence_ledger(root)


def test_load_rejects_duplicate_json_keys(tmp_path: Path) -> None:
    root, _ = _tracked_workspace(tmp_path)
    (root / "evidence.json").write_text(
        '{"records":[],"schema_version":1,"schema_version":1}',
        encoding="utf-8",
    )
    with pytest.raises(WorkspaceEvidenceError, match="cannot load"):
        load_evidence_ledger(root)


def test_load_missing_ledger_is_explicit(tmp_path: Path) -> None:
    root, _ = _tracked_workspace(tmp_path)
    with pytest.raises(FileNotFoundError):
        load_evidence_ledger(root)


def test_deterministic_state_contains_no_timestamp_or_traceback_fields(
    tmp_path: Path,
) -> None:
    root, _ = _tracked_workspace(tmp_path)
    append_evidence(
        root,
        association_id="deterministic",
        asset_ids=("source",),
        evidence=(_ref("workflow-run", "4" * 64),),
    )
    payload = json.loads((root / "evidence.json").read_text(encoding="utf-8"))
    serialized = json.dumps(payload, sort_keys=True)
    assert "timestamp" not in serialized
    assert "traceback" not in serialized
    assert "pid" not in serialized
    assert "hostname" not in serialized


def test_evidence_module_import_is_lazy_for_workflow_and_presentation() -> None:
    code = """
import sys
import catalysis_workbench.workspace.evidence as evidence
assert "EvidenceLedger" in evidence.__all__
for forbidden in ("numpy", "matplotlib", "pyvista", "vtk", "pymatgen"):
    assert not any(
        name == forbidden or name.startswith(forbidden + ".")
        for name in sys.modules
    )
"""
    subprocess.run([sys.executable, "-c", code], check=True, env=os.environ.copy())
