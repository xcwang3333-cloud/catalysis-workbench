from __future__ import annotations

import numpy as np
import pytest

from catalysis_workbench.computation.band_structure import (
    BandEnergyChannel,
    BandPathSegment,
    BandStructureState,
)
from catalysis_workbench.computation.projected_bands import (
    AggregatedBandProjection,
    BandProjectionChannel,
    BandProjectionError,
    BandProjectionState,
    aggregate_band_projection,
)
from catalysis_workbench.computation.structure import AtomicStructure
from catalysis_workbench.visualization.projected_bands import plot_fat_band


def _structure() -> AtomicStructure:
    return AtomicStructure(
        species=("H", "He"),
        elements=("H", "He"),
        cartesian_coordinates=((0.0, 0.0, 0.0), (1.0, 1.0, 1.0)),
        lattice_angstrom=np.diag([2.0, 2.0, 2.0]),
        pbc=(True, True, True),
        site_keys=("site-H", "site-He"),
    )


def _band_state(*, spin: str = "total") -> BandStructureState:
    kpoints = np.array(
        [
            [0.0, 0.0, 0.0],
            [0.5, 0.0, 0.0],
            [0.0, 0.5, 0.0],
            [0.0, 1.0, 0.0],
        ]
    )
    energies = np.array(
        [
            [4.0, 4.5, 5.0, 5.5],
            [6.0, 6.5, 7.0, 7.5],
        ]
    )
    if spin == "total":
        channels = (BandEnergyChannel("total", energies, (0, 1)),)
    else:
        channels = (
            BandEnergyChannel("up", energies, (0, 1)),
            BandEnergyChannel("down", energies + 0.2, (0, 1)),
        )
    return BandStructureState(
        structure=_structure(),
        kpoints_fractional=kpoints,
        reciprocal_lattice_cartesian=np.diag([2.0, 3.0, 4.0]),
        reciprocal_unit="1/angstrom",
        reciprocal_cartesian_includes_2pi=True,
        channels=channels,
        path_segments=(
            BandPathSegment("G-X", 0, 1, "G", "X"),
            BandPathSegment("M-Y", 2, 3, "M", "Y"),
        ),
        source_digest=f"band-source-{spin}",
        source_fermi_ev=5.0,
    )


def _projection_state() -> BandProjectionState:
    weights = (np.arange(2 * 4 * 2 * 3, dtype=float).reshape(2, 4, 2, 3) + 1.0) / 100.0
    return BandProjectionState(
        band_structure=_band_state(),
        orbitals=("s", "pz", "tot"),
        channels=(BandProjectionChannel("total", weights),),
        source_digest="procar-source",
        metadata={"producer": "synthetic"},
    )


def test_projection_state_preserves_exact_weights_and_source_identity() -> None:
    state = _projection_state()
    assert state.orbitals == ("s", "pz", "tot")
    assert state.site_keys == ("site-H", "site-He")
    assert state.elements == ("H", "He")
    assert state.channels[0].weights.shape == (2, 4, 2, 3)
    assert state.projection_unit == "dimensionless"
    assert state.projection_semantics == "vasp-procar-projection-weight"
    assert not state.channels[0].weights.flags.writeable
    with pytest.raises(ValueError):
        state.channels[0].weights[0, 0, 0, 0] = 9.0


def test_projection_state_rejects_negative_nonfinite_and_shape_mismatch() -> None:
    band = _band_state()
    bad = np.ones((2, 4, 2, 3))
    bad[0, 0, 0, 0] = -0.1
    with pytest.raises(BandProjectionError, match="non-negative"):
        BandProjectionChannel("total", bad)

    nonfinite = np.ones((2, 4, 2, 3))
    nonfinite[0, 0, 0, 0] = np.nan
    with pytest.raises(BandProjectionError, match="finite"):
        BandProjectionChannel("total", nonfinite)

    with pytest.raises(BandProjectionError, match="shape"):
        BandProjectionState(
            band_structure=band,
            orbitals=("s", "pz", "tot"),
            channels=(BandProjectionChannel("total", np.ones((2, 3, 2, 3))),),
            source_digest="bad-shape",
        )


def test_projection_state_requires_exact_band_spin_set() -> None:
    spin_band = _band_state(spin="spin")
    weights = np.ones((2, 4, 2, 3))
    with pytest.raises(BandProjectionError, match="spin set"):
        BandProjectionState(
            band_structure=spin_band,
            orbitals=("s", "pz", "tot"),
            channels=(BandProjectionChannel("up", weights),),
            source_digest="missing-down",
        )


