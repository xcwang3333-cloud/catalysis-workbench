from __future__ import annotations

import matplotlib as mpl
import matplotlib.image as mpimg
import pytest

from catalysis_workbench.core import Axis, Dataset, Series
from catalysis_workbench.visualization import (
    ExportSpec,
    FigureSpec,
    LayoutSpec,
    VisualizationError,
    export_figure,
    render_curves,
)


def _curve(
    *,
    key: str,
    reference: str | None = None,
    normalization: str | None = None,
    source_reference: str | None = None,
    electrode_area_cm2: float | None = None,
) -> Series:
    x_metadata: dict[str, object] = {}
    y_metadata: dict[str, object] = {}
    if reference is not None:
        x_metadata["reference"] = reference
    if source_reference is not None:
        x_metadata["source_reference"] = source_reference
    if normalization is not None:
        y_metadata["normalization"] = normalization
    if electrode_area_cm2 is not None:
        y_metadata["electrode_area_cm2"] = electrode_area_cm2
    return Series(
        x=(0.0, 0.5, 1.0),
        y=(1.0, 2.0, 3.0),
        label=key,
        key=key,
        x_axis=Axis(
            "potential",
            unit="V",
            label="Potential",
            metadata=x_metadata,
        ),
        y_axis=Axis(
            "current_density",
            unit="mA/cm^2",
            label="Current density",
            metadata=y_metadata,
        ),
    )


def test_render_rejects_different_electrochemical_reference_metadata():
    dataset = Dataset(
        [
            _curve(key="rhe", reference="RHE"),
            _curve(key="agcl", reference="Ag/AgCl"),
        ]
    )

    with pytest.raises(VisualizationError, match="reference"):
        render_curves(dataset)


def test_render_rejects_different_current_density_normalization_basis():
    dataset = Dataset(
        [
            _curve(key="geo", normalization="geometric_area"),
            _curve(key="ecsa", normalization="ECSA"),
        ]
    )

    with pytest.raises(VisualizationError, match="normalization"):
        render_curves(dataset)


def test_render_allows_provenance_only_axis_metadata_to_differ():
    dataset = Dataset(
        [
            _curve(
                key="a",
                reference="RHE",
                normalization="geometric_area",
                source_reference="Ag/AgCl",
                electrode_area_cm2=0.2,
            ),
            _curve(
                key="b",
                reference="RHE",
                normalization="geometric_area",
                source_reference="SCE",
                electrode_area_cm2=1.0,
            ),
        ]
    )

    _, ax = render_curves(dataset)
    assert len(ax.lines) == 2


def test_explicit_blank_axis_labels_disable_automatic_labels():
    spec = FigureSpec(xlabel="", ylabel="")

    _, ax = render_curves(_curve(key="a"), spec)

    assert ax.get_xlabel() == ""
    assert ax.get_ylabel() == ""


def test_renderer_ignores_ambient_rc_style_and_restores_it():
    original_facecolor = mpl.rcParams["axes.facecolor"]
    original_grid = mpl.rcParams["axes.grid"]
    try:
        mpl.rcParams["axes.facecolor"] = "red"
        mpl.rcParams["axes.grid"] = True

        _, ax = render_curves(_curve(key="a"))

        assert ax.get_facecolor() == pytest.approx((1.0, 1.0, 1.0, 1.0))
        assert not any(line.get_visible() for line in ax.get_xgridlines())
        assert not any(line.get_visible() for line in ax.get_ygridlines())
        assert mpl.rcParams["axes.facecolor"] == "red"
        assert mpl.rcParams["axes.grid"] is True
    finally:
        mpl.rcParams["axes.facecolor"] = original_facecolor
        mpl.rcParams["axes.grid"] = original_grid


def test_export_restores_live_figure_size_after_temporary_export_layout(tmp_path):
    preview_spec = FigureSpec(
        layout=LayoutSpec(
            figure_width_in=4.0,
            figure_height_in=3.0,
            left_margin_in=0.5,
            right_margin_in=0.2,
            bottom_margin_in=0.4,
            top_margin_in=0.2,
        )
    )
    export_spec = FigureSpec(
        layout=LayoutSpec(
            figure_width_in=2.0,
            figure_height_in=1.0,
            left_margin_in=0.25,
            right_margin_in=0.10,
            bottom_margin_in=0.25,
            top_margin_in=0.10,
        ),
        export=ExportSpec(dpi=120),
    )
    figure, _ = render_curves(_curve(key="a"), preview_spec)

    output = export_figure(figure, tmp_path / "export.png", spec=export_spec)
    image = mpimg.imread(output)

    assert image.shape[:2] == (120, 240)
    assert tuple(figure.get_size_inches()) == pytest.approx((4.0, 3.0))


def test_export_rejects_invalid_spec_type_with_documented_type_error(tmp_path):
    figure, _ = render_curves(_curve(key="a"))

    with pytest.raises(TypeError, match="spec must be a FigureSpec"):
        export_figure(figure, tmp_path / "figure.png", spec=object())  # type: ignore[arg-type]
