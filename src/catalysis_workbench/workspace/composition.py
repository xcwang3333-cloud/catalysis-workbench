"""Workspace composition bridges for reviewed recipes and figure state."""

from __future__ import annotations

import tempfile
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from types import MappingProxyType
from typing import TYPE_CHECKING

from catalysis_workbench._canonical_json import (
    CanonicalJSONError,
    canonical_json_bytes,
    canonical_json_sha256,
    loads_strict_json,
)
from catalysis_workbench.workflow import (
    RecipeStep,
    WorkflowRecipe,
    dump_recipe,
    load_recipe,
)

from .assets import _sha256_file, import_asset
from .evidence import open_evidence_ledger
from .manifest import WorkspaceAsset, WorkspaceError, _identifier
if TYPE_CHECKING:
    from catalysis_workbench.visualization import FigurePresetBundle, FigureSpec

from .persistence import (
    _owned_path,
    _replace_manifest_atomically,
    _root_path,
    open_workspace,
)

__all__ = [
    "FigureComposition",
    "RecipeComposition",
    "WorkspaceComposition",
    "bind_recipe_assets",
    "create_workspace_composition",
    "figure_spec_sha256",
    "insert_recipe_step",
    "load_figure_spec_asset",
    "load_preset_bundle_asset",
    "load_recipe_asset",
    "move_recipe_step",
    "open_workspace_composition",
    "record_figure_export",
    "remove_recipe_step",
    "replace_recipe_step",
    "save_figure_spec_asset",
    "save_preset_bundle_asset",
    "save_recipe_asset",
    "save_workspace_composition",
]

_COMPOSITION_FILENAME = "workspace-composition.json"
_RECIPE_ASSET_TYPE = "workflow_recipe"
_FIGURE_SPEC_ASSET_TYPE = "figure_spec"
_PRESET_BUNDLE_ASSET_TYPE = "figure_preset_bundle"


def _identifiers(value: object, *, label: str) -> tuple[str, ...]:
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        raise WorkspaceError(f"{label} must be an ordered sequence")
    checked = tuple(_identifier(item, label=f"{label} item") for item in value)
    if len(set(checked)) != len(checked):
        raise WorkspaceError(f"{label} values must be unique")
    return checked


def _string_mapping(value: object, *, label: str) -> Mapping[str, str]:
    if not isinstance(value, Mapping):
        raise WorkspaceError(f"{label} must be a mapping")
    detached: dict[str, str] = {}
    for key, item in value.items():
        checked_key = _identifier(key, label=f"{label} key")
        checked_item = _identifier(item, label=f"{label}[{checked_key!r}]")
        detached[checked_key] = checked_item
    return MappingProxyType(detached)


def _sha256(value: object, *, label: str) -> str:
    if type(value) is not str or len(value) != 64:
        raise WorkspaceError(f"{label} must be a 64-character lowercase SHA-256")
    if value != value.lower() or any(ch not in "0123456789abcdef" for ch in value):
        raise WorkspaceError(f"{label} must be a 64-character lowercase SHA-256")
    return value


@dataclass(frozen=True, slots=True)
class RecipeComposition:
    """Explicit association between one recipe snapshot and workspace assets."""

    composition_id: str
    recipe_asset_id: str
    recipe_sha256: str
    input_assets: Mapping[str, str]
    output_assets: Mapping[str, str]
    composition_sha256: str = field(init=False)

    def __post_init__(self) -> None:
        composition_id = _identifier(self.composition_id, label="composition_id")
        recipe_asset_id = _identifier(self.recipe_asset_id, label="recipe_asset_id")
        recipe_sha256 = _sha256(self.recipe_sha256, label="recipe_sha256")
        input_assets = _string_mapping(self.input_assets, label="input_assets")
        output_assets = _string_mapping(self.output_assets, label="output_assets")
        digest = canonical_json_sha256(
            {
                "recipe_composition_schema_version": 1,
                "composition_id": composition_id,
                "recipe_asset_id": recipe_asset_id,
                "recipe_sha256": recipe_sha256,
                "input_assets": dict(input_assets),
                "output_assets": dict(output_assets),
            }
        )
        object.__setattr__(self, "composition_id", composition_id)
        object.__setattr__(self, "recipe_asset_id", recipe_asset_id)
        object.__setattr__(self, "recipe_sha256", recipe_sha256)
        object.__setattr__(self, "input_assets", input_assets)
        object.__setattr__(self, "output_assets", output_assets)
        object.__setattr__(self, "composition_sha256", digest)


