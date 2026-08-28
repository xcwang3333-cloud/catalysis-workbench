"""GUI-neutral, transaction-safe CatalysisWorkbench application session state."""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, replace
from pathlib import Path
from typing import TYPE_CHECKING, Any

from catalysis_workbench.workflow import (
    QAFinding,
    QAReport,
    WorkflowRecipe,
    WorkflowRun,
    execute_recipe,
    run_qa,
)
from catalysis_workbench.workspace import (
    WorkspaceManifest,
    open_workspace as _open_workspace,
)
from catalysis_workbench.workspace.composition import (
    load_figure_spec_asset,
    load_recipe_asset,
    save_figure_spec_asset,
    save_recipe_asset,
)

from .commands import RecipeEditCommand, apply_recipe_edit

if TYPE_CHECKING:
    from catalysis_workbench.visualization import FigureSpec


class ApplicationError(RuntimeError):
    """Raised when a GUI-neutral application command cannot be committed safely."""


def _identifier(value: object, *, label: str) -> str:
    if type(value) is not str or not value or value != value.strip():
        raise ApplicationError(
            f"{label} must be a non-empty string without surrounding whitespace"
        )
    return value


def _identifiers(value: object, *, label: str) -> tuple[str, ...]:
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        raise ApplicationError(f"{label} must be an ordered sequence")
    checked = tuple(_identifier(item, label=f"{label} item") for item in value)
    if len(set(checked)) != len(checked):
        raise ApplicationError(f"{label} values must be unique")
    return checked


