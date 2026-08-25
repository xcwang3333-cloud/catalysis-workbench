from __future__ import annotations

import numpy as np
import pytest

from catalysis_workbench.computation import (
    AtomicStructure,
    BandEnergyChannel,
    BandPathSegment,
    BandStructureError,
    BandStructureState,
    band_path_coordinates,
    reference_band_structure_to_fermi,
)
from catalysis_workbench.visualization import plot_band_structure


def _structure() -> AtomicStructure:
    return AtomicStructure(
        species=("H",),
        elements=("H",),
        cartesian_coordinates=((0.0, 0.0, 0.0),),
        lattice_angstrom=np.diag([2.0, 2.0, 2.0]),
        pbc=(True, True, True),
        site_keys=("site-H",),
    )


def _state(*, includes_2pi: bool = True) -> BandStructureState:
    kpoints = np.array(
        [
            [0.0, 0.0, 0.0],
            [0.5, 0.0, 0.0],
            [0.0, 0.5, 0.0],
            [0.0, 1.0, 0.0],
        ]
    )
    return BandStructureState(
        structure=_structure(),
        kpoints_fractional=kpoints,
        reciprocal_lattice_cartesian=np.diag([2.0, 3.0, 4.0]),
        reciprocal_unit="1/angstrom",
        reciprocal_cartesian_includes_2pi=includes_2pi,
        channels=(
            BandEnergyChannel(
                spin="total",
                energies_ev=np.array(
                    [
                        [4.0, 4.5, 5.0, 5.5],
                        [6.0, 6.5, 7.0, 7.5],
                    ]
                ),
                band_indices=(0, 1),
            ),
        ),
        path_segments=(
            BandPathSegment(
                key="G-X",
                start_index=0,
                end_index=1,
                start_label="G",
                end_label="X",
            ),
            BandPathSegment(
                key="M-Y",
                start_index=2,
                end_index=3,
                start_label="M",
                end_label="Y",
            ),
        ),
        source_digest="source-band",
        source_fermi_ev=5.0,
    )


def test_band_state_preserves_exact_source_order_and_is_immutable() -> None:
    state = _state()
    assert state.reference_kind == "source-native"
    assert state.applied_shift_ev == 0.0
    assert state.channels[0].spin == "total"
    assert state.channels[0].band_indices == (0, 1)
    assert [segment.key for segment in state.path_segments] == ["G-X", "M-Y"]
    assert not state.kpoints_fractional.flags.writeable
    assert not state.channels[0].energies_ev.flags.writeable
    with pytest.raises(ValueError):
        state.kpoints_fractional[0, 0] = 9.0


def test_path_distance_uses_full_retained_reciprocal_matrix_and_skips_jump() -> None:
    path = band_path_coordinates(_state())
    assert np.array_equal(path.segments[0].distances, np.array([0.0, 1.0]))
    assert np.array_equal(path.segments[1].distances, np.array([1.0, 2.5]))
    assert path.segments[1].distances[0] == path.segments[0].distances[-1]


def test_path_distance_never_inserts_or_removes_two_pi() -> None:
    with_two_pi = _state(includes_2pi=True)
    without_two_pi = _state(includes_2pi=False)
    first = band_path_coordinates(with_two_pi)
    second = band_path_coordinates(without_two_pi)
    for left, right in zip(first.segments, second.segments, strict=True):
        assert np.array_equal(left.distances, right.distances)
    assert first.reciprocal_cartesian_includes_2pi is True
    assert second.reciprocal_cartesian_includes_2pi is False
    assert first.digest != second.digest


def test_explicit_fermi_reference_is_exact_and_idempotent() -> None:
    state = _state()
    referenced = reference_band_structure_to_fermi(state)
    assert referenced.reference_kind == "fermi"
    assert referenced.applied_shift_ev == pytest.approx(-5.0)
    assert referenced.source_fermi_ev == pytest.approx(5.0)
    assert referenced.source_digest == state.source_digest
    assert np.array_equal(
        referenced.channels[0].energies_ev,
        state.channels[0].energies_ev - 5.0,
    )
    assert reference_band_structure_to_fermi(referenced) is referenced


def test_fermi_reference_requires_retained_source_fermi() -> None:
    state = _state()
    missing = BandStructureState(
        structure=state.structure,
        kpoints_fractional=state.kpoints_fractional,
        reciprocal_lattice_cartesian=state.reciprocal_lattice_cartesian,
        reciprocal_unit=state.reciprocal_unit,
        reciprocal_cartesian_includes_2pi=True,
        channels=state.channels,
        path_segments=state.path_segments,
        source_digest="missing-fermi",
        source_fermi_ev=None,
    )
    with pytest.raises(BandStructureError, match="source_fermi_ev"):
        reference_band_structure_to_fermi(missing)


def test_invalid_spin_shape_and_segment_state_fail_closed() -> None:
    with pytest.raises(BandStructureError, match="complete up/down pair"):
        BandStructureState(
            structure=_structure(),
            kpoints_fractional=np.zeros((2, 3)),
            reciprocal_lattice_cartesian=np.eye(3),
            reciprocal_unit="1/angstrom",
            reciprocal_cartesian_includes_2pi=True,
            channels=(
                BandEnergyChannel(
                    spin="up",
                    energies_ev=np.zeros((1, 2)),
                    band_indices=(0,),
                ),
            ),
            path_segments=(BandPathSegment("a", 0, 1),),
            source_digest="bad-spin",
        )

    with pytest.raises(BandStructureError, match="bounds exceed"):
        BandStructureState(
            structure=_structure(),
            kpoints_fractional=np.zeros((2, 3)),
            reciprocal_lattice_cartesian=np.eye(3),
            reciprocal_unit="1/angstrom",
            reciprocal_cartesian_includes_2pi=True,
            channels=(
                BandEnergyChannel(
                    spin="total",
                    energies_ev=np.zeros((1, 2)),
                    band_indices=(0,),
                ),
            ),
            path_segments=(BandPathSegment("a", 0, 2),),
            source_digest="bad-segment",
        )


def test_passive_plot_draws_each_band_segment_without_discontinuity_connector() -> None:
    state = _state()
    before = np.array(state.channels[0].energies_ev, copy=True)
    figure, ax = plot_band_structure(state)

    assert len(ax.lines) == 4
    assert np.array_equal(ax.lines[0].get_xdata(), np.array([0.0, 1.0]))
    assert np.array_equal(ax.lines[1].get_xdata(), np.array([0.0, 1.0]))
    assert np.array_equal(ax.lines[2].get_xdata(), np.array([1.0, 2.5]))
    assert np.array_equal(ax.lines[3].get_xdata(), np.array([1.0, 2.5]))
    assert [tick.get_text() for tick in ax.get_xticklabels()] == ["G", "X | M", "Y"]
    assert np.array_equal(state.channels[0].energies_ev, before)
    assert figure.axes == [ax]


def test_plot_fermi_marker_uses_current_explicit_reference() -> None:
    source = _state()
    _, source_ax = plot_band_structure(source, show_fermi=True)
    assert np.array_equal(source_ax.lines[-1].get_ydata(), np.array([5.0, 5.0]))

    referenced = reference_band_structure_to_fermi(source)
    _, referenced_ax = plot_band_structure(referenced, show_fermi=True)
    assert np.array_equal(referenced_ax.lines[-1].get_ydata(), np.array([0.0, 0.0]))
