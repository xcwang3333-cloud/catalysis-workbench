from __future__ import annotations

import ast
from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

import catalysis_workbench.visualization.presets as preset_registry
from catalysis_workbench._canonical_json import canonical_json_bytes
from catalysis_workbench.visualization import (
    FigurePresetBundle,
    FigurePresetEntry,
    FigureSpec,
    PlotStyle,
    VisualizationError,
    get_preset,
    install_preset_bundle,
    list_presets,
    load_preset_bundle,
    save_preset_bundle,
)


def _entry(name: str = "paper", *, title: str | None = None) -> FigurePresetEntry:
    return FigurePresetEntry(name=name, spec=FigureSpec(title=title))


def _bundle(
    entries: tuple[FigurePresetEntry, ...] | None = None,
) -> FigurePresetBundle:
    selected = (_entry(),) if entries is None else entries
    return FigurePresetBundle(schema_version=1, entries=selected)


def _serialized(bundle: FigurePresetBundle) -> dict[str, object]:
    return {
        "schema_version": bundle.schema_version,
        "entries": [
            {"name": entry.name, "spec": entry.spec.to_dict()}
            for entry in bundle.entries
        ],
    }


def _isolated_registry(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        preset_registry,
        "_PRESETS",
        {
            "publication": FigureSpec(title="publication"),
            "existing": FigureSpec(title="existing"),
        },
    )


def test_bundle_models_are_frozen_and_detached_from_entry_sequence() -> None:
    entry = _entry()
    entries = [entry]
    bundle = FigurePresetBundle(schema_version=1, entries=entries)
    entries.clear()

    assert bundle.entries == (entry,)
    with pytest.raises(FrozenInstanceError):
        entry.name = "changed"  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        bundle.entries = ()  # type: ignore[misc]


@pytest.mark.parametrize("schema_version", [True, 0, -1, 2, "1"])
def test_bundle_rejects_unknown_schema_version(schema_version: object) -> None:
    with pytest.raises(VisualizationError, match="integer 1"):
        FigurePresetBundle(schema_version=schema_version, entries=(_entry(),))


@pytest.mark.parametrize("entries", [(), [], "paper", b"paper", {"paper"}])
def test_bundle_requires_nonempty_ordered_entries(entries: object) -> None:
    with pytest.raises((TypeError, VisualizationError)):
        FigurePresetBundle(schema_version=1, entries=entries)  # type: ignore[arg-type]


def test_bundle_rejects_duplicate_entry_names() -> None:
    with pytest.raises(VisualizationError, match="unique"):
        _bundle((_entry("paper"), _entry("paper", title="second")))


@pytest.mark.parametrize(
    "name",
    [
        "",
        " paper",
        "paper ",
        "Paper",
        "PAPER",
        "\ud800",
    ],
)
def test_entry_name_must_be_explicit_canonical_registry_key(name: str) -> None:
    with pytest.raises(VisualizationError):
        _entry(name)


def test_entry_requires_figure_spec() -> None:
    with pytest.raises(TypeError, match="FigureSpec"):
        FigurePresetEntry(name="paper", spec=object())  # type: ignore[arg-type]


def test_bundle_digest_is_deterministic_and_sensitive_to_entry_order() -> None:
    first = _entry("first", title="First")
    second = FigurePresetEntry(
        name="second",
        spec=FigureSpec(
            title="Second",
            style=PlotStyle(font_size=9.0, line_width=1.5),
        ),
    )
    left = _bundle((first, second))
    repeated = _bundle((first, second))
    reversed_bundle = _bundle((second, first))

    assert left.bundle_sha256 == repeated.bundle_sha256
    assert len(left.bundle_sha256) == 64
    assert left.bundle_sha256 != reversed_bundle.bundle_sha256


def test_save_and_load_round_trip_uses_canonical_json(tmp_path: Path) -> None:
    bundle = _bundle(
        (
            _entry("first", title="催化"),
            _entry("second", title="Comparison"),
        )
    )
    path = tmp_path / "presets.json"
    save_preset_bundle(bundle, path)

    expected = _serialized(bundle)
    assert path.read_bytes() == canonical_json_bytes(expected) + b"\n"
    restored = load_preset_bundle(path)
    assert restored.bundle_sha256 == bundle.bundle_sha256
    assert tuple(entry.name for entry in restored.entries) == ("first", "second")
    assert tuple(entry.spec.to_dict() for entry in restored.entries) == tuple(
        entry.spec.to_dict() for entry in bundle.entries
    )


def test_save_refuses_overwrite_by_default_and_allows_explicit_overwrite(
    tmp_path: Path,
) -> None:
    path = tmp_path / "presets.json"
    original = _bundle((_entry("first"),))
    changed = _bundle((_entry("second"),))
    save_preset_bundle(original, path)

    with pytest.raises(FileExistsError):
        save_preset_bundle(changed, path)

    save_preset_bundle(changed, path, overwrite=True)
    assert load_preset_bundle(path).bundle_sha256 == changed.bundle_sha256


