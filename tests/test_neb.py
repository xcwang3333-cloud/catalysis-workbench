from __future__ import annotations

import numpy as np
import pytest

from catalysis_workbench.computation import (
    AtomicStructure,
    NEBBarrierResult,
    NEBError,
    NEBImageState,
    NEBPath,
    build_neb_path,
    calculate_neb_barrier,
    neb_barrier_frame,
    neb_path_frame,
    validate_neb_barrier_path,
)
from catalysis_workbench.visualization import (
    FigureSpec,
    NEBVisualizationError,
    plot_neb_path,
)


def _structure() -> AtomicStructure:
    return AtomicStructure(
        species=("H",),
        elements=("H",),
        cartesian_coordinates=((0.0, 0.0, 0.0),),
        lattice_angstrom=np.eye(3) * 5.0,
        pbc=(True, True, True),
        site_keys=("site-H",),
    )


def _image(key: str, energy: float, *, label: str | None = None) -> NEBImageState:
    return NEBImageState(
        key=key,
        energy_ev=energy,
        source_key=f"energy:{key}",
        source_type="vasp-energy",
        source_digest=f"digest-{key}",
        label=label,
    )


def _images() -> tuple[NEBImageState, ...]:
    return (
        _image("i0", -10.0, label="Initial"),
        _image("i1", -9.4),
        _image("i2", -9.0, label="Saddle candidate"),
        _image("i3", -9.6, label="Final"),
    )


def test_image_state_retains_exact_energy_provenance_and_optional_structure() -> None:
    structure = _structure()
    image = NEBImageState(
        key="image-01",
        energy_ev=-12.345,
        source_key="OUTCAR:01",
        source_type="external-neb-energy",
        source_digest="source-01",
        structure=structure,
        label="image one",
    )
    assert image.energy_ev == -12.345
    assert image.structure is structure
    assert image.structure_digest == structure.digest
    assert len(image.digest) == 64

    relabeled = NEBImageState(
        key="image-01",
        energy_ev=-12.345,
        source_key="OUTCAR:01",
        source_type="external-neb-energy",
        source_digest="source-01",
        structure=structure,
        label="presentation-only relabel",
    )
    assert relabeled.digest == image.digest
    assert relabeled != image


@pytest.mark.parametrize(
    "kwargs",
    [
        {
            "key": " ",
            "energy_ev": 0.0,
            "source_key": "s",
            "source_type": "t",
            "source_digest": "d",
        },
        {
            "key": "i",
            "energy_ev": np.nan,
            "source_key": "s",
            "source_type": "t",
            "source_digest": "d",
        },
        {
            "key": "i",
            "energy_ev": 0.0,
            "source_key": " ",
            "source_type": "t",
            "source_digest": "d",
        },
        {
            "key": "i",
            "energy_ev": 0.0,
            "source_key": "s",
            "source_type": " ",
            "source_digest": "d",
        },
        {
            "key": "i",
            "energy_ev": 0.0,
            "source_key": "s",
            "source_type": "t",
            "source_digest": " ",
        },
    ],
)
def test_image_state_rejects_ambiguous_or_nonfinite_input(kwargs: dict[str, object]) -> None:
    with pytest.raises((NEBError, TypeError)):
        NEBImageState(**kwargs)


def test_image_state_rejects_non_atomic_structure_attachment() -> None:
    with pytest.raises(TypeError, match="AtomicStructure"):
        NEBImageState(
            key="i0",
            energy_ev=0.0,
            source_key="s",
            source_type="t",
            source_digest="d",
            structure=object(),  # type: ignore[arg-type]
        )


def test_ordinal_path_preserves_source_order_and_absolute_energies() -> None:
    images = _images()
    path = build_neb_path(images, key="neb-path")
    assert path.images == images
    assert path.image_keys == ("i0", "i1", "i2", "i3")
    assert path.reaction_coordinate_mode == "ordinal"
    assert np.array_equal(path.reaction_coordinates, np.array([0.0, 1.0, 2.0, 3.0]))
    assert path.energy_mode == "absolute"
    assert path.reference_image_key is None
    assert np.array_equal(
        path.plotted_energy_ev,
        np.array([image.energy_ev for image in images]),
    )
    assert not path.reaction_coordinates.flags.writeable
    assert not path.plotted_energy_ev.flags.writeable


def test_explicit_reaction_coordinates_are_retained_literally_without_sorting() -> None:
    coordinates = np.array([0.0, 0.75, 0.4, 2.2])
    path = build_neb_path(
        _images(),
        key="explicit-path",
        reaction_coordinates=coordinates,
    )
    assert path.reaction_coordinate_mode == "explicit"
    assert np.array_equal(path.reaction_coordinates, coordinates)
    assert path.image_keys == ("i0", "i1", "i2", "i3")