@dataclass(frozen=True, slots=True)
class FigureComposition:
    """Exact association between presentation state, export bytes, and evidence."""

    composition_id: str
    figure_spec_asset_id: str
    figure_spec_sha256: str
    exported_figure_asset_id: str
    exported_figure_sha256: str
    preset_bundle_asset_id: str | None = None
    preset_bundle_sha256: str | None = None
    evidence_record_ids: Sequence[str] = ()
    composition_sha256: str = field(init=False)

    def __post_init__(self) -> None:
        composition_id = _identifier(self.composition_id, label="composition_id")
        figure_spec_asset_id = _identifier(
            self.figure_spec_asset_id, label="figure_spec_asset_id"
        )
        figure_spec_sha256 = _sha256(
            self.figure_spec_sha256, label="figure_spec_sha256"
        )
        exported_figure_asset_id = _identifier(
            self.exported_figure_asset_id, label="exported_figure_asset_id"
        )
        exported_figure_sha256 = _sha256(
            self.exported_figure_sha256, label="exported_figure_sha256"
        )

        preset_asset = self.preset_bundle_asset_id
        preset_digest = self.preset_bundle_sha256
        if (preset_asset is None) != (preset_digest is None):
            raise WorkspaceError(
                "preset_bundle_asset_id and preset_bundle_sha256 must be supplied together"
            )
        if preset_asset is not None:
            preset_asset = _identifier(preset_asset, label="preset_bundle_asset_id")
            preset_digest = _sha256(preset_digest, label="preset_bundle_sha256")

        evidence_record_ids = _identifiers(
            self.evidence_record_ids, label="evidence_record_ids"
        )
        digest = canonical_json_sha256(
            {
                "figure_composition_schema_version": 1,
                "composition_id": composition_id,
                "figure_spec_asset_id": figure_spec_asset_id,
                "figure_spec_sha256": figure_spec_sha256,
                "exported_figure_asset_id": exported_figure_asset_id,
                "exported_figure_sha256": exported_figure_sha256,
                "preset_bundle_asset_id": preset_asset,
                "preset_bundle_sha256": preset_digest,
                "evidence_record_ids": list(evidence_record_ids),
            }
        )
        object.__setattr__(self, "composition_id", composition_id)
        object.__setattr__(self, "figure_spec_asset_id", figure_spec_asset_id)
        object.__setattr__(self, "figure_spec_sha256", figure_spec_sha256)
        object.__setattr__(
            self, "exported_figure_asset_id", exported_figure_asset_id
        )
        object.__setattr__(
            self, "exported_figure_sha256", exported_figure_sha256
        )
        object.__setattr__(self, "preset_bundle_asset_id", preset_asset)
        object.__setattr__(self, "preset_bundle_sha256", preset_digest)
        object.__setattr__(self, "evidence_record_ids", evidence_record_ids)
        object.__setattr__(self, "composition_sha256", digest)