def _manifest_digest(value: object) -> str:
    if (
        type(value) is not str
        or len(value) != 64
        or value != value.lower()
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise ApplicationError("workspace_manifest_sha256 must be a lowercase SHA-256")
    return value


@dataclass(frozen=True, slots=True)
class ApplicationState:
    """Immutable in-memory state for one GUI-neutral application session."""

    workspace_root: Path | None = None
    workspace_manifest_sha256: str | None = None
    selected_asset_ids: Sequence[str] = ()
    selected_recipe_asset_id: str | None = None
    recipe: WorkflowRecipe | None = None
    recipe_dirty: bool = False
    selected_figure_spec_asset_id: str | None = None
    figure_spec: FigureSpec | None = None
    figure_spec_dirty: bool = False
    last_workflow_run: WorkflowRun | None = None
    last_qa_report: QAReport | None = None
    revision: int = 0

    def __post_init__(self) -> None:
        root = self.workspace_root
        digest = self.workspace_manifest_sha256
        if root is None:
            if digest is not None:
                raise ApplicationError(
                    "closed application state cannot retain a workspace manifest digest"
                )
        else:
            if not isinstance(root, Path):
                raise TypeError("workspace_root must be a pathlib.Path or None")
            if digest is None:
                raise ApplicationError(
                    "open application state requires workspace_manifest_sha256"
                )
            digest = _manifest_digest(digest)

        selected_assets = _identifiers(
            self.selected_asset_ids,
            label="selected_asset_ids",
        )
        recipe_asset_id = self.selected_recipe_asset_id
        if recipe_asset_id is not None:
            recipe_asset_id = _identifier(
                recipe_asset_id,
                label="selected_recipe_asset_id",
            )
        if (recipe_asset_id is None) != (self.recipe is None):
            raise ApplicationError(
                "selected_recipe_asset_id and recipe must be present together"
            )
        if self.recipe is not None and not isinstance(self.recipe, WorkflowRecipe):
            raise TypeError("recipe must be a WorkflowRecipe or None")
        if type(self.recipe_dirty) is not bool:
            raise TypeError("recipe_dirty must be a bool")
        if self.recipe_dirty and self.recipe is None:
            raise ApplicationError("recipe_dirty requires a selected recipe")

        figure_asset_id = self.selected_figure_spec_asset_id
        if figure_asset_id is not None:
            figure_asset_id = _identifier(
                figure_asset_id,
                label="selected_figure_spec_asset_id",
            )
        if (figure_asset_id is None) != (self.figure_spec is None):
            raise ApplicationError(
                "selected_figure_spec_asset_id and figure_spec must be present together"
            )
        if self.figure_spec is not None:
            from catalysis_workbench.visualization import FigureSpec

            if not isinstance(self.figure_spec, FigureSpec):
                raise TypeError("figure_spec must be a FigureSpec or None")
        if type(self.figure_spec_dirty) is not bool:
            raise TypeError("figure_spec_dirty must be a bool")
        if self.figure_spec_dirty and self.figure_spec is None:
            raise ApplicationError(
                "figure_spec_dirty requires a selected FigureSpec"
            )
        if self.last_workflow_run is not None and not isinstance(
            self.last_workflow_run, WorkflowRun
        ):
            raise TypeError("last_workflow_run must be a WorkflowRun or None")
        if self.last_qa_report is not None and not isinstance(
            self.last_qa_report, QAReport
        ):
            raise TypeError("last_qa_report must be a QAReport or None")
        if type(self.revision) is not int or self.revision < 0:
            raise ApplicationError("application revision must be a non-negative integer")

        if root is None and (
            selected_assets
            or recipe_asset_id is not None
            or figure_asset_id is not None
            or self.last_workflow_run is not None
            or self.last_qa_report is not None
        ):
            raise ApplicationError("closed application state cannot retain workspace state")

        object.__setattr__(self, "workspace_manifest_sha256", digest)
        object.__setattr__(self, "selected_asset_ids", selected_assets)
        object.__setattr__(self, "selected_recipe_asset_id", recipe_asset_id)
        object.__setattr__(
            self,
            "selected_figure_spec_asset_id",
            figure_asset_id,
        )


class ApplicationSession:
    """Headless controller that commits state only after successful commands."""

    def __init__(self) -> None:
        self._state = ApplicationState()

    @property
    def state(self) -> ApplicationState:
        """Return the current immutable application state."""
        return self._state

    def _workspace_root(self) -> Path:
        root = self._state.workspace_root
        if root is None:
            raise ApplicationError("no workspace is open")
        return root

    def _assert_manifest_unchanged(self, expected_sha256: str) -> WorkspaceManifest:
        manifest = _open_workspace(self._workspace_root())
        if manifest.manifest_sha256 != expected_sha256:
            raise ApplicationError(
                "workspace changed during the application command; refresh explicitly"
            )
        return manifest

    def _commit(self, **changes: Any) -> ApplicationState:
        if (
            self._state.workspace_root is not None
            and "workspace_root" not in changes
            and "workspace_manifest_sha256" not in changes
        ):
            expected = self._state.workspace_manifest_sha256
            if expected is None:
                raise ApplicationError("open application state lost its manifest identity")
            self._assert_manifest_unchanged(expected)
        candidate = replace(
            self._state,
            revision=self._state.revision + 1,
            **changes,
        )
        self._state = candidate
        return candidate

    def open_workspace(self, root: str | Path) -> ApplicationState:
        """Open one explicit existing workspace and reset transient selections."""
        manifest = _open_workspace(root)
        root_path = Path(root).resolve(strict=True)
        observed = _open_workspace(root_path)
        if observed.manifest_sha256 != manifest.manifest_sha256:
            raise ApplicationError(
                "workspace changed while it was being opened; retry explicitly"
            )
        return self._commit(
            workspace_root=root_path,
            workspace_manifest_sha256=manifest.manifest_sha256,
            selected_asset_ids=(),
            selected_recipe_asset_id=None,
            recipe=None,
            recipe_dirty=False,
            selected_figure_spec_asset_id=None,
            figure_spec=None,
            figure_spec_dirty=False,
            last_workflow_run=None,
            last_qa_report=None,
        )

    def close_workspace(self) -> ApplicationState:
        """Close the current workspace and discard only in-memory session state."""
        return self._commit(
            workspace_root=None,
            workspace_manifest_sha256=None,
            selected_asset_ids=(),
            selected_recipe_asset_id=None,
            recipe=None,
            recipe_dirty=False,
            selected_figure_spec_asset_id=None,
            figure_spec=None,
            figure_spec_dirty=False,
            last_workflow_run=None,
            last_qa_report=None,
        )

    def _current_manifest(self) -> WorkspaceManifest:
        root = self._workspace_root()
        manifest = _open_workspace(root)
        if manifest.manifest_sha256 != self._state.workspace_manifest_sha256:
            raise ApplicationError(
                "workspace changed outside the application session; refresh explicitly"
            )
        return manifest

    def refresh_workspace(
        self,
        *,
        discard_edits: bool = False,
    ) -> ApplicationState:
        """Explicitly accept current workspace state without silently losing edits."""
        if type(discard_edits) is not bool:
            raise TypeError("discard_edits must be a bool")
        root = self._workspace_root()
        manifest = _open_workspace(root)
        if manifest.manifest_sha256 == self._state.workspace_manifest_sha256:
            return self._state
        if (self._state.recipe_dirty or self._state.figure_spec_dirty) and not discard_edits:
            raise ApplicationError(
                "workspace refresh would discard dirty recipe or FigureSpec state"
            )

        available = {asset.asset_id for asset in manifest.assets}
        selected = set(self._state.selected_asset_ids)
        if self._state.selected_recipe_asset_id is not None:
            selected.add(self._state.selected_recipe_asset_id)
        if self._state.selected_figure_spec_asset_id is not None:
            selected.add(self._state.selected_figure_spec_asset_id)
        missing = sorted(selected - available)
        if missing:
            raise ApplicationError(
                f"workspace refresh would invalidate selected asset IDs: {missing!r}"
            )

        recipe = None
        if self._state.selected_recipe_asset_id is not None:
            recipe = load_recipe_asset(root, self._state.selected_recipe_asset_id)
        figure_spec = None
        if self._state.selected_figure_spec_asset_id is not None:
            figure_spec = load_figure_spec_asset(
                root,
                self._state.selected_figure_spec_asset_id,
            )
        observed = _open_workspace(root)
        if observed.manifest_sha256 != manifest.manifest_sha256:
            raise ApplicationError(
                "workspace changed while it was being refreshed; retry explicitly"
            )
        return self._commit(
            workspace_manifest_sha256=manifest.manifest_sha256,
            recipe=recipe,
            recipe_dirty=False,
            figure_spec=figure_spec,
            figure_spec_dirty=False,
            last_workflow_run=None,
            last_qa_report=None,
        )

    def select_assets(self, asset_ids: Sequence[str]) -> ApplicationState:
        """Select explicitly named workspace assets in caller-provided order."""
        manifest = self._current_manifest()
        checked = _identifiers(asset_ids, label="asset_ids")
        available = {asset.asset_id for asset in manifest.assets}
        missing = [asset_id for asset_id in checked if asset_id not in available]
        if missing:
            raise ApplicationError(f"unknown workspace asset IDs: {missing!r}")
        return self._commit(selected_asset_ids=checked)

    def select_recipe(self, asset_id: str) -> ApplicationState:
        """Select and load one reviewed workspace recipe snapshot."""
        self._current_manifest()
        root = self._workspace_root()
        checked = _identifier(asset_id, label="recipe asset_id")
        recipe = load_recipe_asset(root, checked)
        return self._commit(
            selected_recipe_asset_id=checked,
            recipe=recipe,
            recipe_dirty=False,
            last_workflow_run=None,
            last_qa_report=None,
        )

    def edit_recipe(self, command: RecipeEditCommand) -> ApplicationState:
        """Apply one closed-set ordered recipe edit in memory."""
        self._current_manifest()
        recipe = self._state.recipe
        if recipe is None:
            raise ApplicationError("no recipe is selected")
        edited = apply_recipe_edit(recipe, command)
        return self._commit(
            recipe=edited,
            recipe_dirty=True,
            last_workflow_run=None,
            last_qa_report=None,
        )

    def save_recipe(
        self,
        *,
        asset_id: str,
        destination: str,
    ) -> ApplicationState:
        """Snapshot the current recipe through the reviewed workspace bridge."""
        before = self._current_manifest()
        root = self._workspace_root()
        recipe = self._state.recipe
        if recipe is None:
            raise ApplicationError("no recipe is selected")
        asset = save_recipe_asset(
            root,
            recipe,
            asset_id=asset_id,
            destination=destination,
        )
        expected = WorkspaceManifest(
            schema_version=before.schema_version,
            assets=(*before.assets, asset),
        )
        manifest = _open_workspace(root)
        if manifest.manifest_sha256 != expected.manifest_sha256:
            raise ApplicationError(
                "workspace changed concurrently with recipe save; refresh explicitly"
            )
        return self._commit(
            workspace_manifest_sha256=manifest.manifest_sha256,
            selected_recipe_asset_id=asset.asset_id,
            recipe_dirty=False,
        )

    def select_figure_spec(self, asset_id: str) -> ApplicationState:
        """Select and load one reviewed workspace FigureSpec snapshot."""
        self._current_manifest()
        root = self._workspace_root()
        checked = _identifier(asset_id, label="FigureSpec asset_id")
        spec = load_figure_spec_asset(root, checked)
        return self._commit(
            selected_figure_spec_asset_id=checked,
            figure_spec=spec,
            figure_spec_dirty=False,
        )

    def _figure(self) -> FigureSpec:
        self._current_manifest()
        spec = self._state.figure_spec
        if spec is None:
            raise ApplicationError("no FigureSpec is selected")
        return spec

    def update_figure_spec(self, **changes: Any) -> ApplicationState:
        """Apply reviewed top-level FigureSpec updates without rendering."""
        spec = self._figure().updated(**changes)
        return self._commit(figure_spec=spec, figure_spec_dirty=True)

    def update_figure_layout(self, **changes: Any) -> ApplicationState:
        """Apply reviewed FigureSpec layout updates without rendering."""
        spec = self._figure().with_layout(**changes)
        return self._commit(figure_spec=spec, figure_spec_dirty=True)

    def update_figure_style(self, **changes: Any) -> ApplicationState:
        """Apply reviewed FigureSpec style updates without rendering."""
        spec = self._figure().with_style(**changes)
        return self._commit(figure_spec=spec, figure_spec_dirty=True)

    def update_figure_export(self, **changes: Any) -> ApplicationState:
        """Apply reviewed FigureSpec export updates without rendering."""
        spec = self._figure().with_export(**changes)
        return self._commit(figure_spec=spec, figure_spec_dirty=True)

    def save_figure_spec(
        self,
        *,
        asset_id: str,
        destination: str,
    ) -> ApplicationState:
        """Snapshot the current FigureSpec through the reviewed workspace bridge."""
        before = self._current_manifest()
        root = self._workspace_root()
        spec = self._state.figure_spec
        if spec is None:
            raise ApplicationError("no FigureSpec is selected")
        asset = save_figure_spec_asset(
            root,
            spec,
            asset_id=asset_id,
            destination=destination,
        )
        expected = WorkspaceManifest(
            schema_version=before.schema_version,
            assets=(*before.assets, asset),
        )
        manifest = _open_workspace(root)
        if manifest.manifest_sha256 != expected.manifest_sha256:
            raise ApplicationError(
                "workspace changed concurrently with FigureSpec save; refresh explicitly"
            )
        return self._commit(
            workspace_manifest_sha256=manifest.manifest_sha256,
            selected_figure_spec_asset_id=asset.asset_id,
            figure_spec_dirty=False,
        )

    def execute_recipe(
        self,
        inputs: Mapping[str, object],
        *,
        input_identities: Mapping[str, str],
    ) -> WorkflowRun:
        """Execute the selected recipe only through the reviewed workflow API."""
        self._current_manifest()
        recipe = self._state.recipe
        if recipe is None:
            raise ApplicationError("no recipe is selected")
        result = execute_recipe(
            recipe,
            inputs,
            input_identities=input_identities,
        )
        self._commit(last_workflow_run=result, last_qa_report=None)
        return result

    def run_qa(self, findings: Iterable[QAFinding]) -> QAReport:
        """Aggregate only explicitly supplied reviewed QA findings."""
        self._current_manifest()
        report = run_qa(findings)
        self._commit(last_qa_report=report)
        return report
