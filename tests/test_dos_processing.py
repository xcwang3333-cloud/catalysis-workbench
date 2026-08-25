from __future__ import annotations

import sys

import numpy as np
import pytest

from catalysis_workbench.computation import (
    AtomicStructure,
    DOSChannel,
    DOSProjection,
    ElectronicDOS,
    ElectronicEnergyAxis,
)
from catalysis_workbench.computation.dos import (
    DOSProcessingError,
    DOSTrace,
    aggregate_dos,
    crop_dos_trace,
    dos_channel_trace,
    dos_trace_frame,
    reference_dos_to_fermi,
    select_dos_channels,
)
from catalysis_workbench.visualization.dos import DOSVisualizationError, plot_dos


def _dos() -> ElectronicDOS:
    structure = AtomicStructure(
        species=("Fe", "O"),
        elements=("Fe", "O"),
        cartesian_coordinates=((0.0, 0.0, 0.0), (1.0, 1.0, 1.0)),
        lattice_angstrom=((4.0, 0.0, 0.0), (0.0, 4.0, 0.0), (0.0, 0.0, 4.0)),
        pbc=(True, True, True),
        site_keys=("fe-0", "o-1"),
    )
    energy = ElectronicEnergyAxis(
        (-2.0, 0.0, 2.0, 4.0),
        reference_kind="source-native",
        source_fermi_ev=1.0,
    )
    channels = (
        DOSChannel(DOSProjection("total", "total"), "up", (1.0, 2.0, 3.0, 4.0)),
        DOSChannel(DOSProjection("total", "total"), "down", (0.5, 1.0, 1.5, 2.0)),
        DOSChannel(
            DOSProjection(
                "site:fe-0:dxy",
                "site-orbital",
                site_index=0,
                site_key="fe-0",
                element="Fe",
                orbital="dxy",
            ),
            "up",
            (0.2, 0.4, 0.8, 0.4),
            normalization_basis="site",
        ),
        DOSChannel(
            DOSProjection(
                "site:fe-0:dxz",
                "site-orbital",
                site_index=0,
                site_key="fe-0",
                element="Fe",
                orbital="dxz",
            ),
            "up",
            (0.1, 0.3, 0.5, 0.3),
            normalization_basis="site",
        ),
        DOSChannel(
            DOSProjection(
                "site:o-1:pz",
                "site-orbital",
                site_index=1,
                site_key="o-1",
                element="O",
                orbital="pz",
            ),
            "down",
            (0.3, 0.6, 0.9, 0.6),
            normalization_basis="site",
        ),
    )
    return ElectronicDOS(energy=energy, channels=channels, structure=structure)


def test_computation_dos_import_remains_matplotlib_lazy() -> None:
    assert "matplotlib.pyplot" not in sys.modules


def test_explicit_channel_selection_preserves_source_order() -> None:
    dos = _dos()
    total_up = select_dos_channels(dos, projection_kind="total", spins=("up",))
    assert [(item.projection.key, item.spin) for item in total_up] == [("total", "up")]

    fe_up = select_dos_channels(dos, elements=("Fe",), spins=("up",))
    assert [item.projection.orbital for item in fe_up] == ["dxy", "dxz"]

    exact = select_dos_channels(
        dos,
        site_keys=("o-1",),
        orbitals=("pz",),
        spins=("down",),
    )
    assert len(exact) == 1
    assert exact[0].projection.site_index == 1

    with pytest.raises(DOSProcessingError, match="matched no"):
        select_dos_channels(dos, elements=("Pt",))
    with pytest.raises(DOSProcessingError, match="must not be empty"):
        select_dos_channels(dos, orbitals=())


def test_single_channel_trace_is_immutable_and_deterministic() -> None:
    trace = dos_channel_trace(_dos(), projection_key="total", spin="up")
    assert trace.key == "total:up"
    assert trace.source_spins == ("up",)
    np.testing.assert_allclose(trace.density, [1.0, 2.0, 3.0, 4.0])
    assert trace.density.flags.writeable is False
    with pytest.raises(ValueError):
        trace.density.setflags(write=True)
    again = dos_channel_trace(_dos(), projection_key="total", spin="up")
    assert trace.digest == again.digest


