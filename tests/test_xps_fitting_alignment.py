"""Focused fail-closed alignment regressions for constrained XPS fitting."""

from __future__ import annotations

from dataclasses import replace

import numpy as np
import pytest

from catalysis_workbench.core import Axis, Series
from catalysis_workbench.experimental.characterization import (
    XPSError,
    fit_xps_peaks,
    linear_xps_background,
)
from catalysis_workbench.processing import FitParameterSpec, PeakComponentSpec


def _series(*, y_unit: str = "counts") -> Series:
    x = np.linspace(280.0, 290.0, 101)
    y = 2.0 + np.exp(-((x - 285.0) ** 2) / (2.0 * 0.7**2))
    y[0] = 2.0
    y[-1] = 2.0
    return Series(
        x=x,
        y=y,
        key="alignment-source",
        x_axis=Axis("binding_energy", unit="eV"),
        y_axis=Axis("intensity", unit=y_unit),
    )


def _component() -> PeakComponentSpec:
    return PeakComponentSpec(
        key="peak",
        model="gaussian",
        parameters={
            "amplitude": FitParameterSpec(1.0, lower=0.0),
            "center": FitParameterSpec(285.0),
            "sigma": FitParameterSpec(0.8, lower=0.05),
        },
    )


def test_background_intensity_unit_mismatch_fails_closed() -> None:
    source = _series(y_unit="counts")
    background = linear_xps_background(source)
    relabeled = Series(
        x=source.x,
        y=source.y,
        key=source.key,
        x_axis=source.x_axis,
        y_axis=Axis("intensity", unit="cps"),
    )

    with pytest.raises(XPSError, match="intensity unit"):
        fit_xps_peaks(
            relabeled,
            x_min_ev=280.0,
            x_max_ev=290.0,
            components=(_component(),),
            background=background,
        )


def test_background_declared_direction_mismatch_fails_closed() -> None:
    source = _series()
    background = linear_xps_background(source)
    inconsistent = replace(background, source_direction="descending")

    with pytest.raises(XPSError, match="source direction"):
        fit_xps_peaks(
            source,
            x_min_ev=280.0,
            x_max_ev=290.0,
            components=(_component(),),
            background=inconsistent,
        )