@pytest.mark.parametrize(
    "coordinates",
    [
        [0.0, 1.0],
        [0.0, 1.0, np.inf, 3.0],
    ],
)
def test_explicit_reaction_coordinates_fail_closed_on_invalid_shape_or_values(
    coordinates: list[float],
) -> None:
    with pytest.raises(NEBError):
        build_neb_path(
            _images(),
            key="bad-coordinates",
            reaction_coordinates=coordinates,
        )


def test_reference_relative_path_requires_explicit_retained_reference() -> None:
    images = _images()
    path = build_neb_path(
        images,
        key="relative-path",
        reference_image_key="i1",
    )
    absolute = np.array([image.energy_ev for image in images])
    expected = absolute - images[1].energy_ev
    assert path.energy_mode == "reference_relative"
    assert path.reference_image_key == "i1"
    assert np.array_equal(path.plotted_energy_ev, expected)

    with pytest.raises(NEBError, match="reference_image_key"):
        build_neb_path(
            images,
            key="bad-reference",
            reference_image_key="missing",
        )


def test_direct_path_construction_rejects_hidden_zeroing_or_fake_relative_state() -> None:
    images = _images()
    with pytest.raises(NEBError, match="plotted_energy_ev"):
        NEBPath(
            key="fake-absolute",
            images=images,
            reaction_coordinate_mode="ordinal",
            reaction_coordinates=[0.0, 1.0, 2.0, 3.0],
            energy_mode="absolute",
            plotted_energy_ev=[0.0, 0.6, 1.0, 0.4],
        )
    with pytest.raises(NEBError, match="reference_image_key"):
        NEBPath(
            key="missing-reference",
            images=images,
            reaction_coordinate_mode="ordinal",
            reaction_coordinates=[0.0, 1.0, 2.0, 3.0],
            energy_mode="reference_relative",
            plotted_energy_ev=[0.0, 0.6, 1.0, 0.4],
        )


def test_path_rejects_duplicate_image_keys_and_fake_ordinal_coordinates() -> None:
    duplicate = (_image("same", 0.0), _image("same", 1.0))
    with pytest.raises(NEBError, match="unique"):
        build_neb_path(duplicate, key="duplicate")

    images = _images()
    absolute = [image.energy_ev for image in images]
    with pytest.raises(NEBError, match="ordinal reaction coordinates"):
        NEBPath(
            key="fake-ordinal",
            images=images,
            reaction_coordinate_mode="ordinal",
            reaction_coordinates=[0.0, 2.0, 1.0, 3.0],
            energy_mode="absolute",
            plotted_energy_ev=absolute,
        )


def test_discrete_barrier_uses_explicit_three_image_keys_and_absolute_energies() -> None:
    path = build_neb_path(
        _images(),
        key="relative-path",
        reference_image_key="i1",
    )
    result = calculate_neb_barrier(
        path,
        initial_image_key="i0",
        saddle_image_key="i2",
        final_image_key="i3",
    )
    assert result.initial_image_index == 0
    assert result.saddle_image_index == 2
    assert result.final_image_index == 3
    assert result.initial_energy_ev == -10.0
    assert result.saddle_energy_ev == -9.0
    assert result.final_energy_ev == -9.6
    assert result.forward_barrier_ev == pytest.approx(1.0)
    assert result.reverse_barrier_ev == pytest.approx(0.6)
    assert result.barrier_semantics == "discrete_retained_image"
    assert validate_neb_barrier_path(path, result) is result


def test_negative_discrete_barrier_arithmetic_is_retained_not_clipped() -> None:
    path = build_neb_path(
        (_image("a", 0.0), _image("s", -1.0), _image("b", 0.5)),
        key="negative-barrier",
    )
    result = calculate_neb_barrier(
        path,
        initial_image_key="a",
        saddle_image_key="s",
        final_image_key="b",
    )
    assert result.forward_barrier_ev == -1.0
    assert result.reverse_barrier_ev == -1.5


@pytest.mark.parametrize(
    ("initial", "saddle", "final", "pattern"),
    [
        ("i0", "i0", "i3", "distinct"),
        ("missing", "i2", "i3", "not retained"),
        ("i2", "i1", "i3", "initial before saddle before final"),
        ("i0", "i3", "i2", "initial before saddle before final"),
    ],
)
def test_barrier_selection_fails_closed(
    initial: str,
    saddle: str,
    final: str,
    pattern: str,
) -> None:
    path = build_neb_path(_images(), key="path")
    with pytest.raises(NEBError, match=pattern):
        calculate_neb_barrier(
            path,
            initial_image_key=initial,
            saddle_image_key=saddle,
            final_image_key=final,
        )


