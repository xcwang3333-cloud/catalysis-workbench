from __future__ import annotations

import sys

import numpy as np
import pytest

from catalysis_workbench.core import Axis, Dataset, Series
from catalysis_workbench.experimental.characterization.xas import (
    XANESNormalizationResult,
    XANESNormalizationSpec,
    XASError,
    XASWindow,
    normalize_xanes,
    shift_xas_energy,
    validate_xas_series,
    xanes_relative_energy,
)


def _series(*, descending: bool = False) -> Series:
    energy = np.arange(0.0, 7.0)
    delta = energy - 3.0
    pre = 1.0 + 0.1 * delta
    post = 3.0 + 0.2 * delta
    mu = np.where(energy < 3.0, pre, post)
    if descending:
        energy = energy[::-1]
        mu = mu[::-1]
    return Series(
        x=energy,
        y=mu,
        label="sample",
        key="sample",
        x_axis=Axis("energy", unit="eV"),
        y_axis=Axis("mu", unit="a.u."),
        metadata={"source": "synthetic"},
    )


def _spec() -> XANESNormalizationSpec:
    return XANESNormalizationSpec(
        e0_ev=3.0,
        pre_edge=XASWindow(0.0, 2.0),
        post_edge=XASWindow(4.0, 6.0),
        pre_edge_order=1,
        post_edge_order=1,
    )


def test_validate_xas_and_exact_energy_shift() -> None:
    source = _series()
    validate_xas_series(source)
    shifted = shift_xas_energy(source, 1.25, reference="foil alignment")
    np.testing.assert_allclose(shifted.x, np.asarray(source.x) + 1.25)
    np.testing.assert_array_equal(shifted.y, source.y)
    assert shifted.metadata["energy_reference"] == "foil alignment"
    assert shifted.metadata["xas_energy_shift_ev"] == pytest.approx(1.25)
    assert shifted.metadata["processing_history"][-1]["operation"] == "xas.energy_shift"


def test_normalize_xanes_recovers_centered_polynomials_and_edge_step() -> None:
    result = normalize_xanes(_series(), _spec())
    np.testing.assert_allclose(result.pre_edge_coefficients, [1.0, 0.1], atol=1e-12)
    np.testing.assert_allclose(result.post_edge_coefficients, [3.0, 0.2], atol=1e-12)
    assert result.edge_step == pytest.approx(2.0)
    expected = (result.source_mu - result.pre_edge_curve) / 2.0
    np.testing.assert_allclose(result.normalized.y, expected)
    assert result.normalized.y_axis.name == "normalized_mu"
    assert result.normalized.y_axis.unit == "1"
    assert result.normalized.metadata["xas_e0_ev"] == pytest.approx(3.0)


def test_descending_source_preserves_direction_and_scientific_result() -> None:
    ascending = normalize_xanes(_series(), _spec())
    descending = normalize_xanes(_series(descending=True), _spec())
    assert np.all(np.diff(descending.normalized.x) < 0.0)
    np.testing.assert_allclose(
        np.asarray(descending.normalized.y)[::-1],
        np.asarray(ascending.normalized.y),
        atol=1e-12,
    )
    np.testing.assert_allclose(
        descending.pre_edge_coefficients,
        ascending.pre_edge_coefficients,
    )
    np.testing.assert_allclose(
        descending.post_edge_coefficients,
        ascending.post_edge_coefficients,
    )


def test_relative_energy_is_explicit_and_non_mutating() -> None:
    result = normalize_xanes(_series(), _spec())
    relative = xanes_relative_energy(result)
    np.testing.assert_allclose(relative.x, np.asarray(result.source_energy_ev) - 3.0)
    np.testing.assert_array_equal(relative.y, result.normalized.y)
    assert relative.x_axis.name == "energy_relative_to_e0"
    assert relative.x_axis.metadata["reference"] == "E0"
    validate_xas_series(relative, allow_relative_energy=True)


def test_result_reconstruction_fails_closed() -> None:
    result = normalize_xanes(_series(), _spec())
    with pytest.raises(XASError, match="edge_step contradicts"):
        XANESNormalizationResult(
            source_key=result.source_key,
            source_digest=result.source_digest,
            source_energy_ev=result.source_energy_ev,
            source_mu=result.source_mu,
            e0_ev=result.e0_ev,
            pre_edge=result.pre_edge,
            post_edge=result.post_edge,
            pre_edge_order=result.pre_edge_order,
            post_edge_order=result.post_edge_order,
            pre_edge_coefficients=result.pre_edge_coefficients,
            post_edge_coefficients=result.post_edge_coefficients,
            pre_edge_curve=result.pre_edge_curve,
            post_edge_curve=result.post_edge_curve,
            edge_step=result.edge_step + 1.0,
            normalized=result.normalized,
        )


