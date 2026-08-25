from __future__ import annotations

import pytest

from catalysis_workbench.computation import (
    CorrelationDataset,
    CorrelationError,
    CorrelationExclusion,
    CorrelationPoint,
    ICOHPBondSummary,
    ICOHPResult,
    build_correlation_dataset,
    correlation_exclusions_frame,
    correlation_points_frame,
    icohp_length_correlation,
)


def _point(*, key: str = "p1", label: str | None = "display-1") -> CorrelationPoint:
    return CorrelationPoint(
        key=key,
        x_value=2.1,
        y_value=-1.5,
        x_source_key=f"{key}:distance",
        x_source_digest=f"x-digest-{key}",
        y_source_key=f"{key}:descriptor",
        y_source_digest=f"y-digest-{key}",
        mapping_key=f"map:{key}",
        mapping_provenance="caller-declared reviewed identity",
        metadata={"kind": "hand-fixture"},
        source_label=label,
    )


def test_generic_dataset_is_explicit_immutable_and_deterministic() -> None:
    first = _point()
    second = CorrelationPoint(
        key="p2",
        x_value=2.3,
        y_value=-0.7,
        x_source_key="p2:distance",
        x_source_digest="x-digest-p2",
        y_source_key="p2:descriptor",
        y_source_digest="y-digest-p2",
        mapping_key="map:p2",
        mapping_provenance="caller-declared reviewed identity",
        metadata={"kind": "hand-fixture"},
    )
    dataset = build_correlation_dataset(
        (first, second),
        x_definition="bond length",
        x_unit="angstrom",
        y_definition="bond descriptor",
        y_unit="eV",
        provenance_id="manual-map-v1",
    )
    reconstructed = build_correlation_dataset(
        (first, second),
        x_definition="bond length",
        x_unit="angstrom",
        y_definition="bond descriptor",
        y_unit="eV",
        provenance_id="manual-map-v1",
    )

    assert isinstance(dataset, CorrelationDataset)
    assert dataset.digest == reconstructed.digest
    assert dataset == reconstructed
    assert dataset.points == (first, second)
    with pytest.raises(TypeError):
        first.metadata["kind"] = "changed"


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("key", " "),
        ("x_value", float("nan")),
        ("y_value", float("inf")),
        ("x_source_key", ""),
        ("x_source_digest", ""),
        ("y_source_key", ""),
        ("y_source_digest", ""),
        ("mapping_key", ""),
        ("mapping_provenance", ""),
    ],
)
def test_point_invalid_required_state_fails(field: str, value: object) -> None:
    kwargs: dict[str, object] = {
        "key": "p",
        "x_value": 1.0,
        "y_value": 2.0,
        "x_source_key": "x",
        "x_source_digest": "xd",
        "y_source_key": "y",
        "y_source_digest": "yd",
        "mapping_key": "map",
        "mapping_provenance": "manual",
    }
    kwargs[field] = value
    with pytest.raises((CorrelationError, TypeError)):
        CorrelationPoint(**kwargs)  # type: ignore[arg-type]


def test_dataset_definitions_units_and_keys_fail_closed() -> None:
    point = _point()
    for field in ("x_definition", "x_unit", "y_definition", "y_unit", "provenance_id"):
        kwargs = {
            "x_definition": "x",
            "x_unit": "angstrom",
            "y_definition": "y",
            "y_unit": "eV",
            "provenance_id": "map-v1",
        }
        kwargs[field] = " "
        with pytest.raises(CorrelationError):
            CorrelationDataset(points=(point,), **kwargs)

    with pytest.raises(CorrelationError, match="unique"):
        build_correlation_dataset(
            (point, _point()),
            x_definition="x",
            x_unit="angstrom",
            y_definition="y",
            y_unit="eV",
            provenance_id="map-v1",
        )


def test_display_labels_do_not_change_scientific_digest() -> None:
    first = _point(label="first display")
    second = _point(label="second display")
    assert first.digest == second.digest
    assert first != second

    one = build_correlation_dataset(
        (first,),
        x_definition="x",
        x_unit="angstrom",
        y_definition="y",
        y_unit="eV",
        provenance_id="map-v1",
        source_label="dataset display A",
    )
    two = build_correlation_dataset(
        (second,),
        x_definition="x",
        x_unit="angstrom",
        y_definition="y",
        y_unit="eV",
        provenance_id="map-v1",
        source_label="dataset display B",
    )
    assert one.digest == two.digest
    assert one != two