def test_direct_barrier_result_rejects_wrong_arithmetic_and_semantics() -> None:
    path = build_neb_path(_images(), key="path")
    initial, saddle, final = path.images[0], path.images[2], path.images[3]
    common = dict(
        path_digest=path.digest,
        initial_image_key=initial.key,
        saddle_image_key=saddle.key,
        final_image_key=final.key,
        initial_image_index=0,
        saddle_image_index=2,
        final_image_index=3,
        initial_image_digest=initial.digest,
        saddle_image_digest=saddle.digest,
        final_image_digest=final.digest,
        initial_energy_ev=initial.energy_ev,
        saddle_energy_ev=saddle.energy_ev,
        final_energy_ev=final.energy_ev,
        forward_barrier_ev=1.0,
        reverse_barrier_ev=0.6,
    )
    with pytest.raises(NEBError, match="E_saddle - E_initial"):
        NEBBarrierResult(**{**common, "forward_barrier_ev": 2.0})
    with pytest.raises(NEBError, match="barrier_semantics"):
        NEBBarrierResult(**{**common, "barrier_semantics": "continuous-spline-ts"})


def test_reporting_is_detached_and_preserves_retained_semantics() -> None:
    path = build_neb_path(
        _images(),
        key="reported",
        reaction_coordinates=[0.0, 0.4, 1.1, 2.0],
        reference_image_key="i0",
    )
    barrier = calculate_neb_barrier(
        path,
        initial_image_key="i0",
        saddle_image_key="i2",
        final_image_key="i3",
    )
    frame = neb_path_frame(path)
    assert frame["image_key"].tolist() == ["i0", "i1", "i2", "i3"]
    assert frame["reaction_coordinate"].tolist() == [0.0, 0.4, 1.1, 2.0]
    assert frame["energy_mode"].unique().tolist() == ["reference_relative"]
    frame.loc[0, "absolute_energy_ev"] = 123.0
    assert path.images[0].energy_ev == -10.0

    barrier_frame = neb_barrier_frame(barrier)
    assert barrier_frame.loc[0, "barrier_semantics"] == "discrete_retained_image"
    assert barrier_frame.loc[0, "forward_barrier_ev"] == pytest.approx(1.0)


def test_passive_plot_uses_exact_points_straight_segments_and_explicit_saddle_only() -> None:
    path = build_neb_path(
        _images(),
        key="plotted",
        reaction_coordinates=[0.0, 0.5, 1.4, 2.0],
        reference_image_key="i0",
    )
    barrier = calculate_neb_barrier(
        path,
        initial_image_key="i0",
        saddle_image_key="i2",
        final_image_key="i3",
    )
    x_before = np.array(path.reaction_coordinates, copy=True)
    y_before = np.array(path.plotted_energy_ev, copy=True)
    digest_before = path.digest

    figure, ax = plot_neb_path(path, barrier=barrier)
    assert figure.axes == [ax]
    assert len(ax.lines) == 1
    assert len(ax.collections) == 1
    assert np.array_equal(ax.lines[0].get_xdata(), x_before)
    assert np.array_equal(ax.lines[0].get_ydata(), y_before)
    assert ax.lines[0].get_drawstyle() == "default"
    assert np.array_equal(path.reaction_coordinates, x_before)
    assert np.array_equal(path.plotted_energy_ev, y_before)
    assert path.digest == digest_before

    figure_without_barrier, ax_without_barrier = plot_neb_path(path)
    assert figure_without_barrier.axes == [ax_without_barrier]
    assert len(ax_without_barrier.lines) == 1
    assert len(ax_without_barrier.collections) == 0


def test_plot_rejects_mismatched_barrier_provenance_and_nonlinear_scales() -> None:
    path = build_neb_path(_images(), key="path")
    barrier = calculate_neb_barrier(
        path,
        initial_image_key="i0",
        saddle_image_key="i2",
        final_image_key="i3",
    )
    other_path = build_neb_path(_images(), key="other-path")
    with pytest.raises(NEBVisualizationError, match="path_digest"):
        plot_neb_path(other_path, barrier=barrier)

    with pytest.raises(NEBVisualizationError, match="linear"):
        plot_neb_path(path, spec=FigureSpec(xscale="log"))