@pytest.mark.parametrize(
    ("series", "message"),
    [
        (
            Series(
                [1.0, 2.0],
                [1.0, 2.0],
                x_axis=Axis("wavelength", unit="eV"),
                y_axis=Axis("mu", unit="a.u."),
            ),
            "x axis",
        ),
        (
            Series(
                [1.0, 2.0],
                [1.0, 2.0],
                x_axis=Axis("energy", unit="keV"),
                y_axis=Axis("mu", unit="a.u."),
            ),
            "eV",
        ),
        (
            Series(
                [1.0, 2.0],
                [1.0 + 0.0j, 2.0 + 1.0j],
                x_axis=Axis("energy", unit="eV"),
                y_axis=Axis("mu", unit="a.u."),
            ),
            "real-valued",
        ),
        (
            Series(
                [1.0, 1.0, 2.0],
                [1.0, 1.2, 2.0],
                x_axis=Axis("energy", unit="eV"),
                y_axis=Axis("mu", unit="a.u."),
            ),
            "strictly monotonic",
        ),
        (
            Series(
                [1.0, 3.0, 2.0],
                [1.0, 2.0, 1.5],
                x_axis=Axis("energy", unit="eV"),
                y_axis=Axis("mu", unit="a.u."),
            ),
            "strictly monotonic",
        ),
    ],
)
def test_validation_failures(series: Series, message: str) -> None:
    with pytest.raises(XASError, match=message):
        validate_xas_series(series)


def test_missing_data_is_rejected() -> None:
    source = Series(
        [1.0, 2.0, 3.0],
        [1.0, np.nan, 2.0],
        x_axis=Axis("energy", unit="eV"),
        y_axis=Axis("mu", unit="a.u."),
    )
    with pytest.raises(XASError, match="missing"):
        validate_xas_series(source)


def test_normalization_spec_and_range_failures() -> None:
    source = _series()
    with pytest.raises(XASError, match="strictly inside"):
        normalize_xanes(
            source,
            XANESNormalizationSpec(
                0.0,
                XASWindow(-2.0, -1.0),
                XASWindow(1.0, 2.0),
            ),
        )
    with pytest.raises(XASError, match="pre-edge window"):
        XANESNormalizationSpec(
            3.0,
            XASWindow(1.0, 3.0),
            XASWindow(4.0, 6.0),
        )
    with pytest.raises(XASError, match="post-edge window"):
        XANESNormalizationSpec(
            3.0,
            XASWindow(0.0, 2.0),
            XASWindow(3.0, 5.0),
        )
    with pytest.raises(XASError, match="needs at least"):
        normalize_xanes(
            source,
            XANESNormalizationSpec(
                3.0,
                XASWindow(0.0, 1.0),
                XASWindow(4.0, 6.0),
                pre_edge_order=2,
            ),
        )


def test_non_positive_edge_step_is_rejected() -> None:
    energy = np.arange(0.0, 7.0)
    source = Series(
        energy,
        np.where(energy < 3.0, 3.0, 1.0),
        x_axis=Axis("energy", unit="eV"),
        y_axis=Axis("mu", unit="a.u."),
    )
    with pytest.raises(XASError, match="edge step"):
        normalize_xanes(source, _spec())


def test_plotting_is_lazy_and_passive() -> None:
    result = normalize_xanes(_series(), _spec())
    sys.modules.pop("matplotlib", None)
    sys.modules.pop("matplotlib.pyplot", None)
    import catalysis_workbench.experimental.characterization.xas as xas_module

    assert xas_module.normalize_xanes is normalize_xanes
    assert "matplotlib.pyplot" not in sys.modules

    from catalysis_workbench.experimental.characterization.xas_plotting import plot_xanes

    before_x = np.array(result.normalized.x, copy=True)
    before_y = np.array(result.normalized.y, copy=True)
    figure, ax = plot_xanes(result.normalized)
    np.testing.assert_array_equal(result.normalized.x, before_x)
    np.testing.assert_array_equal(result.normalized.y, before_y)
    np.testing.assert_array_equal(ax.lines[0].get_xdata(), before_x)
    np.testing.assert_array_equal(ax.lines[0].get_ydata(), before_y)
    figure.canvas.draw()


def test_plot_overlay_rejects_mixed_reference_or_normalization_state() -> None:
    from catalysis_workbench.experimental.characterization.xas_plotting import plot_xanes

    result = normalize_xanes(_series(), _spec())
    relative = xanes_relative_energy(result)
    with pytest.raises(XASError, match="energy-reference"):
        plot_xanes(Dataset((result.normalized, relative)))
    with pytest.raises(XASError, match="raw and normalized"):
        plot_xanes(Dataset((_series(), result.normalized)))
