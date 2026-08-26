from __future__ import annotations

import numpy as np
import pytest

from catalysis_workbench.visualization import (
    VisualizationError,
    symmetric_color_limits,
)


def test_nonzero_ranges_are_exact_and_symmetric() -> None:
    assert symmetric_color_limits([-2.0, 4.0]) == (-4.0, 4.0)
    assert symmetric_color_limits([1.0, 3.0]) == (-3.0, 3.0)
    assert symmetric_color_limits(np.array([[1.0, -7.0], [3.0, 2.0]])) == (-7.0, 7.0)
    assert symmetric_color_limits(2.5) == (-2.5, 2.5)


def test_all_zero_uses_explicit_fallback() -> None:
    assert symmetric_color_limits(np.zeros((2, 3))) == (-1.0, 1.0)
    assert symmetric_color_limits([0.0], zero_half_range=0.25) == (-0.25, 0.25)


def test_does_not_mutate_input() -> None:
    values = np.array([[-2.0, 0.0], [3.0, 1.0]])
    before = values.copy()
    symmetric_color_limits(values)
    np.testing.assert_array_equal(values, before)


@pytest.mark.parametrize("values", [[], [np.nan], [np.inf], [-np.inf]])
def test_invalid_values_fail_closed(values) -> None:
    with pytest.raises(VisualizationError):
        symmetric_color_limits(values)


def test_complex_and_nonnumeric_fail_closed() -> None:
    with pytest.raises(VisualizationError, match="complex"):
        symmetric_color_limits([1.0 + 0.0j])
    with pytest.raises(TypeError, match="real numeric"):
        symmetric_color_limits(["not-a-number"])


@pytest.mark.parametrize("fallback", [0.0, -1.0, np.nan, np.inf])
def test_invalid_zero_fallback_fails_closed(fallback) -> None:
    with pytest.raises(VisualizationError, match="zero_half_range"):
        symmetric_color_limits([0.0], zero_half_range=fallback)