def test_exclusions_are_explicit_and_separate_from_numeric_points() -> None:
    exclusion = CorrelationExclusion(
        key="excluded-1",
        mapping_key="map:excluded-1",
        reason="caller reports missing reviewed descriptor",
        x_source_key="geom:excluded-1",
        metadata={"decision": "manual exclusion"},
    )
    dataset = build_correlation_dataset(
        (_point(),),
        x_definition="x",
        x_unit="angstrom",
        y_definition="y",
        y_unit="eV",
        provenance_id="map-v1",
        exclusions=(exclusion,),
    )
    points = correlation_points_frame(dataset)
    excluded = correlation_exclusions_frame(dataset)
    assert len(points) == 1
    assert len(excluded) == 1
    assert "x_value" not in excluded.columns
    assert excluded.loc[0, "reason"] == "caller reports missing reviewed descriptor"

    with pytest.raises(CorrelationError, match="at least one"):
        CorrelationExclusion(key="bad", mapping_key="map", reason="missing both sources")


def test_frames_are_detached() -> None:
    dataset = build_correlation_dataset(
        (_point(),),
        x_definition="x",
        x_unit="angstrom",
        y_definition="y",
        y_unit="eV",
        provenance_id="map-v1",
    )
    frame = correlation_points_frame(dataset)
    frame.loc[0, "x_value"] = 99.0
    frame.loc[0, "metadata"] = {"changed": "yes"}
    assert dataset.points[0].x_value == pytest.approx(2.1)
    assert dict(dataset.points[0].metadata) == {"kind": "hand-fixture"}


def _nonspin_icohp() -> ICOHPResult:
    return ICOHPResult(
        bonds=(
            ICOHPBondSummary(
                bond_key="bond:1",
                source_label="1",
                bond_length_angstrom=2.0,
                number_of_bonds=2,
                icohp_by_spin={"total": -1.5},
            ),
            ICOHPBondSummary(
                bond_key="bond:2",
                source_label="2",
                bond_length_angstrom=2.4,
                number_of_bonds=1,
                icohp_by_spin={"total": -0.5},
            ),
        ),
        source_id="fixture",
    )


def _spin_icohp() -> ICOHPResult:
    return ICOHPResult(
        bonds=(
            ICOHPBondSummary(
                bond_key="bond:1",
                source_label="1",
                bond_length_angstrom=2.1,
                number_of_bonds=3,
                icohp_by_spin={"up": -1.2, "down": -0.8},
            ),
        ),
        source_id="spin-fixture",
    )


def test_icohp_length_correlation_total_is_hand_verifiable() -> None:
    source = _nonspin_icohp()
    dataset = icohp_length_correlation(
        source,
        spins=("total",),
        provenance_id="same-icohp-summary-v1",
    )
    assert dataset.x_definition == "LOBSTER ICOHP bond length"
    assert dataset.x_unit == "angstrom"
    assert dataset.y_definition == "source-sign ICOHP(E_F)"
    assert dataset.y_unit == "eV"
    assert [(p.x_value, p.y_value) for p in dataset.points] == [
        (2.0, -1.5),
        (2.4, -0.5),
    ]
    assert [p.metadata["number_of_bonds"] for p in dataset.points] == ["2", "1"]
    assert dataset.points[0].y_value == pytest.approx(-1.5)


def test_icohp_length_correlation_spin_sum_is_explicit_and_source_sign() -> None:
    source = _spin_icohp()
    dataset = icohp_length_correlation(
        source,
        spins=("up", "down"),
        provenance_id="explicit-spin-sum-v1",
    )
    point = dataset.points[0]
    assert point.x_value == pytest.approx(2.1)
    assert point.y_value == pytest.approx(-2.0)
    assert point.metadata["contributing_spins"] == "up,down"
    assert point.metadata["number_of_bonds"] == "3"
    assert point.metadata["source_result_digest"] == source.digest
    assert point.y_source_key.endswith("icohp_ef:up+down")


def test_icohp_length_correlation_single_spin_is_explicit() -> None:
    dataset = icohp_length_correlation(
        _spin_icohp(),
        spins=("up",),
        provenance_id="explicit-up-v1",
    )
    assert dataset.points[0].y_value == pytest.approx(-1.2)
    assert dataset.points[0].metadata["contributing_spins"] == "up"


@pytest.mark.parametrize("spins", [(), ("total",), ("up", "up"), ("bogus",)])
def test_icohp_length_correlation_invalid_spin_requests_fail(spins: tuple[str, ...]) -> None:
    with pytest.raises(CorrelationError):
        icohp_length_correlation(
            _spin_icohp(),
            spins=spins,
            provenance_id="invalid-request",
        )


def test_icohp_selector_preserves_source_order_and_empty_fails() -> None:
    source = _nonspin_icohp()
    selected = icohp_length_correlation(
        source,
        spins=("total",),
        provenance_id="selection-v1",
        bond_keys=("bond:2",),
    )
    assert [point.key for point in selected.points] == ["bond:2"]
    with pytest.raises(CorrelationError, match="matched no"):
        icohp_length_correlation(
            source,
            spins=("total",),
            provenance_id="selection-v1",
            bond_keys=("missing",),
        )