@dataclass(frozen=True, slots=True)
class WorkspaceComposition:
    """Ordered immutable workspace recipe/figure association state."""

    schema_version: int
    recipes: Sequence[RecipeComposition]
    figures: Sequence[FigureComposition]
    composition_sha256: str = field(init=False)

    def __post_init__(self) -> None:
        if type(self.schema_version) is not int or self.schema_version != 1:
            raise WorkspaceError(
                "workspace composition schema_version must be the integer 1"
            )
        if isinstance(self.recipes, (str, bytes)) or not isinstance(
            self.recipes, Sequence
        ):
            raise WorkspaceError("recipe compositions must be an ordered sequence")
        if isinstance(self.figures, (str, bytes)) or not isinstance(
            self.figures, Sequence
        ):
            raise WorkspaceError("figure compositions must be an ordered sequence")

        recipes = tuple(self.recipes)
        figures = tuple(self.figures)
        if any(not isinstance(item, RecipeComposition) for item in recipes):
            raise TypeError("recipes must contain RecipeComposition values")
        if any(not isinstance(item, FigureComposition) for item in figures):
            raise TypeError("figures must contain FigureComposition values")

        identifiers = tuple(item.composition_id for item in (*recipes, *figures))
        if len(set(identifiers)) != len(identifiers):
            raise WorkspaceError("workspace composition_id values must be unique")

        digest = canonical_json_sha256(
            {
                "workspace_composition_identity_schema_version": 1,
                "recipes": [
                    {
                        "composition_id": item.composition_id,
                        "composition_sha256": item.composition_sha256,
                    }
                    for item in recipes
                ],
                "figures": [
                    {
                        "composition_id": item.composition_id,
                        "composition_sha256": item.composition_sha256,
                    }
                    for item in figures
                ],
            }
        )
        object.__setattr__(self, "recipes", recipes)
        object.__setattr__(self, "figures", figures)
        object.__setattr__(self, "composition_sha256", digest)


_RECIPE_FIELDS = frozenset(
    {
        "composition_id",
        "recipe_asset_id",
        "recipe_sha256",
        "input_assets",
        "output_assets",
    }
)
_FIGURE_FIELDS = frozenset(
    {
        "composition_id",
        "figure_spec_asset_id",
        "figure_spec_sha256",
        "exported_figure_asset_id",
        "exported_figure_sha256",
        "preset_bundle_asset_id",
        "preset_bundle_sha256",
        "evidence_record_ids",
    }
)
_COMPOSITION_FIELDS = frozenset({"schema_version", "recipes", "figures"})


def _required_fields(
    value: Mapping[object, object], *, required: frozenset[str], label: str
) -> None:
    if not all(type(key) is str for key in value):
        raise WorkspaceError(f"{label} field names must be strings")
    fields = set(value)
    missing = sorted(required - fields)
    unknown = sorted(fields - required)
    if missing or unknown:
        raise WorkspaceError(
            f"invalid {label} fields; missing={missing!r}, unknown={unknown!r}"
        )


def _recipe_to_plain_dict(value: RecipeComposition) -> dict[str, object]:
    return {
        "composition_id": value.composition_id,
        "recipe_asset_id": value.recipe_asset_id,
        "recipe_sha256": value.recipe_sha256,
        "input_assets": dict(value.input_assets),
        "output_assets": dict(value.output_assets),
    }


def _figure_to_plain_dict(value: FigureComposition) -> dict[str, object]:
    return {
        "composition_id": value.composition_id,
        "figure_spec_asset_id": value.figure_spec_asset_id,
        "figure_spec_sha256": value.figure_spec_sha256,
        "exported_figure_asset_id": value.exported_figure_asset_id,
        "exported_figure_sha256": value.exported_figure_sha256,
        "preset_bundle_asset_id": value.preset_bundle_asset_id,
        "preset_bundle_sha256": value.preset_bundle_sha256,
        "evidence_record_ids": list(value.evidence_record_ids),
    }


def _composition_to_plain_dict(
    value: WorkspaceComposition,
) -> dict[str, object]:
    return {
        "schema_version": value.schema_version,
        "recipes": [_recipe_to_plain_dict(item) for item in value.recipes],
        "figures": [_figure_to_plain_dict(item) for item in value.figures],
    }