def test_explicit_aggregation_is_exact_and_canonicalized_to_source_order() -> None:
    state = _projection_state()
    result = aggregate_band_projection(
        state,
        spin="total",
        site_indices=(1, 0),
        orbitals=("pz", "s"),
    )
    assert result.site_indices == (0, 1)
    assert result.site_keys == ("site-H", "site-He")
    assert result.elements == ("H", "He")
    assert result.orbitals == ("s", "pz")
    source = state.channel("total").weights
    expected = source[:, :, :, (0, 1)].sum(axis=(2, 3))
    assert np.allclose(result.weights, expected, rtol=0.0, atol=1e-15)
    assert np.max(result.weights) > 1.0
    assert result.aggregation == "sum"


def test_aggregated_state_rejects_noncanonical_or_spoofed_site_identity() -> None:
    state = _projection_state()
    base = dict(
        band_structure=state.band_structure,
        projection_state_digest=state.digest,
        projection_source_digest=state.source_digest,
        spin="total",
        orbitals=("s",),
        weights=np.ones((2, 4)),
    )
    with pytest.raises(BandProjectionError, match="source order"):
        AggregatedBandProjection(
            **base,
            site_indices=(1, 0),
            site_keys=("site-He", "site-H"),
            elements=("He", "H"),
        )
    with pytest.raises(BandProjectionError, match="associated structure sites"):
        AggregatedBandProjection(
            **base,
            site_indices=(0,),
            site_keys=("site-He",),
            elements=("He",),
        )


def test_aggregation_never_normalizes_or_sums_spin_implicitly() -> None:
    band = _band_state(spin="spin")
    up = np.full((2, 4, 2, 2), 0.3)
    down = np.full((2, 4, 2, 2), 0.7)
    state = BandProjectionState(
        band_structure=band,
        orbitals=("s", "tot"),
        channels=(
            BandProjectionChannel("up", up),
            BandProjectionChannel("down", down),
        ),
        source_digest="spin-procar",
    )
    result = aggregate_band_projection(
        state,
        spin="up",
        site_indices=(0, 1),
        orbitals=("s",),
    )
    assert np.array_equal(result.weights, np.full((2, 4), 0.6))
    assert not np.array_equal(result.weights, np.full((2, 4), 2.0))


def test_aggregation_rejects_empty_duplicate_and_unknown_selection() -> None:
    state = _projection_state()
    with pytest.raises(BandProjectionError, match="must not be empty"):
        aggregate_band_projection(state, spin="total", site_indices=(), orbitals=("s",))
    with pytest.raises(BandProjectionError, match="duplicates"):
        aggregate_band_projection(
            state,
            spin="total",
            site_indices=(0, 0),
            orbitals=("s",),
        )
    with pytest.raises(BandProjectionError, match="unknown source site"):
        aggregate_band_projection(
            state,
            spin="total",
            site_indices=(9,),
            orbitals=("s",),
        )
    with pytest.raises(BandProjectionError, match="duplicates"):
        aggregate_band_projection(
            state,
            spin="total",
            site_indices=(0,),
            orbitals=("s", "s"),
        )
    with pytest.raises(BandProjectionError, match="unknown source orbital"):
        aggregate_band_projection(
            state,
            spin="total",
            site_indices=(0,),
            orbitals=("dxy",),
        )


def test_fat_band_plot_is_segment_separated_and_presentation_scale_only() -> None:
    state = _projection_state()
    result = aggregate_band_projection(
        state,
        spin="total",
        site_indices=(0,),
        orbitals=("s",),
    )
    weights_before = np.array(result.weights, copy=True)
    digest_before = result.digest

    figure, ax = plot_fat_band(result, marker_area_scale=10.0)
    assert len(ax.lines) == 4
    assert len(ax.collections) == 4
    assert np.array_equal(ax.lines[0].get_xdata(), np.array([0.0, 1.0]))
    assert np.array_equal(ax.lines[2].get_xdata(), np.array([1.0, 2.5]))
    assert np.array_equal(ax.collections[0].get_sizes(), result.weights[0, :2] * 10.0)
    assert np.array_equal(result.weights, weights_before)
    assert result.digest == digest_before
    assert figure.axes == [ax]

    _, scaled_ax = plot_fat_band(result, marker_area_scale=20.0)
    assert np.array_equal(
        scaled_ax.collections[0].get_sizes(),
        result.weights[0, :2] * 20.0,
    )
    assert result.digest == digest_before


def test_zero_projection_weight_has_zero_marker_area() -> None:
    band = _band_state()
    state = BandProjectionState(
        band_structure=band,
        orbitals=("s",),
        channels=(BandProjectionChannel("total", np.zeros((2, 4, 2, 1))),),
        source_digest="zero-procar",
    )
    result = aggregate_band_projection(
        state,
        spin="total",
        site_indices=(0,),
        orbitals=("s",),
    )
    _, ax = plot_fat_band(result, marker_area_scale=100.0)
    assert np.array_equal(ax.collections[0].get_sizes(), np.array([0.0, 0.0]))
