"""Installed-wheel smoke for v0.7 Block-6 explicit NEB/barrier public API."""

from __future__ import annotations

import sys

import numpy as np

from catalysis_workbench.computation import (
    NEBImageState,
    build_neb_path,
    calculate_neb_barrier,
    neb_barrier_frame,
    neb_path_frame,
)
from catalysis_workbench.visualization import plot_neb_path


def _unexpected_backends() -> list[str]:
    return sorted(
        name
        for name in sys.modules
        if name == "ase"
        or name.startswith("ase.")
        or name == "pymatgen"
        or name.startswith("pymatgen.")
    )


def main() -> None:
    assert not _unexpected_backends(), _unexpected_backends()
    images = (
        NEBImageState("i0", -10.0, "e0", "explicit", "d0"),
        NEBImageState("i1", -9.5, "e1", "explicit", "d1"),
        NEBImageState("i2", -9.0, "e2", "explicit", "d2"),
        NEBImageState("i3", -9.6, "e3", "explicit", "d3"),
    )
    path = build_neb_path(
        images,
        key="installed-neb",
        reaction_coordinates=[0.0, 0.4, 1.2, 2.0],
        reference_image_key="i0",
    )
    assert path.image_keys == ("i0", "i1", "i2", "i3")
    assert np.array_equal(path.reaction_coordinates, np.array([0.0, 0.4, 1.2, 2.0]))
    assert np.allclose(
        path.plotted_energy_ev,
        np.array([0.0, 0.5, 1.0, 0.4]),
        rtol=0.0,
        atol=1e-12,
    )

    barrier = calculate_neb_barrier(
        path,
        initial_image_key="i0",
        saddle_image_key="i2",
        final_image_key="i3",
    )
    assert barrier.forward_barrier_ev == 1.0
    assert np.isclose(barrier.reverse_barrier_ev, 0.6, rtol=0.0, atol=1e-12)
    assert barrier.barrier_semantics == "discrete_retained_image"
    assert neb_path_frame(path).shape[0] == 4
    assert neb_barrier_frame(barrier).shape[0] == 1

    figure, ax = plot_neb_path(path, barrier=barrier)
    assert figure.axes == [ax]
    assert len(ax.lines) == 1
    assert len(ax.collections) == 1
    assert np.array_equal(ax.lines[0].get_xdata(), path.reaction_coordinates)
    assert np.array_equal(ax.lines[0].get_ydata(), path.plotted_energy_ev)
    assert not _unexpected_backends(), _unexpected_backends()
    print("installed v0.7 Block-6 explicit NEB/barrier smoke: ok")


if __name__ == "__main__":
    main()