def _composition_from_dict(value: object) -> WorkspaceComposition:
    if not isinstance(value, Mapping):
        raise WorkspaceError("serialized workspace composition must be an object")
    _required_fields(
        value, required=_COMPOSITION_FIELDS, label="workspace composition"
    )
    recipes = value["recipes"]
    figures = value["figures"]
    if not isinstance(recipes, list):
        raise WorkspaceError("serialized recipe compositions must be a list")
    if not isinstance(figures, list):
        raise WorkspaceError("serialized figure compositions must be a list")

    parsed_recipes: list[RecipeComposition] = []
    for index, item in enumerate(recipes):
        if not isinstance(item, Mapping):
            raise WorkspaceError(
                f"serialized recipe composition {index} must be an object"
            )
        _required_fields(
            item,
            required=_RECIPE_FIELDS,
            label=f"recipe composition {index}",
        )
        parsed_recipes.append(
            RecipeComposition(
                composition_id=item["composition_id"],
                recipe_asset_id=item["recipe_asset_id"],
                recipe_sha256=item["recipe_sha256"],
                input_assets=item["input_assets"],
                output_assets=item["output_assets"],
            )
        )

    parsed_figures: list[FigureComposition] = []
    for index, item in enumerate(figures):
        if not isinstance(item, Mapping):
            raise WorkspaceError(
                f"serialized figure composition {index} must be an object"
            )
        _required_fields(
            item,
            required=_FIGURE_FIELDS,
            label=f"figure composition {index}",
        )
        parsed_figures.append(
            FigureComposition(
                composition_id=item["composition_id"],
                figure_spec_asset_id=item["figure_spec_asset_id"],
                figure_spec_sha256=item["figure_spec_sha256"],
                exported_figure_asset_id=item["exported_figure_asset_id"],
                exported_figure_sha256=item["exported_figure_sha256"],
                preset_bundle_asset_id=item["preset_bundle_asset_id"],
                preset_bundle_sha256=item["preset_bundle_sha256"],
                evidence_record_ids=item["evidence_record_ids"],
            )
        )

    return WorkspaceComposition(
        schema_version=value["schema_version"],
        recipes=parsed_recipes,
        figures=parsed_figures,
    )


def _payload(value: WorkspaceComposition) -> bytes:
    if not isinstance(value, WorkspaceComposition):
        raise TypeError("composition must be a WorkspaceComposition")
    try:
        return canonical_json_bytes(_composition_to_plain_dict(value)) + b"\n"
    except CanonicalJSONError as exc:
        raise WorkspaceError("workspace composition cannot be serialized") from exc


def _composition_path(root: Path) -> Path:
    return root / _COMPOSITION_FILENAME


def _asset_by_id(root: Path, asset_id: str) -> WorkspaceAsset:
    checked = _identifier(asset_id, label="asset_id")
    manifest = open_workspace(root)
    for asset in manifest.assets:
        if asset.asset_id == checked:
            return asset
    raise WorkspaceError(f"unknown workspace asset_id: {checked!r}")


def _verified_copy_asset(
    root: Path, asset_id: str, *, expected_type: str | None = None
) -> tuple[WorkspaceAsset, Path]:
    asset = _asset_by_id(root, asset_id)
    if asset.policy != "copy":
        raise WorkspaceError(f"asset {asset.asset_id!r} must be workspace-owned")
    if expected_type is not None and asset.asset_type != expected_type:
        raise WorkspaceError(
            f"asset {asset.asset_id!r} must have asset_type {expected_type!r}"
        )
    if asset.content_sha256 is None:
        raise WorkspaceError(f"asset {asset.asset_id!r} requires content_sha256")
    path = _owned_path(root, asset.path)
    if path.is_symlink():
        raise WorkspaceError(f"asset {asset.asset_id!r} must not be a symbolic link")
    if not path.exists():
        raise FileNotFoundError(path)
    if not path.is_file():
        raise WorkspaceError(f"asset {asset.asset_id!r} path must be a regular file")
    observed = _sha256_file(path)
    if observed != asset.content_sha256:
        raise WorkspaceError(
            f"asset {asset.asset_id!r} content digest does not match workspace catalog"
        )
    return asset, path


def _snapshot_asset(
    root: str | Path,
    *,
    asset_id: str,
    asset_type: str,
    destination: str,
    suffix: str,
    writer: Callable[[Path], None],
) -> WorkspaceAsset:
    root_path = _root_path(root, must_exist=True)
    with tempfile.TemporaryDirectory(prefix="catalysis-workbench-") as directory:
        temporary_path = Path(directory) / f"snapshot{suffix}"
        writer(temporary_path)
        manifest = import_asset(
            root_path,
            temporary_path,
            asset_id=asset_id,
            asset_type=asset_type,
            policy="copy",
            destination=destination,
        )
    return next(asset for asset in manifest.assets if asset.asset_id == asset_id)


