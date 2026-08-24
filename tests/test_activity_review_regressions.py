"""Regression tests for findings from the formal Issue #24 API review."""

from __future__ import annotations

import pytest

from catalysis_workbench.core import Axis, Series
from catalysis_workbench.experimental.echem import (
    ActivityNormalizationError,
    normalize_activity,
    plot_activity,
)


def _valid_kwargs() -> dict[str, object]:
    return {
        "current": [-2.0],
        "current_unit": "mA",
        "current_basis": "current",
        "basis": "catalyst_mass",
        "denominator_value": 2.0,
        "denominator_unit": "mg",
    }


@pytest.mark.parametrize("field", ["basis", "current_basis", "sign_mode"])
def test_invalid_unhashable_enum_inputs_raise_domain_error(field: str):
    kwargs = _valid_kwargs()
    kwargs[field] = {"invalid": "value"}
    with pytest.raises(ActivityNormalizationError):
        normalize_activity(**kwargs)  # type: ignore[arg-type]


def test_plot_activity_rejects_unhashable_normalization_metadata_cleanly():
    malformed = Series(
        x=(-0.7,),
        y=(-1.0,),
        key="cat-a",
        x_axis=Axis("potential", unit="V", metadata={"reference": "RHE"}),
        y_axis=Axis(
            "activity",
            unit="A/g",
            metadata={"normalization": {"basis": "catalyst_mass"}},
        ),
    )
    with pytest.raises(ActivityNormalizationError, match="normalization metadata"):
        plot_activity(malformed)