def test_explicit_aggregation_is_hand_verifiable_and_fail_closed() -> None:
    dos = _dos()
    fe_channels = select_dos_channels(dos, elements=("Fe",), spins=("up",))
    trace = aggregate_dos(dos, fe_channels, key="fe-d-up", label="Fe d up")
    np.testing.assert_allclose(trace.density, [0.3, 0.7, 1.3, 0.7])
    assert trace.source_projection_keys == ("site:fe-0:dxy", "site:fe-0:dxz")
    assert trace.normalization_basis == "site"

    mixed = (dos.channels[0], dos.channels[2])
    with pytest.raises(DOSProcessingError, match="normalization"):
        aggregate_dos(dos, mixed, key="bad")
    with pytest.raises(DOSProcessingError, match="included twice"):
        aggregate_dos(dos, (dos.channels[2], dos.channels[2]), key="duplicate")


def test_fermi_reference_is_explicit_idempotent_and_crops_without_interpolation() -> None:
    source = dos_channel_trace(_dos(), projection_key="total", spin="up")
    referenced = reference_dos_to_fermi(source)
    assert referenced.energy.reference_kind == "fermi"
    assert referenced.energy.applied_shift_ev == pytest.approx(-1.0)
    np.testing.assert_allclose(referenced.energy.values_ev, [-3.0, -1.0, 1.0, 3.0])
    assert reference_dos_to_fermi(referenced) is referenced

    cropped = crop_dos_trace(referenced, -1.0, 2.0)
    np.testing.assert_allclose(cropped.energy.values_ev, [-1.0, 1.0])
    np.testing.assert_allclose(cropped.density, [2.0, 3.0])
    assert cropped.operations[-1].startswith("crop:")
    with pytest.raises(DOSProcessingError, match="at least two"):
        crop_dos_trace(referenced, 0.5, 1.5)


def test_fermi_reference_requires_retained_source_fermi() -> None:
    dos = _dos()
    trace = dos_channel_trace(dos, projection_key="total", spin="up")
    no_fermi = DOSTrace(
        key=trace.key,
        label=trace.label,
        energy=ElectronicEnergyAxis((-2.0, 0.0, 2.0, 4.0)),
        density=trace.density,
        source_dos_digest=trace.source_dos_digest,
        source_channel_digests=trace.source_channel_digests,
        source_projection_keys=trace.source_projection_keys,
        source_spins=trace.source_spins,
        density_unit=trace.density_unit,
        normalization_basis=trace.normalization_basis,
        operations=trace.operations,
    )
    with pytest.raises(DOSProcessingError, match="source_fermi"):
        reference_dos_to_fermi(no_fermi)


def test_detached_reporting_frame_retains_reference_and_provenance() -> None:
    trace = reference_dos_to_fermi(
        dos_channel_trace(_dos(), projection_key="total", spin="down")
    )
    frame = dos_trace_frame(trace)
    assert list(frame["energy_ev"]) == pytest.approx([-3.0, -1.0, 1.0, 3.0])
    assert set(frame["energy_reference"]) == {"fermi"}
    assert set(frame["source_spins"]) == {("down",)}
    frame.loc[0, "density"] = 999.0
    assert trace.density[0] == pytest.approx(0.5)


def test_passive_plot_mirrors_spin_down_only_in_rendered_copy() -> None:
    trace = reference_dos_to_fermi(
        dos_channel_trace(_dos(), projection_key="total", spin="down", label="down")
    )
    before = np.array(trace.density, copy=True)
    figure, ax = plot_dos(trace, mirror_spin_down=True, show_fermi=True)
    np.testing.assert_allclose(ax.lines[0].get_xdata(), [-3.0, -1.0, 1.0, 3.0])
    np.testing.assert_allclose(ax.lines[0].get_ydata(), -before)
    assert ax.lines[1].get_xdata()[0] == pytest.approx(0.0)
    np.testing.assert_array_equal(trace.density, before)
    figure.canvas.draw()


def test_plot_overlay_rejects_incompatible_reference_or_normalization() -> None:
    dos = _dos()
    native = dos_channel_trace(dos, projection_key="total", spin="up")
    fermi = reference_dos_to_fermi(
        dos_channel_trace(dos, projection_key="total", spin="down")
    )
    with pytest.raises(DOSVisualizationError, match="matching energy-reference"):
        plot_dos((native, fermi))

    site = aggregate_dos(
        dos,
        select_dos_channels(dos, elements=("Fe",), spins=("up",)),
        key="site",
    )
    with pytest.raises(DOSVisualizationError, match="normalization-basis"):
        plot_dos((native, site))


def test_source_native_fermi_marker_uses_retained_current_axis_position() -> None:
    trace = dos_channel_trace(_dos(), projection_key="total", spin="up")
    figure, ax = plot_dos(trace, show_fermi=True)
    assert ax.lines[1].get_xdata()[0] == pytest.approx(1.0)
    figure.canvas.draw()