def save_recipe_asset(
    root: str | Path,
    recipe: WorkflowRecipe,
    *,
    asset_id: str,
    destination: str,
) -> WorkspaceAsset:
    """Snapshot one reviewed recipe through the existing v0.9 serializer."""

    if not isinstance(recipe, WorkflowRecipe):
        raise TypeError("recipe must be a WorkflowRecipe")

    def writer(path: Path) -> None:
        dump_recipe(recipe, path)

    return _snapshot_asset(
        root,
        asset_id=asset_id,
        asset_type=_RECIPE_ASSET_TYPE,
        destination=destination,
        suffix=".json",
        writer=writer,
    )


def load_recipe_asset(root: str | Path, asset_id: str) -> WorkflowRecipe:
    """Load one workspace recipe snapshot through the reviewed v0.9 loader."""

    root_path = _root_path(root, must_exist=True)
    _asset, path = _verified_copy_asset(
        root_path, asset_id, expected_type=_RECIPE_ASSET_TYPE
    )
    return load_recipe(path)


def figure_spec_sha256(spec: FigureSpec) -> str:
    """Return deterministic identity for the existing FigureSpec persistence state."""

    from catalysis_workbench.visualization import FigureSpec

    if not isinstance(spec, FigureSpec):
        raise TypeError("spec must be a FigureSpec")
    return canonical_json_sha256(
        {"figure_spec_identity_schema_version": 1, "spec": spec.to_dict()}
    )


def save_figure_spec_asset(
    root: str | Path,
    spec: FigureSpec,
    *,
    asset_id: str,
    destination: str,
) -> WorkspaceAsset:
    """Snapshot validated FigureSpec state without rendering or mutating data."""

    from catalysis_workbench.visualization import FigureSpec

    if not isinstance(spec, FigureSpec):
        raise TypeError("spec must be a FigureSpec")

    def writer(path: Path) -> None:
        payload = canonical_json_bytes(
            {"schema_version": 1, "spec": spec.to_dict()}
        ) + b"\n"
        path.write_bytes(payload)

    return _snapshot_asset(
        root,
        asset_id=asset_id,
        asset_type=_FIGURE_SPEC_ASSET_TYPE,
        destination=destination,
        suffix=".json",
        writer=writer,
    )


def load_figure_spec_asset(root: str | Path, asset_id: str) -> FigureSpec:
    """Strictly load one FigureSpec snapshot and reject non-canonical state."""

    from catalysis_workbench.visualization import FigureSpec

    root_path = _root_path(root, must_exist=True)
    _asset, path = _verified_copy_asset(
        root_path, asset_id, expected_type=_FIGURE_SPEC_ASSET_TYPE
    )
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeError as exc:
        raise WorkspaceError("FigureSpec asset is not valid UTF-8") from exc
    try:
        value = loads_strict_json(text)
    except CanonicalJSONError as exc:
        raise WorkspaceError("cannot load FigureSpec asset") from exc
    if not isinstance(value, Mapping):
        raise WorkspaceError("serialized FigureSpec asset must be an object")
    _required_fields(
        value,
        required=frozenset({"schema_version", "spec"}),
        label="FigureSpec asset",
    )
    if value["schema_version"] != 1 or type(value["schema_version"]) is not int:
        raise WorkspaceError("FigureSpec asset schema_version must be the integer 1")
    state = value["spec"]
    if not isinstance(state, Mapping):
        raise WorkspaceError("serialized FigureSpec state must be an object")
    try:
        spec = FigureSpec.from_dict(state)
    except (TypeError, ValueError) as exc:
        raise WorkspaceError("invalid FigureSpec asset state") from exc
    try:
        canonical_state = canonical_json_bytes(spec.to_dict())
        serialized_state = canonical_json_bytes(state)
    except CanonicalJSONError as exc:
        raise WorkspaceError("FigureSpec asset state is not canonical JSON") from exc
    if canonical_state != serialized_state:
        raise WorkspaceError(
            "FigureSpec asset state must contain the complete reviewed persistence form"
        )
    return spec


