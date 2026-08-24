"""Contract tests for partial current density calculations."""

import numpy as np
import pytest

from catalysis_workbench.experimental.echem.partial_current import (
    PartialCurrentDensityError,
    partial_current_density,
)


def test_signed_partial_current_density_preserves_cathodic_sign():
    result = partial_current_density([-100.0], [0.95])

    assert np.allclose(result.values, [-95.0])
    assert result.sign_mode == "signed"


def test_magnitude_partial_current_density_returns_absolute_value():
    result = partial_current_density([-100.0], [0.95], sign_mode="magnitude")

    assert np.allclose(result.values, [95.0])


def test_percentage_fe_is_converted_to_fraction():
    result = partial_current_density([-100.0], [95.0], fe_unit="%")

    assert np.allclose(result.fe_fraction, [0.95])


def test_shape_mismatch_is_rejected():
    with pytest.raises(PartialCurrentDensityError):
        partial_current_density([1.0, 2.0], [0.5, 0.5, 0.5])


def test_negative_fe_is_rejected():
    with pytest.raises(PartialCurrentDensityError):
        partial_current_density([1.0], [-0.1])