@pytest.mark.parametrize("overwrite", [1, None, "yes"])
def test_save_and_install_require_boolean_overwrite(
    tmp_path: Path,
    overwrite: object,
) -> None:
    bundle = _bundle()
    with pytest.raises(TypeError, match="bool"):
        save_preset_bundle(
            bundle,
            tmp_path / "presets.json",
            overwrite=overwrite,  # type: ignore[arg-type]
        )
    with pytest.raises(TypeError, match="bool"):
        install_preset_bundle(bundle, overwrite=overwrite)  # type: ignore[arg-type]


def test_load_rejects_duplicate_json_keys(tmp_path: Path) -> None:
    path = tmp_path / "presets.json"
    path.write_text(
        '{"schema_version":1,"schema_version":1,"entries":[]}',
        encoding="utf-8",
    )
    with pytest.raises(VisualizationError, match="cannot load preset bundle"):
        load_preset_bundle(path)


@pytest.mark.parametrize("field", ["metadata", "digest"])
def test_load_rejects_unknown_bundle_fields(tmp_path: Path, field: str) -> None:
    value = _serialized(_bundle())
    value[field] = "unexpected"
    path = tmp_path / "presets.json"
    path.write_bytes(canonical_json_bytes(value))
    with pytest.raises(VisualizationError, match="unknown"):
        load_preset_bundle(path)


def test_load_rejects_missing_bundle_field(tmp_path: Path) -> None:
    value = _serialized(_bundle())
    del value["entries"]
    path = tmp_path / "presets.json"
    path.write_bytes(canonical_json_bytes(value))
    with pytest.raises(VisualizationError, match="missing"):
        load_preset_bundle(path)


def test_load_rejects_unknown_or_missing_entry_fields(tmp_path: Path) -> None:
    unknown = _serialized(_bundle())
    unknown_entries = unknown["entries"]
    assert isinstance(unknown_entries, list)
    unknown_entry = unknown_entries[0]
    assert isinstance(unknown_entry, dict)
    unknown_entry["callable"] = "forbidden"

    missing = _serialized(_bundle())
    missing_entries = missing["entries"]
    assert isinstance(missing_entries, list)
    missing_entry = missing_entries[0]
    assert isinstance(missing_entry, dict)
    del missing_entry["spec"]

    for index, value in enumerate((unknown, missing)):
        path = tmp_path / f"invalid-{index}.json"
        path.write_bytes(canonical_json_bytes(value))
        with pytest.raises(VisualizationError):
            load_preset_bundle(path)


def test_load_rejects_invalid_figure_spec(tmp_path: Path) -> None:
    value = _serialized(_bundle())
    entries = value["entries"]
    assert isinstance(entries, list)
    entry = entries[0]
    assert isinstance(entry, dict)
    spec = entry["spec"]
    assert isinstance(spec, dict)
    spec["layout"] = {"figure_width_in": -1.0}

    path = tmp_path / "presets.json"
    path.write_bytes(canonical_json_bytes(value))
    with pytest.raises(VisualizationError, match="invalid FigureSpec"):
        load_preset_bundle(path)


def test_file_path_does_not_affect_bundle_digest(tmp_path: Path) -> None:
    bundle = _bundle()
    first = tmp_path / "first.json"
    second = tmp_path / "nested" / "second.json"
    second.parent.mkdir()
    save_preset_bundle(bundle, first)
    save_preset_bundle(bundle, second)
    assert load_preset_bundle(first).bundle_sha256 == load_preset_bundle(
        second
    ).bundle_sha256


def test_install_preserves_literal_bundle_order_for_new_presets(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _isolated_registry(monkeypatch)
    bundle = _bundle((_entry("first"), _entry("second")))
    install_preset_bundle(bundle)

    assert list_presets() == ("publication", "existing", "first", "second")
    assert get_preset("first").to_dict() == bundle.entries[0].spec.to_dict()
    assert get_preset("second").to_dict() == bundle.entries[1].spec.to_dict()


def test_install_conflict_has_zero_partial_registry_mutation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _isolated_registry(monkeypatch)
    before_names = list_presets()
    before = {name: get_preset(name) for name in before_names}
    bundle = _bundle((_entry("new"), _entry("existing", title="replacement")))

    with pytest.raises(VisualizationError, match="already registered"):
        install_preset_bundle(bundle)

    assert list_presets() == before_names
    assert {name: get_preset(name) for name in before_names} == before
    with pytest.raises(VisualizationError, match="unknown visualization preset"):
        get_preset("new")


def test_install_overwrite_is_atomic_and_preserves_existing_key_position(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _isolated_registry(monkeypatch)
    replacement = _entry("existing", title="replacement")
    added = _entry("new", title="new")
    install_preset_bundle(_bundle((replacement, added)), overwrite=True)

    assert list_presets() == ("publication", "existing", "new")
    assert get_preset("existing").title == "replacement"
    assert get_preset("new").title == "new"


def test_bundle_source_does_not_execute_dynamic_configuration() -> None:
    source = (
        Path(__file__).parents[1]
        / "src"
        / "catalysis_workbench"
        / "visualization"
        / "preset_bundles.py"
    )
    tree = ast.parse(source.read_text(encoding="utf-8"))
    imported_roots: set[str] = set()
    called_names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_roots.update(alias.name.split(".", 1)[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported_roots.add(node.module.split(".", 1)[0])
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            called_names.add(node.func.id)

    assert "importlib" not in imported_roots
    assert {"eval", "exec", "__import__"}.isdisjoint(called_names)