def save_preset_bundle_asset(
    root: str | Path,
    bundle: FigurePresetBundle,
    *,
    asset_id: str,
    destination: str,
) -> WorkspaceAsset:
    """Snapshot one reviewed FigurePresetBundle through its existing serializer."""

    from catalysis_workbench.visualization import FigurePresetBundle, save_preset_bundle

    if not isinstance(bundle, FigurePresetBundle):
        raise TypeError("bundle must be a FigurePresetBundle")

    def writer(path: Path) -> None:
        save_preset_bundle(bundle, path)

    return _snapshot_asset(
        root,
        asset_id=asset_id,
        asset_type=_PRESET_BUNDLE_ASSET_TYPE,
        destination=destination,
        suffix=".json",
        writer=writer,
    )


def load_preset_bundle_asset(root: str | Path, asset_id: str) -> FigurePresetBundle:
    """Load one workspace preset-bundle snapshot through the reviewed loader."""

    from catalysis_workbench.visualization import load_preset_bundle

    root_path = _root_path(root, must_exist=True)
    _asset, path = _verified_copy_asset(
        root_path, asset_id, expected_type=_PRESET_BUNDLE_ASSET_TYPE
    )
    return load_preset_bundle(path)


def _validate_recipe_composition(root: Path, item: RecipeComposition) -> None:
    recipe = load_recipe_asset(root, item.recipe_asset_id)
    if recipe.recipe_sha256 != item.recipe_sha256:
        raise WorkspaceError(
            f"recipe composition {item.composition_id!r} recipe digest mismatch"
        )

    if set(item.input_assets) != set(recipe.inputs):
        raise WorkspaceError(
            f"recipe composition {item.composition_id!r} input bindings "
            "must exactly match recipe inputs"
        )
    if set(item.output_assets) != set(recipe.outputs):
        raise WorkspaceError(
            f"recipe composition {item.composition_id!r} output bindings "
            "must exactly match recipe outputs"
        )
    for asset_id in (*item.input_assets.values(), *item.output_assets.values()):
        _asset_by_id(root, asset_id)


def _evidence_ids(root: Path) -> set[str]:
    path = root / "workspace-evidence.json"
    if not path.exists() and not path.is_symlink():
        return set()
    ledger = open_evidence_ledger(root)
    return {record.record_id for record in ledger.records}


def _validate_figure_composition(root: Path, item: FigureComposition) -> None:
    spec = load_figure_spec_asset(root, item.figure_spec_asset_id)
    if figure_spec_sha256(spec) != item.figure_spec_sha256:
        raise WorkspaceError(
            f"figure composition {item.composition_id!r} FigureSpec digest mismatch"
        )

    export_asset, _export_path = _verified_copy_asset(
        root, item.exported_figure_asset_id
    )
    export_sha = export_asset.content_sha256
    if export_sha is None:
        raise WorkspaceError(
            f"figure composition {item.composition_id!r} export lacks content digest"
        )
    if export_sha != item.exported_figure_sha256:
        raise WorkspaceError(
            f"figure composition {item.composition_id!r} export digest mismatch"
        )

    if item.preset_bundle_asset_id is not None:
        bundle = load_preset_bundle_asset(root, item.preset_bundle_asset_id)
        if bundle.bundle_sha256 != item.preset_bundle_sha256:
            raise WorkspaceError(
                f"figure composition {item.composition_id!r} preset digest mismatch"
            )

    available_evidence = _evidence_ids(root)
    missing = sorted(set(item.evidence_record_ids) - available_evidence)
    if missing:
        raise WorkspaceError(
            f"figure composition {item.composition_id!r} references unknown "
            f"evidence records: {missing!r}"
        )


def _validate_composition(value: WorkspaceComposition, root: Path) -> None:
    open_workspace(root)
    for item in value.recipes:
        _validate_recipe_composition(root, item)
    for item in value.figures:
        _validate_figure_composition(root, item)


def create_workspace_composition(root: str | Path) -> WorkspaceComposition:
    """Create empty workspace composition metadata beside an existing workspace."""

    root_path = _root_path(root, must_exist=True)
    open_workspace(root_path)
    path = _composition_path(root_path)
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    value = WorkspaceComposition(schema_version=1, recipes=(), figures=())
    with path.open("xb") as stream:
        stream.write(_payload(value))
    return value


def save_workspace_composition(
    composition: WorkspaceComposition,
    root: str | Path,
    *,
    overwrite: bool = False,
) -> None:
    """Persist completely validated composition state."""

    if type(overwrite) is not bool:
        raise TypeError("overwrite must be a bool")
    payload = _payload(composition)
    root_path = _root_path(root, must_exist=True)
    _validate_composition(composition, root_path)
    path = _composition_path(root_path)
    if path.is_symlink():
        raise WorkspaceError("workspace composition metadata must not be a symbolic link")
    if overwrite:
        _replace_manifest_atomically(path, payload)
        return
    with path.open("xb") as stream:
        stream.write(payload)


def open_workspace_composition(root: str | Path) -> WorkspaceComposition:
    """Strictly load composition associations without execution or rendering."""

    root_path = _root_path(root, must_exist=True)
    open_workspace(root_path)
    path = _composition_path(root_path)
    if path.is_symlink():
        raise WorkspaceError("workspace composition metadata must not be a symbolic link")
    if not path.exists():
        raise FileNotFoundError(path)
    if not path.is_file():
        raise WorkspaceError("workspace composition path must be a regular file")
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeError as exc:
        raise WorkspaceError("workspace composition is not valid UTF-8") from exc
    try:
        state = loads_strict_json(text)
    except CanonicalJSONError as exc:
        raise WorkspaceError("cannot load workspace composition") from exc
    composition = _composition_from_dict(state)
    _validate_composition(composition, root_path)
    return composition


def _replace_or_append_recipe(
    composition: WorkspaceComposition, item: RecipeComposition
) -> WorkspaceComposition:
    existing = [
        entry
        for entry in composition.recipes
        if entry.composition_id == item.composition_id
    ]
    if existing:
        raise WorkspaceError(f"composition_id collision: {item.composition_id!r}")
    return WorkspaceComposition(
        schema_version=composition.schema_version,
        recipes=(*composition.recipes, item),
        figures=composition.figures,
    )


def _replace_or_append_figure(
    composition: WorkspaceComposition, item: FigureComposition
) -> WorkspaceComposition:
    if any(
        entry.composition_id == item.composition_id
        for entry in (*composition.recipes, *composition.figures)
    ):
        raise WorkspaceError(f"composition_id collision: {item.composition_id!r}")
    return WorkspaceComposition(
        schema_version=composition.schema_version,
        recipes=composition.recipes,
        figures=(*composition.figures, item),
    )


def bind_recipe_assets(
    root: str | Path,
    *,
    composition_id: str,
    recipe_asset_id: str,
    input_assets: Mapping[str, str],
    output_assets: Mapping[str, str],
) -> WorkspaceComposition:
    """Persist exact named asset bindings for one recipe snapshot."""

    root_path = _root_path(root, must_exist=True)
    composition = open_workspace_composition(root_path)
    recipe = load_recipe_asset(root_path, recipe_asset_id)

    if not isinstance(input_assets, Mapping):
        raise WorkspaceError("input_assets must be a mapping")
    if not isinstance(output_assets, Mapping):
        raise WorkspaceError("output_assets must be a mapping")
    if set(input_assets) != set(recipe.inputs):
        raise WorkspaceError("input_assets must exactly match recipe input names")
    if set(output_assets) != set(recipe.outputs):
        raise WorkspaceError("output_assets must exactly match recipe output names")

    ordered_inputs = {name: input_assets[name] for name in recipe.inputs}
    ordered_outputs = {name: output_assets[name] for name in recipe.outputs}
    item = RecipeComposition(
        composition_id=composition_id,
        recipe_asset_id=recipe_asset_id,
        recipe_sha256=recipe.recipe_sha256,
        input_assets=ordered_inputs,
        output_assets=ordered_outputs,
    )
    _validate_recipe_composition(root_path, item)
    updated = _replace_or_append_recipe(composition, item)
    save_workspace_composition(updated, root_path, overwrite=True)
    return updated


def record_figure_export(
    root: str | Path,
    *,
    composition_id: str,
    figure_spec_asset_id: str,
    exported_figure_asset_id: str,
    preset_bundle_asset_id: str | None = None,
    evidence_record_ids: Sequence[str] = (),
) -> WorkspaceComposition:
    """Persist exact figure presentation/export/evidence association state."""

    root_path = _root_path(root, must_exist=True)
    composition = open_workspace_composition(root_path)
    spec = load_figure_spec_asset(root_path, figure_spec_asset_id)
    export_asset, _export_path = _verified_copy_asset(
        root_path, exported_figure_asset_id
    )
    export_sha = export_asset.content_sha256
    if export_sha is None:
        raise WorkspaceError("exported figure asset requires content_sha256")

    preset_sha: str | None = None
    if preset_bundle_asset_id is not None:
        bundle = load_preset_bundle_asset(root_path, preset_bundle_asset_id)
        preset_sha = bundle.bundle_sha256

    item = FigureComposition(
        composition_id=composition_id,
        figure_spec_asset_id=figure_spec_asset_id,
        figure_spec_sha256=figure_spec_sha256(spec),
        exported_figure_asset_id=exported_figure_asset_id,
        exported_figure_sha256=export_sha,
        preset_bundle_asset_id=preset_bundle_asset_id,
        preset_bundle_sha256=preset_sha,
        evidence_record_ids=evidence_record_ids,
    )
    _validate_figure_composition(root_path, item)
    updated = _replace_or_append_figure(composition, item)
    save_workspace_composition(updated, root_path, overwrite=True)
    return updated


def _validated_recipe(recipe: WorkflowRecipe) -> WorkflowRecipe:
    if not isinstance(recipe, WorkflowRecipe):
        raise TypeError("recipe must be a WorkflowRecipe")
    return recipe


def _validated_step(step: RecipeStep) -> RecipeStep:
    if not isinstance(step, RecipeStep):
        raise TypeError("step must be a RecipeStep")
    return step


def _step_index(recipe: WorkflowRecipe, step_id: str) -> int:
    checked = _identifier(step_id, label="step_id")
    for index, step in enumerate(recipe.steps):
        if step.step_id == checked:
            return index
    raise WorkspaceError(f"unknown recipe step_id: {checked!r}")


def _recipe_with_steps(
    recipe: WorkflowRecipe, steps: Sequence[RecipeStep]
) -> WorkflowRecipe:
    return WorkflowRecipe(
        schema_version=recipe.schema_version,
        inputs=recipe.inputs,
        steps=steps,
        outputs=recipe.outputs,
    )


def insert_recipe_step(
    recipe: WorkflowRecipe, index: int, step: RecipeStep
) -> WorkflowRecipe:
    """Insert one explicit step at a literal position and validate as-is."""

    recipe = _validated_recipe(recipe)
    step = _validated_step(step)
    if type(index) is not int or index < 0 or index > len(recipe.steps):
        raise IndexError("recipe step insertion index out of range")
    steps = list(recipe.steps)
    steps.insert(index, step)
    return _recipe_with_steps(recipe, steps)


def replace_recipe_step(
    recipe: WorkflowRecipe, step_id: str, replacement: RecipeStep
) -> WorkflowRecipe:
    """Replace one explicit step in-place without discovering operations."""

    recipe = _validated_recipe(recipe)
    replacement = _validated_step(replacement)
    index = _step_index(recipe, step_id)
    steps = list(recipe.steps)
    steps[index] = replacement
    return _recipe_with_steps(recipe, steps)


def remove_recipe_step(recipe: WorkflowRecipe, step_id: str) -> WorkflowRecipe:
    """Remove one explicit step and fail if remaining bindings become invalid."""

    recipe = _validated_recipe(recipe)
    index = _step_index(recipe, step_id)
    steps = list(recipe.steps)
    del steps[index]
    return _recipe_with_steps(recipe, steps)


def move_recipe_step(
    recipe: WorkflowRecipe, step_id: str, new_index: int
) -> WorkflowRecipe:
    """Move one step literally; no dependency inference or topological repair occurs."""

    recipe = _validated_recipe(recipe)
    if type(new_index) is not int or new_index < 0 or new_index >= len(recipe.steps):
        raise IndexError("recipe step move index out of range")
    index = _step_index(recipe, step_id)
    steps = list(recipe.steps)
    step = steps.pop(index)
    steps.insert(new_index, step)
    return _recipe_with_steps(recipe, steps)
